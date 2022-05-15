from __future__ import annotations

import asyncio
import importlib.util
import sys
import traceback
import types
from typing import Coroutine, Dict, List, Optional, Union

from .commands import Command
from .components import Component
from .context import Context
from .errors import *
from twitchio import Client, Message


class Bot(Client):

    def __init__(self, prefix: Union[list, callable, Coroutine], *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__commands: Dict[str, Command] = {}
        self.__components: Dict[str, Component] = {}
        self.__extensions: Dict[str, types.ModuleType] = {}

        self._unassigned_prefixes = prefix
        self._prefixes: List[str] = []

        self._in_context: bool = False

    async def __aenter__(self) -> Bot:
        self._in_context = True

        await self._prepare_prefixes()
        await super().__aenter__()

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._in_context = False

        await super().__aexit__(exc_type, exc_val, exc_tb)

    def run(self, token: Optional[str] = None) -> None:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._prepare_prefixes())

        super().run(token=token)

    async def start(self, token: Optional[str] = None) -> None:
        if not self._in_context:
            raise RuntimeError('"bot.start" can only be used within the bot async context manager.')

        await super().start(token=token)

    @property
    def prefixes(self) -> List[str]:
        return self._prefixes.copy()

    @property
    def commands(self) -> Dict[str, Command]:
        return self.__commands.copy()

    @property
    def components(self) -> Dict[str, Component]:
        return self.__components.copy()

    @property
    def extensions(self) -> Dict[str, types.ModuleType]:
        return self.__extensions.copy()

    async def _prepare_prefixes(self) -> None:
        if asyncio.iscoroutine(self._unassigned_prefixes):
            prefixes = await self._unassigned_prefixes(self)

        elif callable(self._unassigned_prefixes):
            prefixes = self._unassigned_prefixes(self)

        else:
            prefixes = self._unassigned_prefixes

        if isinstance(prefixes, str):
            self._prefixes = [prefixes]

        elif isinstance(prefixes, list):
            if not all(isinstance(prefix, str) for prefix in prefixes):
                raise TypeError('prefix parameter must be a str, list of str or callable/coroutine returning either.')
            self._prefixes = prefixes

        else:
            raise TypeError('prefix parameter must be a str, list of str or callable/coroutine returning either.')

    def get_context(self, message: Message, *, cls: Optional[Context] = Context) -> Context:
        # noinspection PyTypeChecker
        if cls and not issubclass(cls, Context):
            raise TypeError(f'cls parameter must derive from {Context!r}.')

        return cls(message, self)

    async def process_commands(self, message: Message):
        context = self.get_context(message=message)

        if context.is_valid:
            await context.invoke()

    def add_command(self, command: Command) -> None:
        if not isinstance(command, Command):
            raise TypeError(f'The command argument must be a subclass of commands.Command.')

        if command.name in self.commands or any(x in self.commands for x in command.aliases):
            raise ValueError(f'Command "{command.name}" is already registered command or alias.')

        if not asyncio.iscoroutinefunction(command._callback):
            raise TypeError('Command callbacks must be coroutines.')

        command._instance = command._component or self

        self.__commands[command.name] = command

    def remove_command(self, command: Command) -> None:
        if not isinstance(command, Command):
            raise TypeError(f'The command argument must be a subclass of commands.Command.')

        if command.name not in self.commands and not any(x in self.commands for x in command.aliases):
            raise ValueError(f'Command "{command.name}" is not an already registered command or alias.')

        del self.__commands[command.name]

    async def add_component(self, component: Component, *, override: bool = False) -> None:
        if not isinstance(component, Component):
            raise TypeError(f'component argument must be of type "commands.Component", not {type(component)}.')

        # noinspection PyUnresolvedReferences
        if not override and component.__component_name__ in self.__components:
            raise ComponentAlreadyExistsError('This component has already been loaded. '
                                              'Consider using the override parameter.')

        # noinspection PyUnresolvedReferences
        commands_ = component.commands
        for name, command in commands_.items():
            self.add_command(command)

        try:
            await component.component_on_load()
        except Exception as e:
            for name, command in commands_.items():
                self.remove_command(command)

            raise ComponentLoadError(f'The component "{component.name}" failed to load due to the above error.') from e

        self.__components[component.__component_name__] = component

    async def remove_component(self, component: Union[str, Component]) -> None:
        if isinstance(component, str):
            try:
                component = self.__components[component]
            except KeyError:
                raise ComponentNotFoundError(f'The component "{component}" is not currently loaded.')

        elif not isinstance(component, Component):
            raise TypeError(f'component argument must be of type "commands.Component" or str, not {type(component)}.')

        commands_ = component.commands
        for name, command in commands_.items():
            self.remove_command(command)

        try:
            await component.component_on_unload()
        except Exception as e:
            print(f'Ignoring exception in "{component.__component_name__}.component_on_unload":', file=sys.stderr)
            traceback.print_tb(e.__traceback__)

        del self.__components[component.__component_name__]

    def _get_extension_name(self, extension: str, package: Optional[str]) -> str:
        try:
            return importlib.util.resolve_name(extension, package)
        except ImportError:
            raise ExtensionNotFoundError(f'The extension "{extension}" was not found.')

    async def _remove_extension_remnants(self, name: str):
        for component_name, component in self.__components.copy().items():
            if component.__module__ == name or component.__module__.startswith(f'{name}.'):
                await self.remove_component(component)

    async def load_extension(self, extension: str, package: Optional[str] = None) -> None:
        name = self._get_extension_name(extension, package)

        if name in self.__extensions:
            raise ExtensionAlreadyLoadedError(f'The extension "{extension}" is already loaded.')

        spec = importlib.util.find_spec(name)
        if spec is None:
            raise ExtensionNotFoundError(f'The extension "{extension}" was not found.')

        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            del sys.modules[name]
            raise ExtensionLoadFailureError(e) from e

        try:
            entry = getattr(module, 'setup')
        except AttributeError:
            del sys.modules[name]
            raise NoExtensionEntryPoint(f'The extension "{extension}" has no setup coroutine.')

        if not asyncio.iscoroutinefunction(entry):
            del sys.modules[name]
            raise TypeError(f'The extension "{extension}"\'s setup function is not a coroutine.')

        try:
            await entry(self)
        except Exception as e:
            del sys.modules[name]
            await self._remove_extension_remnants(module.__name__)
            raise ExtensionLoadFailureError(e) from e

        self.__extensions[name] = module

    async def unload_extension(self, extension: str, package: Optional[str] = None) -> None:
        name = self._get_extension_name(extension, package)

        if name not in self.__extensions:
            raise ExtensionNotFoundError(f'The extension "{extension}" is not already loaded.')

        module = self.__extensions[name]

        try:
            exit_ = getattr(module, 'teardown')
        except AttributeError:
            exit_ = None

        try:
            if exit_:
                await exit_(self)
        except Exception as e:
            print(f'Ignoring exception in "{name}.teardown":', file=sys.stderr)
            traceback.print_tb(e.__traceback__)
        finally:
            try:
                await self._remove_extension_remnants(name)
            except Exception:
                pass

            del sys.modules[name]
            del self.__extensions[name]
            del module

    async def reload_extension(self, extension: str, package: Optional[str] = None):
        name = self._get_extension_name(extension, package)

        await self.unload_extension(name)
        await self.load_extension(name)

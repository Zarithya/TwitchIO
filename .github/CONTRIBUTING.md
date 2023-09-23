Thanks for your interest in developing TwitchIO. This document will guide you through all the project-specific information such as documentation formatting, naming guides, and code styles.

# Documentation

## Changelog

All changes must be documented in the changelog.
The changelog has a category for the main lib (eg anything under the `twitchio` namespace) and a category for each sub-library (each ext).
Each category has 3 sub-categories: `Additions`, `Updates` and `Bug Fixes`.
Additions is for new methods, classes, or functions.
Updates is for changes to any methods, classes, or functions.
Bug Fixes is for any Updates that are made specifically to fix an issue with the library (as opposed to Updates that do not fix an existing issue).

When documenting a change, include the class or function being added/changed as a sphinx directive (eg :class:\`~twitchio.PartialUser\` or :meth:\`~twitchio.PartialUser.ban_user\`).
Also include a quick snippet of what the change has done, what parameters it has added, etc.
An example would be: 
```
- Twitchio
    - Additions
        - Added :class:`~twitchio.FunkyData` to contain data for calls to :meth:`twitchio.PartialUser.fetch_funky_data`
```

### When to use the tilde

of note in this example; the tilde (~) is used to remove the prefixing data from the displayed text,
so :meth:\`twitchio.PartialUser.fetch_funky_data\` would show up as `twitchio.PartialUser.fetch_funky_data`,
while :meth:\`~twitchio.PartialUser.fetch_funky_data\` would show up as `fetch_funky_data`.

When displaying a method of a class, it is important to keep the name of the class in the displayed text, as such we do not use a tilde (the only exception to this is referencing another method of a class from within it). 
However, when simply referencing a class, we may use the tilde to remove the prefix of `twitchio.` from the displayed text.

## Building the docs

Building the docs is quite simple.
Simply `cd` into the `docs` folder, ensure you have the doc dependancies installed with `pip install requirements.txt`, and run `make html`.

All in one, that might look like this:
```sh
$ cd docs/
$ pip install requirements.txt
$ make html
```

## Documentation basics

Whenever you are documenting any function, class or otherwise, we follow full english grammar. This means that all sentences start with a capital, and end with a period.
Whenever you are referencing a class, you must include a sphinx directive link to that class, you may not simply put the name in plaintext. You can do this via :class:\`~twitchio.MyClass\` .
The same goes for references to functions, you must include a sphinx directive link to them. When linking to functions, you must not use a tilde (see: "when to use the tilde"), UNLESS the function you are referencing is in the same class as the one you are referencing it from.
You can provide function references using :meth:\`twitchio.MyClass.my_func\` .
Whenever making a heading (for anything from a text heading to a list of attributes or parameters), the heading marker should be one character longer than the text of the heading, eg:
```rst
My Heading
===========

My Subheading
--------------

My SubSubHeading
+++++++++++++++++
```
This is the exact order of characters to be used when making headings/subheadings. When making any headings within a docstring, use dashes (----) as the top-level heading character.

## Documenting classes

Class docstrings are important to get right, as they power the attribute table extension. Mistyping a class docstring will lead to the attribute table not working.

Here is an example of a class docstring:

```py
class PartialUser:
    """
    This is a user on Twitch, created from local information. From here you can perform API calls, check the user's information, and so on.

    .. container:: operations

        .. describe:: x == y

            Checks if the token is equal to another.

        .. describe:: x != y

            Checks if the token is not equal to another.

        .. describe:: str(x)

            Returns the token.

        .. describe:: hash(x)

            Returns the hash of the access token.

    .. versionadded:: 3.0

    Attributes
    -----------
    id: :class:`str`
        The unique ID of the user.
    name: :class:`str`
        The name that is displayed in chat and on the user's page.
    login: :class:`str`
        The unique name that the user has on twitch, in all lowercase.
    """
```

The first thing in each class docstring should be a brief description of the class' purpose.
Secondly, there should be a container describing all the available operations on the class. If no operations are available, think again. There should always be at the very least an eq, neq, and str or repr or both.
After the container, you should include the version marker. It should be one of `.. versionadded:: VERSION` or `.. versionchanged:: VERSION`. The version changed marker should only be used if changing the attributes of a class, not the methods of it (as those have their own versionadded/versionchanged markers).
You may have both a versionadded and a versionchanged, but if a versionchanged already exists, it should instead be updated.
After the version marker, you should have a list of all attributes, under the `Attributes` header.
Each attribute should follow this exact format:

```rst
Attributes
-----------
attribute_name: :class:`attribute_type`
    A short description of the attribute.

    .. note::
        A note or warning where applicable, eg if an attribute has been deprectated. This is OPTIONAL.
        If no note/warning is required, do not include the note directive at all.
```

## Documenting methods

Method/Function docstrings contain all the information a user should need to call the method, whether that be background information on the conditions to use the function, or scopes requires for an API call to succeed.
Here's an example of a fully documented method:

```py
class PartialUser:
    async def fetch_custom_rewards(
        self, *, only_manageable=False, ids: list[int] | None = None, force=False
    ) -> HTTPAwaitableAsyncIterator[CustomReward]:
        """|aai|

        Fetches the channels custom rewards (aka channel points) from the api.
        Requires an OAuth token with the ``channel:read:redemptions`` or ``channel:manage:redemptions`` scope.

        .. versionchanged:: 3.0
            Description of what has changed.

        Parameters
        ----------
        only_manageable: :class:`bool`
            Whether to fetch all rewards or only ones you can manage. Defaults to ``False``.
        ids: list[:class:`int`]
            An optional list of reward ids.
        force: :class:`bool`
            Whether to force a fetch or try to get from cache. Defaults to ``False``.

        Returns
        -------
        :class:`~twitchio.AwaitableAsyncIterator`[:class:`~twitchio.CustomReward`]
        """
```

parameter types in docstrings should use the most up-to-date typing constructs (eg. as of writing: ``A | B``, ``list[T]``, etc.).
While types should always point to documentation wherever possible (eg primitives, models). If needed, the label can be modified by doing ```:class:`Label <reference>` ``` (useful for decorators, not so much for parameter types).


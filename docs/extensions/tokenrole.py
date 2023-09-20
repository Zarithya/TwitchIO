from docutils.parsers.rst import Directive

from typing import Any, Dict, List, Tuple

from docutils import nodes, utils
from docutils.nodes import Node, system_message
from docutils.parsers.rst.states import Inliner
from sphinx.util.nodes import split_explicit_title

class TokenText(nodes.General, nodes.Element):
    pass

def visit_token_node(self, node):
    self.visit_

class Token(Directive):
    required_arguments = 1

    def run(self):
        print(dir(self))
        print(self.arguments)
        p = nodes.document(f"This API call requires a token with the ``{self.arguments[0]}`` scope")
        return [p]

def role(
        typ: str,
        rawtext: str,
        text: str,
        lineno: int,
        inliner: Inliner,
        options: Dict = {},
        content: List[str] = []
    ) -> Tuple[List[Node], List[system_message]]:

    text = utils.unescape(text)
    print("ROLE WORKS", typ, rawtext, text, options, content)
    text = utils.unescape(text)
    has_explicit_title, title, key = split_explicit_title(text)
    pnode = nodes.reference(title, title, internal=False, refuri="")
    return [pnode], []

def foo(app):
    print("adding role")
    app.add_role("token", role)


def setup(app):
    print("SETTING UP APP")
    #app.connect("builder-inited", foo)
    #app.add_role("token", role)
    app.add_node(TokenText)
    app.add_directive("token", Token)

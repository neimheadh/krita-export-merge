"""Minimal tests for ``merger.py`` using stubs of Krita's Node/Document."""

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock


# Load merger.py without going through merge_groups/__init__.py, which
# would pull in the real PyQt/Krita modules. Stubbing ``krita`` is
# enough for merger.py — it only uses ``Krita.instance().createDocument``.
_MERGER_PATH = Path(__file__).resolve().parent.parent / "merge_groups" / "merger.py"
sys.modules.setdefault("krita", MagicMock())
_spec = importlib.util.spec_from_file_location("_merger_under_test", _MERGER_PATH)
merger = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(merger)


class _Rect:
    def __init__(self, x=0, y=0, w=10, h=10):
        self._x, self._y, self._w, self._h = x, y, w, h

    def x(self): return self._x
    def y(self): return self._y
    def width(self): return self._w
    def height(self): return self._h
    def isEmpty(self): return self._w <= 0 or self._h <= 0


class _Node:
    def __init__(self, name, node_type, color_label=0, children=None):
        self._name = name
        self._type = node_type
        self._color_label = color_label
        self._children = []
        self._parent = None
        self._opacity, self._blending_mode = 255, "normal"
        self._visible, self._locked = True, False
        self._inherit_alpha, self._collapsed = False, False
        self.pixel_data_set = None
        for child in (children or ()):
            self._children.append(child)
            child._parent = self

    def name(self): return self._name
    def type(self): return self._type
    def colorLabel(self): return self._color_label
    def setColorLabel(self, v): self._color_label = v
    def childNodes(self): return list(self._children)
    def bounds(self): return _Rect(0, 0, 10, 10)

    def projectionPixelData(self, x, y, w, h):
        return f"<{self._name}:{x},{y},{w}x{h}>".encode()

    def setPixelData(self, data, x, y, w, h):
        self.pixel_data_set = (bytes(data), x, y, w, h)

    def opacity(self): return self._opacity
    def setOpacity(self, v): self._opacity = v
    def blendingMode(self): return self._blending_mode
    def setBlendingMode(self, v): self._blending_mode = v
    def visible(self): return self._visible
    def setVisible(self, v): self._visible = v
    def locked(self): return self._locked
    def setLocked(self, v): self._locked = v
    def inheritAlpha(self): return self._inherit_alpha
    def setInheritAlpha(self, v): self._inherit_alpha = v
    def collapsed(self): return self._collapsed
    def setCollapsed(self, v): self._collapsed = v

    def addChildNode(self, child, above):
        if above is None:
            self._children.append(child)
        else:
            self._children.insert(self._children.index(above) + 1, child)
        child._parent = self

    def remove(self):
        if self._parent is not None:
            self._parent._children.remove(self)
            self._parent = None

    def clone(self):
        twin = _Node(self._name, self._type, self._color_label,
                     [c.clone() for c in self._children])
        twin._opacity, twin._blending_mode = self._opacity, self._blending_mode
        twin._visible, twin._locked = self._visible, self._locked
        twin._inherit_alpha, twin._collapsed = self._inherit_alpha, self._collapsed
        return twin


class _Document:
    def __init__(self, root_children=()):
        self._root = _Node("root", "grouplayer", children=root_children)

    def rootNode(self): return self._root
    def width(self): return 100
    def height(self): return 100
    def name(self): return "Test"
    def colorModel(self): return "RGBA"
    def colorDepth(self): return "U8"
    def colorProfile(self): return ""
    def resolution(self): return 72
    def createNode(self, name, node_type): return _Node(name, node_type)
    def setBatchmode(self, _): pass
    def refreshProjection(self): pass


def _patch_krita_create_document():
    """Patch ``merger.Krita`` so ``createDocument`` returns a fresh
    ``_Document`` (with a default paint layer, to exercise the cleanup
    path in ``_new_document_like``)."""
    holder = {}

    def make_doc(*_args, **_kwargs):
        doc = _Document()
        default_layer = _Node("default", "paintlayer")
        doc._root._children.append(default_layer)
        default_layer._parent = doc._root
        holder["doc"] = doc
        return doc

    merger.Krita = MagicMock()
    merger.Krita.instance.return_value.createDocument.side_effect = make_doc
    return holder


class MergeMarkedGroupsTest(unittest.TestCase):

    def test_marked_group_is_flattened_into_paint_layer(self):
        source = _Document(root_children=[
            _Node("TATTOOS", "grouplayer", color_label=1, children=[
                _Node("dot", "paintlayer"),
                _Node("line", "paintlayer"),
            ]),
        ])
        holder = _patch_krita_create_document()

        merger.merge_marked_groups(source, {1})

        children = holder["doc"].rootNode().childNodes()
        self.assertEqual(len(children), 1)
        result = children[0]
        self.assertEqual(result.type(), "paintlayer")
        self.assertEqual(result.name(), "TATTOOS")
        self.assertIsNotNone(result.pixel_data_set,
                             "flattened group must have pixel data written")

    def test_unmarked_group_keeps_hierarchy_with_cloned_leaves(self):
        chair = _Node("chair", "paintlayer")
        source = _Document(root_children=[
            _Node("BACKGROUND", "grouplayer", color_label=0, children=[chair]),
        ])
        holder = _patch_krita_create_document()

        merger.merge_marked_groups(source, {1})

        children = holder["doc"].rootNode().childNodes()
        self.assertEqual(len(children), 1)
        bg = children[0]
        self.assertEqual(bg.type(), "grouplayer")
        self.assertEqual(bg.name(), "BACKGROUND")
        self.assertEqual([c.name() for c in bg.childNodes()], ["chair"])
        # The leaf in the dest tree must be a clone, not the source node.
        self.assertIsNot(bg.childNodes()[0], chair)

    def test_nested_marked_group_is_absorbed_by_marked_ancestor(self):
        source = _Document(root_children=[
            _Node("OUTER", "grouplayer", color_label=1, children=[
                _Node("INNER", "grouplayer", color_label=1, children=[
                    _Node("p", "paintlayer"),
                ]),
            ]),
        ])
        holder = _patch_krita_create_document()

        merger.merge_marked_groups(source, {1})

        children = holder["doc"].rootNode().childNodes()
        self.assertEqual(len(children), 1)
        result = children[0]
        self.assertEqual(result.type(), "paintlayer")
        self.assertEqual(result.name(), "OUTER")
        # OUTER replaces INNER entirely — no nested groups survive.
        self.assertEqual(result.childNodes(), [])

    def test_marked_group_with_only_vector_children_becomes_paint_layer(self):
        source = _Document(root_children=[
            _Node("ICONS", "grouplayer", color_label=1, children=[
                _Node("arrow", "vectorlayer"),
                _Node("circle", "vectorlayer"),
            ]),
        ])
        holder = _patch_krita_create_document()

        merger.merge_marked_groups(source, {1})

        children = holder["doc"].rootNode().childNodes()
        self.assertEqual(len(children), 1)
        result = children[0]
        self.assertEqual(result.type(), "paintlayer",
                         "vector-only marked group must still be rasterised")
        self.assertEqual(result.name(), "ICONS")
        self.assertIsNotNone(result.pixel_data_set)

    def test_marked_group_with_mixed_layer_types_becomes_paint_layer(self):
        source = _Document(root_children=[
            _Node("MIXED", "grouplayer", color_label=1, children=[
                _Node("base", "paintlayer"),
                _Node("decor", "vectorlayer"),
                _Node("fill", "filllayer"),
            ]),
        ])
        holder = _patch_krita_create_document()

        merger.merge_marked_groups(source, {1})

        children = holder["doc"].rootNode().childNodes()
        self.assertEqual(len(children), 1)
        result = children[0]
        self.assertEqual(result.type(), "paintlayer",
                         "mixed-type marked group must be rasterised")
        self.assertEqual(result.name(), "MIXED")
        self.assertIsNotNone(result.pixel_data_set)

    def test_only_selected_color_labels_trigger_merge(self):
        source = _Document(root_children=[
            _Node("BLUE_GROUP", "grouplayer", color_label=1, children=[
                _Node("a", "paintlayer"),
            ]),
            _Node("RED_GROUP", "grouplayer", color_label=6, children=[
                _Node("b", "paintlayer"),
            ]),
        ])
        holder = _patch_krita_create_document()

        merger.merge_marked_groups(source, {1})  # blue only

        by_name = {c.name(): c for c in holder["doc"].rootNode().childNodes()}
        self.assertEqual(by_name["BLUE_GROUP"].type(), "paintlayer")
        self.assertEqual(by_name["RED_GROUP"].type(), "grouplayer")


if __name__ == "__main__":
    unittest.main()

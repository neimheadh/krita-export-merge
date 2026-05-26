"""Core logic for the Merge Groups Export plugin.

Walks a source document's layer tree from the root toward the leaves and
builds a new document. As soon as a group whose color label is in the
selected set is encountered, its entire sub-tree is flattened into a
single paint layer (via projectionPixelData, which gives us the composed
result regardless of child types and masks). Non-marked branches are
cloned as-is, preserving the hierarchy.

Because the recursion stops at the first marked group it sees on a
branch, nested marked groups are simply absorbed by their marked
ancestor — no need to forbid or validate nested marking.
"""

from krita import Krita


def merge_marked_groups(source_doc, marked_labels):
    """Return a new document where every group whose color label is in
    ``marked_labels`` has been flattened into a paint layer.

    The returned document is not attached to any window; the caller is
    responsible for opening it (typically via ``window.addView(doc)``).

    Args:
        source_doc: ``krita.Document`` to read from.
        marked_labels: iterable of color label indices (1..8). Label 0
            (no label) is silently ignored.
    """
    marked = {int(label) for label in marked_labels if int(label) > 0}

    dest_doc = _new_document_like(source_doc)
    dest_doc.setBatchmode(True)
    try:
        _populate(source_doc.rootNode(), dest_doc.rootNode(), dest_doc, marked)
    finally:
        dest_doc.setBatchmode(False)
    dest_doc.refreshProjection()
    return dest_doc


def _new_document_like(source):
    """Create a blank document matching ``source``'s canvas, stripped of
    the default paint layer that ``createDocument`` adds."""
    app = Krita.instance()
    new_doc = app.createDocument(
        source.width(),
        source.height(),
        source.name() + " (merged)",
        source.colorModel(),
        source.colorDepth(),
        source.colorProfile(),
        source.resolution(),
    )
    for child in list(new_doc.rootNode().childNodes()):
        child.remove()
    return new_doc


def _populate(source_parent, dest_parent, dest_doc, marked):
    """Copy the children of ``source_parent`` into ``dest_parent``."""
    # NOTE: addChildNode(child, above) places ``child`` directly above
    # ``above`` in the stack; passing the previously inserted node as
    # the anchor preserves the source order regardless of whether
    # childNodes() yields bottom-first or top-first.
    previous = None
    for source_child in source_parent.childNodes():
        new_node = _convert(source_child, dest_doc, marked)
        if new_node is None:
            continue
        dest_parent.addChildNode(new_node, previous)
        previous = new_node


def _convert(source_node, dest_doc, marked):
    """Produce the dest-side counterpart of ``source_node``."""
    node_type = source_node.type()

    if node_type == "grouplayer" and source_node.colorLabel() in marked:
        return _flatten_group(source_node, dest_doc)

    if node_type == "grouplayer":
        new_group = dest_doc.createNode(source_node.name(), "grouplayer")
        _copy_properties(source_node, new_group)
        _populate(source_node, new_group, dest_doc, marked)
        return new_group

    # Leaf layer (paint, vector, fill, filter, clone, file…) or mask:
    # cloning preserves type, content, and any attached masks.
    return source_node.clone()


def _flatten_group(group_node, dest_doc):
    """Rasterize the composited projection of ``group_node`` into a new
    paint layer belonging to ``dest_doc``."""
    new_layer = dest_doc.createNode(group_node.name(), "paintlayer")
    _copy_properties(group_node, new_layer)

    bounds = group_node.bounds()
    if bounds.isEmpty():
        return new_layer

    pixels = group_node.projectionPixelData(
        bounds.x(), bounds.y(), bounds.width(), bounds.height()
    )
    new_layer.setPixelData(
        pixels, bounds.x(), bounds.y(), bounds.width(), bounds.height()
    )
    return new_layer


def _copy_properties(src, dst):
    dst.setOpacity(src.opacity())
    dst.setBlendingMode(src.blendingMode())
    dst.setVisible(src.visible())
    dst.setLocked(src.locked())
    dst.setColorLabel(src.colorLabel())
    if hasattr(src, "inheritAlpha"):
        dst.setInheritAlpha(src.inheritAlpha())
    if hasattr(src, "collapsed"):
        dst.setCollapsed(src.collapsed())

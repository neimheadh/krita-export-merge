"""Krita Extension that registers the ``Merge groups…`` action."""

from krita import Extension, Krita
from PyQt5.QtWidgets import QMessageBox

from .dialog import ask_color_labels
from .merger import merge_marked_groups


ACTION_ID = "merge_groups_export"
ACTION_TEXT = "Merge groups…"
# Default placement: Tools > Scripts. Putting the action directly under
# Tools would require editing Krita's global ``kritamenu.action`` file,
# which a redistributable plugin can't do portably. A keyboard shortcut
# can be bound in Settings > Configure Krita > Keyboard Shortcuts.
ACTION_MENU = "tools/scripts"

DIALOG_TITLE = "Merge Groups Export"


class MergeGroupsExtension(Extension):
    def __init__(self, parent):
        super().__init__(parent)
        self._last_selection = set()

    def setup(self):
        pass

    def createActions(self, window):
        action = window.createAction(ACTION_ID, ACTION_TEXT, ACTION_MENU)
        action.triggered.connect(self._on_triggered)

    def _on_triggered(self):
        app = Krita.instance()
        window = app.activeWindow()
        parent = window.qwindow() if window is not None else None

        source_doc = app.activeDocument()
        if source_doc is None:
            QMessageBox.information(
                parent, DIALOG_TITLE, "Open a document first."
            )
            return

        selection = ask_color_labels(parent, initial_selection=self._last_selection)
        if selection is None:
            return
        self._last_selection = selection

        try:
            merged_doc = merge_marked_groups(source_doc, selection)
        except Exception as exc:
            QMessageBox.critical(
                parent,
                DIALOG_TITLE,
                f"Failed to build the merged document:\n\n{exc}",
            )
            return

        window.addView(merged_doc)

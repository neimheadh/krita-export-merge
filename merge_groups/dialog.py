"""Modal Qt dialog asking which color labels should trigger a merge."""

from PyQt5.QtCore import QSize
from PyQt5.QtGui import QColor, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
)


# Index matches what Krita's ``Node.colorLabel()`` returns (0 = no label).
# Hex values are approximations of Krita 5.2's built-in label swatches;
# tweak if they drift visibly from what users see in the layer panel.
COLOR_LABELS = [
    (1, "Blue",   "#3F70B8"),
    (2, "Green",  "#57B255"),
    (3, "Yellow", "#E8C447"),
    (4, "Orange", "#E08A36"),
    (5, "Brown",  "#8C612D"),
    (6, "Red",    "#C23E3E"),
    (7, "Purple", "#A148A0"),
    (8, "Gray",   "#8E8E8E"),
]


def _swatch_icon(hex_color, size=14):
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(hex_color))
    return QIcon(pixmap)


class MergeGroupsDialog(QDialog):
    def __init__(self, parent=None, initial_selection=None):
        super().__init__(parent)
        self.setWindowTitle("Merge Groups Export")
        self.setModal(True)
        self.setMinimumWidth(320)

        preselected = set(initial_selection or ())
        self._checkboxes = {}

        layout = QVBoxLayout(self)

        intro = QLabel(
            "Groups whose color label is checked below will be flattened "
            "into a single paint layer. The result opens in a new tab — "
            "your current document is not modified."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        for idx, name, hex_color in COLOR_LABELS:
            cb = QCheckBox(name)
            cb.setIcon(_swatch_icon(hex_color))
            cb.setIconSize(QSize(14, 14))
            cb.setChecked(idx in preselected)
            cb.toggled.connect(self._refresh_ok_state)
            self._checkboxes[idx] = cb
            layout.addWidget(cb)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self._refresh_ok_state()

    def _refresh_ok_state(self):
        any_checked = any(cb.isChecked() for cb in self._checkboxes.values())
        self._buttons.button(QDialogButtonBox.Ok).setEnabled(any_checked)

    def selected_labels(self):
        return {idx for idx, cb in self._checkboxes.items() if cb.isChecked()}


def ask_color_labels(parent=None, initial_selection=None):
    """Show the dialog. Return the chosen set of label indices, or
    ``None`` if the user cancelled."""
    dlg = MergeGroupsDialog(parent, initial_selection=initial_selection)
    if dlg.exec_() != QDialog.Accepted:
        return None
    return dlg.selected_labels()

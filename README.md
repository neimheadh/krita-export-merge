# Merge Groups Export — Krita plugin

Export the current Krita document with **marked groups flattened into paint layers**, leaving the rest of the layer hierarchy intact. The result opens in a new tab — your original document is untouched.

A group is "marked" by giving it one of Krita's color labels (the colored dots on each layer). At export time, you choose which color labels trigger a merge.

## How it works

The plugin walks the layer tree from the root toward the leaves. As soon as it encounters a group whose color label is in your selection, the entire sub-tree of that group is flattened into a single paint layer. Groups with non-selected (or no) labels are kept as groups, and the recursion continues inside them.

Because the algorithm stops at the first marked group it sees on a branch, any nested marked groups are simply absorbed by their marked ancestor — you don't need to worry about nesting.

## Installation

Krita 5.2+ required.

### From a packaged zip

In Krita: **Tools → Scripts → Import Python Plugin From File…**, select `merge_groups.zip`, then restart Krita.

Enable the plugin in **Settings → Configure Krita → Python Plugin Manager**.

### Manual install

Copy `merge_groups/` and `merge_groups.desktop` into your Krita resource folder, under `pykrita/`:

- Linux: `~/.local/share/krita/pykrita/`
- macOS: `~/Library/Application Support/krita/pykrita/`
- Windows: `%APPDATA%\krita\pykrita\`

Restart Krita and enable the plugin in the Python Plugin Manager.

## Usage

1. Give a color label to each group you want flattened (right-click on a layer → choose a color).
2. **Tools → Scripts → Merge groups…**
3. In the dialog, tick the color labels that should trigger a merge.
4. A new tab opens with the merged result.

## Keyboard shortcut

The action is exposed through Krita's standard shortcuts editor. Open **Settings → Configure Krita → Keyboard Shortcuts**, search for *Merge groups*, and assign any key combo you like. No default shortcut is bound, to avoid clashing with other plugins.

## Packaging

```sh
./package.sh
```

Produces `merge_groups.zip` ready to import via Krita's plugin importer.

## Tests

The merge algorithm in `merger.py` is covered by a small unit test suite using stubs for Krita's `Node`/`Document` API (no running Krita required):

```sh
python3 -m unittest discover tests
```

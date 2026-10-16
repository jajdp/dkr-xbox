# This folder is empty on purpose

*(Español: [README.es.md](README.es.md))*

The nine package tiles are **not** distributed here: the ones used on the real console were made
from *Diddy Kong Racing*'s cover art, which is not ours to publish.

Supply your own — sizes, names and the four things that are easy to get wrong are in
[`../../docs/ASSETS.md`](../../docs/ASSETS.md) ([en español](../../docs/ASSETS.es.md)).
`tools/make_tiles.py` turns four images into the nine the manifest needs, and `tools/package_uwp.py` stops with a clear message if any is missing.

This README and its Spanish counterpart are the only files `.gitignore` lets through here, so that
the folder itself survives a fresh clone.

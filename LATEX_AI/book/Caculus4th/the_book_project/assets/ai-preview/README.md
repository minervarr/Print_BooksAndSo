# ai-preview/ — reconstructed figures for AI only

JPEGs at 300 dpi. **Not** included by `main.tex`.

| Folder | Who uses it |
|---|---|
| `scans/` | original-book crops (the model) |
| `rendered/` | FreeCAD SVG the book `\includesvg`s |
| `geometric/` `plots/` | TikZ the book `\input`s |
| **`ai-preview/`** | this dump, for a chat model to look at |

Regenerate:

```
python3 ../preview-figures.py
python3 ../preview-figures.py ch04-fig07
```

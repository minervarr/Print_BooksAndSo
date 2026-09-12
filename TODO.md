# TODO

Working notes for what is next. The product today is a CLI that writes a
notebook PDF. This file is the GUI plan and the leftover print work, not a
spec — the design spec stays in `docs/superpowers/specs/`.

## Fonts (the π failure)

Latin Modern **Roman** is a text face. It has Latin and uppercase Greek (Π)
and not lowercase π. Spivak’s mini-TOC has `16. π is Irrational` (`U+03C0`).
Furniture is glyph **outlines**, so a missing cmap entry aborts the build.

Fix in tree: `assets/fonts/latinmodern-math.otf` (GUST, same family as the
Roman faces; copied from the vk_canvas atlas baker). `FallbackGlyphs` tries
Roman/Italic first, then Math. Outlines from Math are scaled into the
primary face’s em. Still no LaTeX at runtime.

If a later book dies on another codepoint, check whether Math has it before
adding a fourth face.

## GUI — use vk_canvas, do not feed it the PDF path

`Matrix_Player/framework/vk_canvas` (and `first_party/vulkan_font_engine`)
is a **GPU UI + text** stack: Wayland window, widgets, MSDF atlas, Vulkan
shaders. That is the right toolkit for a GUI. It is the **wrong** toolkit
for writing the notebook PDF.

| Layer | Job | Engine |
|---|---|---|
| Notebook PDF | Form XObject copy + cubic outlines in the PDF | `print-books` as it is (`qpdf` + `FT_Outline_Decompose`) |
| GUI | Window, lists, preview, buttons | vk_canvas + vulkan_font_engine |

`core/` must stay ignorant of who called it. The GUI is another `cli/`: it
asks `plan_sides` / `layout_side` for data, then draws a **preview** with
vk_canvas. It does not replace `emit()`.

### Why not `vk_font_core` inside emit

`Font::emitGlyph` produces screen-pixel, Y-down cubics for a compute
rasterizer. `print-books` needs PDF user-space, Y-up, `m`/`c`/`h`/`f`.
`vk_font_core` also links Vulkan and msdfgen on desktop. We already have
the only piece that engine uses for outlines (FreeType). Wiring the whole
font engine into emit would pull a GPU stack to solve a cmap gap.

The one thing worth stealing from that tree for PDF is the **math OTF**,
which is already shipped here.

### What the GUI should be (v1)

A desktop previewer, not a typesetting app.

1. **Open a project TOML** (or a PDF → run the same `init` path).
2. **Chapter list** from `plan_sides` / the TOML — pick `--chapters`.
3. **Sheet pager** — left/right, show side kind (portrait / mini-TOC /
   content / notes / blank). This is where vk_canvas’s pager/widgets earn
   their keep.
4. **Preview** of the current side:
   - furniture (kicker, title, ticks, grid) drawn with vk_canvas text/shapes
     from `SideLayout` data, **or**
   - cheaper v1: `print-books proof`-style PNGs via `pdftoppm` after a
     throwaway emit, displayed as an image layer.
5. **Build** button → existing `emit()` to a path the user chose.
6. **Printer profile later** (duplex calibrate) as a settings panel, still
   calling core, not duplicating imposition.

Proof-via-PNG is the honest first preview: one code path for paper and
screen, no second layout engine that can drift. Live `SideLayout` drawing
is nicer once the pager exists and you care about sub-second chapter
switching without writing a PDF.

### How it would sit in the repo

```
cpp/
  core/       unchanged — still no OS, no PDF, no Vulkan
  backend/    qpdf + FreeType (PDF). vk_canvas does not belong here.
  cli/        print-books
  gui/        new executable, links printbooks_core + printbooks_backend
              + vk_canvas (add_subdirectory or a git submodule of the
              framework). OUTPUT_NAME something like print-books-gui.
```

vk_canvas would come in as a submodule (same rule as qpdf/freetype: source
in-tree). Linux host is already there (`platform/linux`). Do not add Vulkan
to `printbooks_core` or to the `print-books` CLI link line — a headless
build of the notebook tool must keep working on a machine with no GPU.

### What the GUI is not (v1)

- Not a PDF editor.
- Not booklet / saddle-stitch (still sequential leaves).
- Not an in-app TeX engine.
- Not a replacement for `./print-books` — CLI stays the batch path
  (700-page Spivak should still build without opening a window).

## Print features still open

From the original spec, still not built:

- Sampled ink bbox (`gs -sDEVICE=bbox`, ~16 pages, cached in the TOML) and
  `--fit content|page`
- `--duplex manual`, calibrate, printer profiles (`backs_order` × rotate)
- `print-books proof` (pdftoppm PNGs)
- `NotesMode.LINES` (accepted, not drawn — ticks only)
- Golden tests: dump `Plan` + content streams, C++ vs Python prototype
- TOC scrape for books with no outline
- Manual duplex shuffle (`--duplex manual`, calibrate, printer profiles).
  Sequential PDF is what we emit; the printer driver handles two-sided.

## Done enough to use

```
./print-books init BOOK.pdf
./print-books build BOOK.toml
```

`--share` / Arch packages, fallback Math font, stdlib `./print-books`
locator.

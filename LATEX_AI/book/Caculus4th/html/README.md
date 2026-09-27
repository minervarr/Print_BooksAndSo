# html/ — browser reading (MathJax)

Smoke: title through chapter 8. Graphs are SVG (`export-figures-svg.py`).
Needs JavaScript (MathJax from jsDelivr).
`python3 ../chapter.py test-html` must PASS (unknown/forbidden TeX in
MathJax spans). `build.py html` runs the same gate. Not the print book.

```
python3 ../build.py html
```

Open `index.html`. Full-book HTML is a later pass.

# kit/make/latex.mk — book + per-unit + standalone-figure PDFs.
#
# A book's Makefile sets:
#   KIT     path to this kit (e.g. ../kit)
#   FRONT   unit names in \frontmatter
#   MAIN    unit names in \mainmatter
#   BACK    unit names in \backmatter
# Optional: BUILD (default build), LATEX, UNITS (default FRONT MAIN BACK)

BUILD ?= build
LATEX ?= pdflatex -interaction=nonstopmode -halt-on-error

export TEXINPUTS := .:$(abspath $(KIT)/tex):$(TEXINPUTS)

UNITS ?= $(FRONT) $(MAIN) $(BACK)

.PHONY: book units unit figures clean

book: $(BUILD)/book.pdf

CHAPTERS := $(wildcard chapters/*.tex)
FIGURES  := $(wildcard figures/geometric/*.tex) $(wildcard figures/plots/*.tex)

$(BUILD)/book.pdf: main.tex style.tex $(KIT)/tex/packages.tex $(KIT)/tex/figure-style.tex $(CHAPTERS) $(FIGURES)
	@mkdir -p $(BUILD)
	$(LATEX) -output-directory=$(BUILD) -jobname=book main.tex
	$(LATEX) -output-directory=$(BUILD) -jobname=book main.tex

# Map a unit name to the book-class matter (no backslash — TeX \csname's it).
matter_name = $(if $(filter $(1),$(FRONT)),frontmatter,$(if $(filter $(1),$(BACK)),backmatter,mainmatter))

units: $(foreach u,$(UNITS),$(BUILD)/units/$(u).pdf)

$(BUILD)/units/%.pdf: chapters/%.tex unit.tex style.tex $(KIT)/tex/packages.tex
	@mkdir -p $(BUILD)/units
	$(LATEX) -output-directory=$(BUILD)/units -jobname=$* \
	  '\def\unitname{$*}\def\unitmattername{$(call matter_name,$*)}\input{unit.tex}'

unit:
	@test -n "$(UNIT)" || (echo "usage: make unit UNIT=<name>"; exit 1)
	$(MAKE) $(BUILD)/units/$(UNIT).pdf

FIG_TEX := $(wildcard figures/geometric/*.tex) $(wildcard figures/plots/*.tex)
FIG_PDF := $(patsubst figures/%.tex,$(BUILD)/figures/%.pdf,$(FIG_TEX))

figures: $(FIG_PDF)

$(BUILD)/figures/%.pdf: figures/%.tex $(KIT)/tex/figure-standalone.tex $(KIT)/tex/packages.tex $(KIT)/tex/figure-style.tex
	@mkdir -p $(dir $@)
	$(LATEX) -output-directory=$(dir $@) -jobname=$(basename $(notdir $<)) \
	  '\def\figfile{$<}\input{figure-standalone}'

clean:
	rm -rf $(BUILD)

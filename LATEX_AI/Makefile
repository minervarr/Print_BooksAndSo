# Convenience: run from LATEX_AI/. The real Makefile is book/Makefile.
.PHONY: book units figures unit clean
book units figures clean:
	$(MAKE) -C book $@
unit:
	$(MAKE) -C book unit UNIT=$(UNIT)

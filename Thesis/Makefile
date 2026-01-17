MAINTEX  := thesis.tex
BUILDDIR := build
LATEX    := lualatex
FLAGS    := -quiet -shell-escape -output-directory=$(BUILDDIR) -halt-on-error -synctex=1 -e '$$max_repeat=6'

.PHONY : default help pdf verbose clean veryclean

pdf :
	mkdir -p $(BUILDDIR)/chapters $(BUILDDIR)/appendices
	latexmk -$(LATEX) $(FLAGS) $(MAINTEX)
	cp $(BUILDDIR)/$(MAINTEX:tex=pdf) .

$(BUILDDIR):
	mkdir $(BUILDDIR)

help :
	@echo ""
	@echo "This Makefile creates the PDF of the thesis by using 'latexmk'"
	@echo "  make             : Generate PDF of the thesis"
	@echo "  make force       : Generate PDF of the thesis (forced mode)"
	@echo "  make verbose     : Show output from latex compiler"
	@echo "  make clean       : Delete temporary files"
	@echo "  make veryclean   : Delete temporary files including PDF"
	@echo ""


force : | $(BUILDDIR)
	latexmk -g -$(LATEX) $(FLAGS) $(MAINTEX)
	cp $(BUILDDIR)/$(MAINTEX:tex=pdf) .

verbose : | $(BUILDDIR)
	latexmk -g -$(LATEX) $(FLAGS) -verbose $(MAINTEX)
	cp $(BUILDDIR)/$(MAINTEX:tex=pdf) .

clean :
	latexmk -c
	rm -f *.lol *.fls thesis-blx.bib *.xml *.bbl
	rm -rf $(BUILDDIR)

veryclean : clean
	latexmk -C
	rm -rf $(BUILDDIR)

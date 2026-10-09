all: main.pdf
main.pdf: main.tex refs.bib numbers.tex figures/fig_resonator.pdf
	pdflatex -interaction=nonstopmode main.tex >/dev/null || true
	bibtex main >/dev/null || true
	pdflatex -interaction=nonstopmode main.tex >/dev/null || true
	pdflatex -interaction=nonstopmode main.tex | grep -E "Output written|Error|Warning: (Citation|Reference)" || true
numbers.tex:
	cd .. && python3 sim/make_figures.py
clean:
	rm -f main.aux main.bbl main.blg main.log main.out main.pdf

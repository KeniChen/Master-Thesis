# Master’s Thesis LaTeX Project (Reader-Friendly Guide)

This repository contains the LaTeX source code for my master’s thesis. The main entry point is `thesis.tex`, based on the template `template/acsthesis.cls`. The recommended build pipeline is **LuaLaTeX + biber**.

## Repository Structure (What You’ll Likely Use)

* `thesis.tex`: Main file (title, author info, chapter includes/references, etc.)
* `chapters/`: Thesis chapters (e.g., `Introduction.tex`, `Methods.tex`, …)
* `abstract/`: Abstracts (English and German)
* `appendices/`: Appendices
* `bibliography.bib`: Bibliography database (biblatex + biber)
* `graphics/`: Figures and image assets
* `template/`: Thesis template files (usually no need to modify)
* `Makefile`: One-command build script (**recommended**)
* `build/`: Build artifacts / intermediate files

## Quick Start (The Easiest Way)

1. Install a LaTeX distribution (see platform-specific instructions below).
2. Run the following in the project root:

   ```bash
   make
   ```
3. The output `thesis.pdf` will be generated in the project root directory.

## Installation and Setup by Platform

### Linux (Ubuntu / Debian / Mint, etc.)

Install the following packages (sufficient to build this project):

```bash
sudo apt update
sudo apt install -y texlive-latex-recommended texlive-lang-german \
  texlive-latex-extra texlive-science texlive-bibtex-extra texlive-luatex
```

If you prefer a full installation (large download and disk usage):

```bash
sudo apt install -y texlive-full
```

### Linux (Fedora)

Package names differ on Fedora. Please refer to the dependency list in
`utils/Dockerfile_fedora` and install accordingly.

### macOS

Install **MacTeX** (the official TeX Live distribution for macOS):

* Website: [http://www.tug.org/mactex/](http://www.tug.org/mactex/)

After installation, it is recommended to update:

```bash
tlmgr update --self --all
```

### Windows

Recommended distributions:

* **MiKTeX** (lightweight, installs packages on demand)
* **TeX Live** (more complete, larger; full install recommended)

Notes:

* This project uses `biber` — make sure it is included or installable in your distribution.
* If you use `xindy` for sorting (e.g., advanced indexing/glossaries), you may need an additional Perl installation.
* Alternatively, you can compile via **WSL2 + a Linux distribution**, which works especially well with VS Code.

## Build Options (Choose One)

### Option A: `make` (Recommended)

```bash
make
```

### Option B: `latexmk`

```bash
latexmk --lualatex thesis.tex --shell-escape --silent
```

Continuous build (auto recompile on file changes):

```bash
latexmk --lualatex thesis.tex --shell-escape --silent --pvc
```

### Option C: Manual Build (Useful for Debugging)

```bash
lualatex -shell-escape thesis.tex
biber thesis
lualatex -shell-escape thesis.tex
lualatex -shell-escape thesis.tex
```

## Where to Start Editing

* Basic metadata: `thesis.tex` (title, author, student ID, supervisor, etc.)
* Chapter content: files under `chapters/`
* Abstracts: `abstract/english.tex`, `abstract/german.tex`
* References: `bibliography.bib`
* Figures/images: `graphics/`

## Cleaning Build Artifacts

```bash
make clean
```

Full cleanup (including the PDF):

```bash
make veryclean
```

## Troubleshooting

* **`biber` not found**: Ensure `biber` is installed (e.g., `tlmgr install biber`)
* **Missing LaTeX packages**: On TeX Live, install via `tlmgr install <package>`
* **Compilation issues related to German/English hyphenation**: The template enables `ngerman,english`; ensure language packages and fonts are properly installed
* **`minted` errors**: `minted` is commented out in the template; if you enable it, make sure `pygments` is installed

## Recommended Editors

* **VS Code** + LaTeX Workshop (great build + preview experience)
* **TeXstudio** (lightweight and well integrated)

Optional tools for grammar/spell checking:

* VS Code: LTeX / Spell Right
* TeXstudio: LanguageTool


# LaTeX

This is how the compiled thesis looks like: [pdf](https://git-ce.rwth-aachen.de/acs/internal/templates/thesis/-/jobs/artifacts/master/raw/thesis.pdf?job=build_ubuntu)

## Installation

### Linux

The package for most Linux Distributions is named _Texlive_. On Linux we strongly recomend the use of _LuaLaTeX_ to build the thesis. LuaLaTeX should be part of every normal Latex installation.

#### Ubuntu

This template requires a bit more than the standard packages. On Ubuntu/Debian/Mint/PoP_OS/... you can install the following files:

```shell
apt update && apt install -y texlive-latex-recommended texlive-lang-german texlive-latex-extra texlive-science texlive-bibtex-extra texlive-luatex
```

If you want to be sure, you can install the full blown version. But this requires a few free Gigabyte on your harddrive.

```shell
apt update && apt install -y texlive-full
```

#### Fedora

See [the Dockerfile](utils/Dockerfile_fedora) for a list of minimal packages to be installed to build the thesis.

### Windows

On Windows there are multiple LaTeX distributions. 
- [MiKTeX](https://miktex.org/)
- [Texlive](http://www.tug.org/texlive/)
- [proTeXt](http://www.tug.org/protext/)

Texlive has the advantage of bundling Perl, which might be needed depending on
which packages you use. As an example, if you want to use `glossaries` and wish
to have the glossary sorted (with support for non-Latin characters), you will 
want to use `xindy`, which requires Perl to be installed.
The full Texlive package does take a long time (>1h) to install on Windows.

You may also consider using LaTeX on the [WSL2](https://docs.microsoft.com/en-us/windows/wsl/compare-versions)
subsystem. This works very well in combination with [VS code](https://code.visualstudio.com/). 
In this case you should keep your project in the WSL2 Filesystem.


### MacOS 

The macOS package is called _MacTeX_. Please take a look at the [official site](http://www.tug.org/mactex/) for installation instructions.

## Get an Editor

You can write your thesis in any kind of *Text*-editor you like. However, there exist full-fledged IDEs which provide syntax highlighting, autocompletion, etc.
A good and free IDE is [TeXstudio](https://www.texstudio.org/).
[VS code](https://code.visualstudio.com/) also works well in combination with 
the [LaTex Workshop](https://marketplace.visualstudio.com/items?itemName=James-Yu.latex-workshop)
extension.

### Spellchecking / Grammar checking

TeXstudio offers spell- and grammar checking if you install the [languagetool](https://languagetool.org/compare)
stand-alone. VS code offers a similar integration with the [LTeX](https://marketplace.visualstudio.com/items?itemName=valentjn.vscode-ltex) 
extension. 
Both ignore text inserted by LaTeX commands, such as `\gls` which is used 
for acronyms and glossaries.
Also advanced error detection rules from languagetoolplus (paid)
are not available.

For VS code the [Spell Right](https://marketplace.visualstudio.com/items?itemName=ban.spellright)
is another extension which provides less false positives, but does not offer
grammar checking. 

You might also consider importing the PDF into MS Word for spell and grammar checking.
This works reasonably well, however you will have a lot of false positives
regarding hyphenation and usage of multiple spaces. A solution for that is 
putting `\raggedright` before the beginning of your main document. This disables 
auto-hyphenation and improves the space recognition by Word, since spaces now
have a constant length. Do remember to remove `\raggedright` from your document
for the final version!  
Using MS Word also has the 
advantage, that there are many third party addons for grammar checking,
such as Grammarly or Duden Mentor.


## Build the PDF

There are multiple options:

- **Command line with `make`**: Go to the main directory of the thesis and execute `make`
- **Command line with `latexmk`**: Go to the main directory of the thesis and execute `latexmk --lualatex thesis.tex  --shell-escape --silent`.
  If you execute `latexmk --lualatex thesis.tex  --shell-escape --silent --pvc` instead, then the _thesis.pdf_ will be rebuilt automatically, every time you change one of the source files.
- **IDE Integration**: TODO

## How to use this template 😕❓

Modify the file `thesis.tex` and enter your Name and the other thesis' dates.
You don't have to add Prof. Monti, Prof. Ponci as your supervisor. Prof. Monti is set by default.

Now you can start editing the files in `chapters/` and `abstract/`.

*Happy Writing* ✍ 🙂👍

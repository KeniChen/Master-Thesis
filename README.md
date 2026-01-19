# Master Thesis - Keni Chen

## Overview
- Thesis: LaTeX sources for the thesis document.
- Code: LLM-based Semantic Annotation Platform (backend, frontend, data).

## Quick start
- Thesis: `cd Thesis` then `make` (or `latexmk --lualatex thesis.tex --shell-escape --silent`).
- Code: `cd Code` then `make setup`, edit `data/config.json`, upload ontologies, tables and labels in `data/ontologies`, `data/tables/real` and  `data/tables/real`, and `make dev`.

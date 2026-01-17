\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{acsthesis}[2015/05/21 Template for Student Theses at ACS]

\LoadClass[12pt, 				% Fontsize
           a4paper,				% Paper format
           listof=totoc,		% 'List of Tables' and 'List of Figures' in table of contents (toc)
           numbers=noenddot, 	% Deactivate dot behind last number in toc
           index=totoc,			% Add index to toc
           BCOR=1cm,			% additional margin for binding
           ]{scrbook}

%------------------------------------------------------------------------------%
% Include packages
%------------------------------------------------------------------------------%
\RequirePackage{ifluatex}					% See if below
\ifluatex 									% Using lualatex is recommended
    \RequirePackage{fontspec}				% See https://tex.stackexchange.com/a/413046
    \setsansfont{CMU Sans Serif}			% {Arial}
    \setmainfont{CMU Serif}					% {Times New Roman}
    \setmonofont{CMU Typewriter Text}		% {Consolas}
    \defaultfontfeatures{Ligatures={TeX}}
\else										% For compatiblity with pdflatex
    \RequirePackage[utf8]{inputenc}
    \RequirePackage[T1]{fontenc}			% West-European Encoding of the output PDF
    \RequirePackage{lmodern} 				% Use modern Linux fonts
\fi
\RequirePackage{graphicx} 					% Include graphics via 'includegraphic'
\RequirePackage{makeidx} 					% Create an index if desired
\RequirePackage[binary-units]{siunitx} 		% Nice numbers with units
\RequirePackage{hyperref} 					% Links within document
\RequirePackage{hyperxmp}					% Add Metadata in Adobe compatible way
\RequirePackage{xparse} 					% NewDocumentCommand etc.
\RequirePackage{etoolbox} 					% If-then-else
\RequirePackage{ifthen} 					% If-then-else
\RequirePackage[shorthands=off]{babel} 		% Disable e.g. "a ->ä.
\RequirePackage{booktabs} 					% nicer tables
\RequirePackage{tikz} 						% draw pictures
\RequirePackage{pgfplots} 					% use for printing diagrams
\RequirePackage{listings}
\RequirePackage{relsize}
\RequirePackage{csquotes}                   % To prevent warning "'babel/polyglossia' detected but 'csquotes' missing"



% Prevent single lines to be printed on the next page
\clubpenalty = 10000
\widowpenalty = 10000
\displaywidowpenalty = 10000

%For German hyphenation in statement and admonition
\hyphenation{Vor-schrif-ten}
%------------------------------------------------------------------------------%
% Command and environment definitions
%------------------------------------------------------------------------------%
\newcommand{\addinstitute}[3]{}                 % Institute hinzufuegen
                                                %  #1 Kuerzel fuer Referenz, z.B. lfbs
                                                %  #2 Titel des Instituts, z.B. Chair for OS, RWTH Aachen University
                                                %  #3 Referenzzeichen, z.B. (*) oder irgendein Symbol


\newcommand{\printinstitutes}{}
\newcommand{\printsupervisors}{}
\newcommand{\printsecondreferees}{}

% ----- Abstract (german and english)
\addto\captionsgerman{%
    \RenewDocumentCommand \abstractname {} {Kurzfassung}
    \def\@keywordName{Stichwörter}
    \def\@keywords{\@keywordsDE}
}
\addto\captionsngerman{%
    \RenewDocumentCommand \abstractname {} {Kurzfassung}
    \def\@keywordName{Stichwörter}
    \def\@keywords{\@keywordsDE}
}
\addto\captionsenglish{%
    \def\@keywordName{Keywords}
    \def\@keywords{\@keywordsEN}
}

\NewDocumentEnvironment{abstract}{}%
{
    \addchap*{\abstractname}
}%
{%end-defs
    \bigskip\par
    \textbf{\@keywordName:} \@keywords
}

% ----- User commands
\def\@titleEN{\@title}
\def\@thesisType{Unknown Thesis Type}
\NewDocumentCommand \titleDE         { m } {\def\@titleDE{#1}}
\NewDocumentCommand \titleEN         { m } {\def\@titleEN{#1}}
\NewDocumentCommand \matrNr          { m } {\def\@matrNr{#1}}
\NewDocumentCommand \addSupervisor   { m } {\edef\@supervisors{#1}}
\NewDocumentCommand \keywordsDE      { m } {\def\@keywordsDE{#1}}
\NewDocumentCommand \keywordsEN      { m } {\def\@keywordsEN{#1}}
\NewDocumentCommand \thesisType      { m } {%
    \ifstrequal{#1}{master}{%
        \iflanguage{ngerman}{%
            \def\@thesisType{Masterarbeit}
        }{%
            \def\@thesisType{Master Thesis}
        }
        \def\@thesisTypeDeclaration{Masterarbeit}
    }{%
    }
    \ifstrequal{#1}{bachelor}{%
        \iflanguage{ngerman}{%
            \def\@thesisType{Bachelorarbeit}
        }{%
            \def\@thesisType{Bachelor Thesis}
        }
        \def\@thesisTypeDeclaration{Bachelorarbeit}
    }{%
    }
}
\newtoggle{printSignatures}
\togglefalse{printSignatures}
\NewDocumentCommand \printSignatures      {   } {%
    \toggletrue{printSignatures}
}


%
% Institut hinzufuegen (falls mehrere Institute/Firmen involviert)
%  #1 Kuerzel (zur Verwendung mit \instituteref)
%  #2 Kompletter Name des Instituts
%  #3 Symbol zur Kennzeichnung von Betreuer/Institut
%
\newtoggle{printInstitutes}
\togglefalse{printInstitutes}
\renewcommand{\printinstitutes}{}
\newcommand{\instref}{}
\renewcommand{\addinstitute}[3]{%
    \expandafter\def\csname instref#1\endcsname{#3}%          % Definiere z.B. \instreflfbs als #3
    \expandafter\def\csname instname#1\endcsname{#2}%         % Definiere z.B. \instnamelfbs als #2
    % Neues Institut an "Tabelle" anhaengen
    \protected@edef\printinstitutes{\printinstitutes#3 #2\\}% % \printinstitutes expandieren und mit Zusatz
                                                              %   wieder speichern
    \toggletrue{printInstitutes}%                       % Wenn wir ein Inst. definiert haben, auch drucken
}
% Anwenderbefehl zum referenzieren des Instituts
\NewDocumentCommand \instituteref { m }{                            % Definiere z.B. \instituteref{lfbs} als \instreflfbs
    \expandafter\csname instref#1\endcsname
%	\csdef{instref#1}{}
}


%
% Betreuer hinzufuegen
%
\newlength{\@templength}
\newlength{\@supervisorlength}                        % Laenge des laengsten Betreuernamens
\newlength{\@supervisorlabellength}                   % Laenge des laengsten Betreuerlabels (Betreuer, Zweitgutachter etc.)
\newlength{\@supervisornamelength}                    % Laenge des Betreuerlabels (z.B. Betreuer)
\newlength{\@secondrefereenamelength}                 % Laenge des Zweitgutachterlabels (z.B. Zweitgutachter)


\NewDocumentCommand \addsupervisor { O{} m }{%
    \ifcsundef{instref#1}{% \instrefxyz not defined
          \ClassError{acsthesis}
                     {Institute "#1" not defined. Institute must be defined before using a reference to it}
                     {Please define institute before using a reference to it.}
    }{%else
        \settowidth{\@templength}{#2 \instituteref{#1}}
        \ifnumcomp{\@templength}{>}{\@supervisorlength}{%
            \setlength{\@supervisorlength}{\@templength}
        }{%else
        }
        % Neuen Betreuer an "Tabelle" anhaengen
        \ifthenelse{\equal{\printsupervisors}{}}
            {\g@addto@macro\printsupervisors{#2 \instituteref{#1}}}    %1. Eintrag
            {\g@addto@macro\printsupervisors{\\ #2 \instituteref{#1}}} %Folgende Eintraege
    }
}

%
% Zweitgutachter hinzufuegen
%
\newtoggle{secondReferee}
\togglefalse{secondReferee}
\NewDocumentCommand \addsecondreferee { O{} m }{%
    \ifcsundef{instref#1}{% \instrefxyz not defined
          \ClassError{acsthesis}
                     {Institute "#1" not defined. Institute must be defined before using a reference to it}
                     {Please define institute before using a reference to it.}
    }{%else
        \settowidth{\@templength}{#2 \instituteref{#1}}
        \ifthenelse{\@templength>\@supervisorlength}
            {\setlength{\@supervisorlength}{\@templength}}%true
            {}%false
        % Neuen Zweitgutachter an "Tabelle" anhaengen
        \ifthenelse{\equal{\printsecondreferees}{}}
            {\g@addto@macro\printsecondreferees{#2 \instituteref{#1}}}    %1. Eintrag
            {\g@addto@macro\printsecondreferees{\\ #2 \instituteref{#1}}} %Folgende Eintraege
        \toggletrue{secondReferee}
    }
}


% ----- Statement of authorship
\NewDocumentCommand \statementOfAuthorship { } {%
    \thispagestyle{empty}

    %\vspace*{\stretch{2}}

    \@statement
    \vspace{0.5cm}
    \@datesignature \\
    %\vspace{\stretch{1}}
    \vspace{1cm}

    \@admonition
    \vspace{0.5cm}
    \@datesignature
    %\vspace{\stretch{1}}
}

\def\@statement{%
    \subsection*{Eidesstattliche Versicherung}
    Ich, \@author{} (Matrikelnummer \@matrNr{}), versichere hiermit an Eides Statt, dass ich die vorliegende \@thesisTypeDeclaration{} mit dem Titel
    \begin{center}
    \textit
    \@titleDE
    \end{center}
    selbstständig und ohne unzulässige fremde Hilfe erbracht habe. Ich habe keine anderen als die angegebenen Quellen und Hilfsmittel benutzt. Für den Fall, dass die Arbeit zusätzlich auf einem Datenträger eingereicht wird, erkläre ich, dass die schriftliche und die elektronische Form vollständig übereinstimmen. Die Arbeit hat in gleicher oder ähnlicher Form noch keiner Prüfungsbehörde vorgelegen.

    \vspace{.5cm}
}

\def\@admonition{%
    \subsection*{Belehrung}
    \subsubsection*{\smaller \S 156 StGB: Falsche Versicherung an Eides Statt}
    {\smaller%
    Wer vor einer zur Abnahme einer Versicherung an Eides Statt zuständigen Behörde eine solche Versicherung falsch abgibt oder unter Berufung auf eine solche Versicherung falsch aussagt, wird mit einer Freiheitsstrafe bis zu drei Jahren oder mit Geldstrafe bestraft.
    }

    \subsubsection*{\smaller \S 161 StGB: Fahrlässiger Falscheid; fahrlässige falsche Versicherung an Eides Statt}
    {\smaller%
    \begin{itemize}
        \item[(1)] Wenn eine der in den \S\S{} 154 bis 156 bezeichneten Handlungen aus Fahrlässigkeit begangen worden ist, so tritt Freiheitsstrafe bis zu einem Jahr oder Geldstrafe ein.
        \item[(2)] Straflosigkeit tritt ein, wenn der Täter die falsche Angabe rechtzeitig berichtigt. Die Vorschriften des \S 158 Abs. 2 und 3 gelten entsprechend.
    \end{itemize}
    Die vorstehende Belehrung habe ich zur Kenntnis genommen:
    }

    \vspace{.5cm}
}

% ----- Language dependent variables
\iflanguage{ngerman}{%
    \def\@tpName{Titelseite}
    \def\@tocName{Inhaltsverzeichnis}
    \def\@mainTitle{\@titleDE}
    \def\@subTitle{\@titleEN}
    \def\@matrNrName{Matrikelnummer}
    \def\@supervisorName{Betreuer}
    \def\@secondRefereeName{Zweitgutachter}
    \def\@firstExaminer{Erstprüfer}
    \def\@secondExaminer{Zweitprüfer}
    \def\@datesignature{\makebox[6cm]{\hrulefill} \hfill \makebox[7cm]{\hrulefill} \makebox[6cm]{Ort, Datum} \hfill \makebox[7cm]{Unterschrift}}
    \def\@rwthAcsName{%
        Diese Arbeit wurde vorgelegt an der\\
        Rheinisch-Westfälischen Technischen Hochschule Aachen\\
        Fakultät für Elektrotechnik und Informationstechnik\\
        Lehrstuhl für Automation of Complex Power Systems\\
        Univ.-Prof. Antonello Monti, Ph.\,D.
    }
}{%
    \renewcommand\lstlistlistingname{List of Listings}
%
    \def\@tpName{Title Page}
    \def\@tocName{Table of Contents}
    \def\@mainTitle{\@titleEN}
    \def\@subTitle{\@titleDE}
    \def\@matrNrName{Matriculation Number}
    \def\@supervisorName{Supervisor}
    \def\@secondRefereeName{Second Referee}
    \def\@firstExaminer{1\textsuperscript{st} Examiner}
    \def\@secondExaminer{2\textsuperscript{nd} Examiner}
    \def\@datesignature{ \makebox[6cm]{\hrulefill} \hfill \makebox[7cm]{\hrulefill} \makebox[6cm]{Ort, Datum} \hfill \makebox[7cm]{Unterschrift}}
    \def\@rwthAcsName{%
        The present work was submitted to \\
        RWTH Aachen University\\
        Faculty of Electrical Engineering and Information Technology\\
        Institute for Automation of Complex Power Systems\\
        Univ.-Prof. Antonello Monti, Ph.\,D.
    }
}

\input{template/titlepage}

\NewDocumentCommand \appendixintro {} {%
    \chapter*{} 				% TODO: Can we omit this dirty hack?
    \thispagestyle{empty}
    {%
        \centering
        \vfill
        \Huge\bfseries\sffamily
        Appendix
        \vfill
    }
}


%------------------------------------------------------------------------------%
% Create cover, table of contents, etc.
%------------------------------------------------------------------------------%
\AtBeginDocument{%
% Everything before the first chapter with roman page numbers
    \frontmatter
    \maketitle
    \cleardoublepage
    \statementOfAuthorship
    \cleardoublepage
    \phantomsection\pdfbookmark{\abstractname}{abstract}

    % German abstract
    \IfFileExists{abstract/german.tex}{
        \begin{otherlanguage}{ngerman}
            \begin{abstract}
                \input{abstract/german}
            \end{abstract}
        \end{otherlanguage}
    }{}%
    % English abstract
    \IfFileExists{abstract/german.tex}{
        \begin{otherlanguage}{english}
            \begin{abstract}
                \input{abstract/english}
            \end{abstract}
        \end{otherlanguage}
    }{}%
    \cleardoublepage
    \phantomsection\pdfbookmark{\@tocName}{toc}
    \tableofcontents

% Here comes the students code
\mainmatter
}

\AtEndDocument{%
    \printbibliography
    \addcontentsline{toc}{chapter}{Bibliography}
    \printindex
}

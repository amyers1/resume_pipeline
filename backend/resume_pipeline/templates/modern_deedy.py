"""
Modern Deedy template implementation.
"""

from .base import BaseTemplate


class ModernDeedyTemplate(BaseTemplate):
    """Modern Deedy resume template."""

    def get_template_string(self) -> str:
        """Return Modern Deedy Jinja2 template."""
        return r"""\documentclass[]{resume-openfont}

\pagestyle{fancy}
\resetHeaderAndFooter

\newcommand{\resumeHeading}[4]{\runsubsection{\uppercase{#1}}\descript{ | #2}\hfill\location{#3 | #4}\fakeNewLine}
\newcommand{\educationHeading}[4]{\runsubsection{#1}\hspace*{\fill}\location{#3 | #4}\\\descript{#2}\fakeNewLine}

\newcommand{\yourName}{\VAR{full_name}}
\newcommand{\yourEmail}{\VAR{email}}
\newcommand{\yourPhone}{\VAR{phone}}
\newcommand{\linkedInUserName}{\VAR{linkedin}}

\begin{document}

\begin{center}
    \Huge \scshape \latoRegular{\yourName} \\ \vspace{1pt}
    \small \href{mailto:\yourEmail}{\underline{\yourEmail}} $|$ \yourPhone $|$
    \href{https://www.linkedin.com/in/\linkedInUserName}{\underline{linkedIn/\linkedInUserName}}
\end{center}

\section{Professional Summary}
\noindent
\BLOCK{for line in professional_summary}
\VAR{line | latex_escape}\BLOCK{if not loop.last} \ \BLOCK{endif}
\BLOCK{endfor}
\sectionsep

\section{Core Competencies}
\begin{bullets}
\BLOCK{for comp in core_competencies}
    \item \VAR{comp | latex_escape}
\BLOCK{endfor}
\end{bullets}
\sectionsep

\section{Work Experience}
\BLOCK{set grouped_section = namespace(started=false)}
\BLOCK{for exp in experience}
\BLOCK{if exp.is_grouped and not grouped_section.started}
\BLOCK{set grouped_section.started = true}
\resumeHeading{Other Relevant Experience}}{}}{Various Locations}}{2006--2016}
\BLOCK{endif}
\BLOCK{if exp.is_grouped}
\begin{bullets}
\BLOCK{for bullet in exp.bullets}
    \item \VAR{bullet | latex_escape}
\BLOCK{endfor}
\end{bullets}
\BLOCK{else}
\resumeHeading{\VAR{exp.organization | latex_escape}}{\VAR{exp.title | latex_escape}}{\VAR{exp.location | latex_escape}}{\VAR{exp.start_date | latex_escape}--\VAR{exp.end_date | latex_escape}}
\begin{bullets}
\BLOCK{for bullet in exp.bullets}
    \item \VAR{bullet | latex_escape}
\BLOCK{endfor}
\end{bullets}
\sectionsep
\BLOCK{endif}
\BLOCK{endfor}

\section{Education}
\BLOCK{for edu in education}
\educationHeading{\VAR{edu.degree | latex_escape}}{\VAR{edu.institution | latex_escape}}{\BLOCK{if edu.location}\VAR{edu.location | latex_escape}\BLOCK{endif}}{\VAR{edu.graduation_date | latex_escape}}
\BLOCK{endfor}
\sectionsep

\BLOCK{if certifications}
\section{Certifications}
\begin{bullets}
\BLOCK{for cert in certifications}
    \item \VAR{cert.name | latex_escape}\BLOCK{if cert.issuer}, \VAR{cert.issuer | latex_escape}\BLOCK{endif}\BLOCK{if cert.date} (\VAR{cert.date | latex_escape})\BLOCK{endif}
\BLOCK{endfor}
\end{bullets}
\sectionsep
\BLOCK{endif}

\BLOCK{if awards}
\section{Awards}
\begin{bullets}
\BLOCK{for award in awards}
    \item \VAR{award.title | latex_escape}\BLOCK{if award.date} (\VAR{award.date | latex_escape})\BLOCK{endif}
\BLOCK{endfor}
\end{bullets}
\sectionsep
\BLOCK{endif}

\end{document}"""

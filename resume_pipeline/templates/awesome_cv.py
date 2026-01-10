"""
Awesome CV template implementation.
"""

from .base import BaseTemplate


class AwesomeCVTemplate(BaseTemplate):
    """Awesome CV resume template."""

    def get_template_string(self) -> str:
        """Return Awesome CV Jinja2 template."""
        return r"""%!TEX TS-program = xelatex
%!TEX encoding = UTF-8 Unicode

\documentclass[11pt, a4paper]{awesome-cv}

\geometry{left=1.4cm, top=.8cm, right=1.4cm, bottom=1.8cm, footskip=.5cm}

\fontdir[fonts/]

\colorlet{awesome}{awesome-red}

\name{\VAR{full_name.split()[0]}}{\VAR{' '.join(full_name.split()[1:])}}
\position{\VAR{role_title | latex_escape}}
\address{\VAR{location | latex_escape}}

\mobile{\VAR{phone}}
\email{\VAR{email}}
\linkedin{\VAR{linkedin.replace('linkedin.com/in/', '')}}

\makecvfooter
  {\today}
  {\VAR{full_name}~~~·~~~Résumé}
  {\thepage}

\begin{document}

\makecvheader[C]

\cvsection{Summary}
\begin{cvparagraph}
\BLOCK{for line in professional_summary}
\VAR{line | latex_escape}\BLOCK{if not loop.last} \BLOCK{endif}
\BLOCK{endfor}
\end{cvparagraph}

\cvsection{Skills}
\begin{cvskills}
\BLOCK{set skills_per_row = 3}
\BLOCK{for i in range(0, core_competencies|length, skills_per_row)}
  \cvskill
    {}
    {\BLOCK{for comp in core_competencies[i:i+skills_per_row]}\VAR{comp | latex_escape}\BLOCK{if not loop.last}, \BLOCK{endif}\BLOCK{endfor}}
\BLOCK{endfor}
\end{cvskills}

\cvsection{Experience}
\BLOCK{set grouped_section = namespace(started=false)}
\BLOCK{for exp in experience}
\BLOCK{if exp.is_grouped and not grouped_section.started}
\cvsubsection{Other Relevant Experience}
\BLOCK{set grouped_section.started = true}
\BLOCK{endif}
\begin{cventries}
  \cventry
    {\VAR{exp.title | latex_escape}}
    {\VAR{exp.organization | latex_escape}}
    {\VAR{exp.location | latex_escape}}
    {\VAR{exp.start_date | latex_escape}--\VAR{exp.end_date | latex_escape}}
    {
      \begin{cvitems}
\BLOCK{for bullet in exp.bullets}
        \item {\VAR{bullet | latex_escape}}
\BLOCK{endfor}
      \end{cvitems}
    }
\end{cventries}
\BLOCK{endfor}

\cvsection{Education}
\begin{cventries}
\BLOCK{for edu in education}
  \cventry
    {\VAR{edu.degree | latex_escape}}
    {\VAR{edu.institution | latex_escape}}
    {\BLOCK{if edu.location}\VAR{edu.location | latex_escape}\BLOCK{endif}}
    {\BLOCK{if edu.graduation_date}\VAR{edu.graduation_date | latex_escape}\BLOCK{endif}}
    {}
\BLOCK{endfor}
\end{cventries}

\cvsection{Certifications}
\begin{cvhonors}
\BLOCK{for cert in certifications}
  \cvhonor
    {}
    {\VAR{cert | latex_escape}}
    {}
    {}
\BLOCK{endfor}
\end{cvhonors}

\cvsection{Awards \& Honors}
\begin{cvhonors}
\BLOCK{for award in awards}
  \cvhonor
    {}
    {\VAR{award | latex_escape}}
    {}
    {}
\BLOCK{endfor}
\end{cvhonors}

\end{document}"""

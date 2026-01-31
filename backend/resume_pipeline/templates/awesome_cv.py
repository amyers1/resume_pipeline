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

\colorlet{awesome}{awesome-darknight}

\name{\VAR{full_name.split()[0]}}{\VAR{' '.join(full_name.split()[1:])}}
\position{\VAR{role_title | latex_escape}}
\address{\VAR{location | latex_escape}}

\mobile{\VAR{phone}}
\email{\VAR{email}}
\linkedin{\VAR{linkedin.replace('www.linkedin.com/in/', '')}}

%\makecvfooter
%  {\today}
%  {\VAR{full_name}~~~·~~~Résumé}
%  {\thepage}

\begin{document}

\makecvheader[C]

% --- 1. SUMMARY ---
\cvsection{Summary}

\begin{cvparagraph}
\BLOCK{for line in professional_summary}
\VAR{line | latex_escape}
\BLOCK{endfor}
\end{cvparagraph}

% --- 2. CORE COMPETENCIES ---
\cvsection{Core Competencies}

\begin{cvcompetencies}
\BLOCK{for line in core_competencies}
  \item \VAR{line | latex_escape}
\BLOCK{endfor}
\end{cvcompetencies}

% --- 3. EXPERIENCE ---
\cvsection{Experience}

\begin{cventries}
\BLOCK{for exp in experience}
\BLOCK{if not exp.is_grouped}
  \cventry
    {\VAR{exp.role_title | latex_escape}}
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
\BLOCK{endif}
\BLOCK{endfor}
  \cventry
    {Other Relevant Experience}
    {Multiple}
    {Various Locations}
    {2006--2016}
    {
      \begin{cvitems}
\BLOCK{for exp in experience}
\BLOCK{if exp.is_grouped}
\BLOCK{for bullet in exp.bullets}
        \item {\VAR{bullet | latex_escape}}
\BLOCK{endfor}
\BLOCK{endif}
\BLOCK{endfor}
      \end{cvitems}
    }

\end{cventries}

% --- 4. EDUCATION ---
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

% --- 5. CERTIFICATIONS ---
\BLOCK{if certifications}
\cvsection{Certifications}
\begin{cvhonors}
\BLOCK{for cert in certifications}
  \cvhonor
    {\VAR{cert.name | latex_escape}}
    {\BLOCK{if cert.issuer}\VAR{cert.issuer | latex_escape}\BLOCK{endif}}
    {}
    {\BLOCK{if cert.date}\VAR{cert.date | latex_escape}\BLOCK{endif}}
\BLOCK{endfor}
\end{cvhonors}
\BLOCK{endif}

% --- 6. AWARDS ---
\BLOCK{if awards}
\cvsection{Awards}
\begin{cvhonors}
\BLOCK{for award in awards}
  \cvhonor
    {\VAR{award.title | latex_escape}}
    {\BLOCK{if award.awarder}\VAR{award.awarder | latex_escape}\BLOCK{endif}}
    {}
    {\BLOCK{if award.date}\VAR{award.date | latex_escape}\BLOCK{endif}}
\BLOCK{endfor}
\end{cvhonors}
\BLOCK{endif}

\end{document}"""

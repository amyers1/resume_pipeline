# LaTeX Template Setup Guide

This guide explains how to set up the LaTeX template files needed for PDF compilation.

## Overview

The pipeline generates LaTeX (`.tex`) files but needs template class files (`.cls`) to compile them to PDF. You need to download these template files from their respective GitHub repositories.

## Required Structure

```
resume-pipeline/
├── templates/                    # ← Create this directory
│   ├── resume-openfont.cls      # ← For Modern Deedy
│   ├── awesome-cv.cls           # ← For Awesome CV
│   └── fontawesome.sty          # ← For Awesome CV icons
├── resume_pipeline/
├── jobs/
└── output/
```

## Template 1: Modern Deedy

### Download Template Files

**Repository:** https://github.com/Aarif123456/modern-deedy

```bash
# From project root
mkdir -p templates

# Download the .cls file
curl -o templates/resume-openfont.cls \
  https://raw.githubusercontent.com/Aarif123456/modern-deedy/master/resume-openfont.cls
```

**Or manually:**
1. Visit https://github.com/Aarif123456/modern-deedy
2. Download `resume-openfont.cls`
3. Place in `templates/` directory

### Required Files
- ✅ `resume-openfont.cls` - Main template class

### Compilation
- **Engine:** pdflatex
- **Packages:** Standard LaTeX (included in texlive-latex-extra)

## Template 2: Awesome CV

### Download Template Files

**Repository:** https://github.com/posquit0/Awesome-CV

```bash
# From project root
mkdir -p templates

# Download required files
curl -o templates/awesome-cv.cls \
  https://raw.githubusercontent.com/posquit0/Awesome-CV/master/awesome-cv.cls

curl -o templates/fontawesome.sty \
  https://raw.githubusercontent.com/posquit0/Awesome-CV/master/fontawesome.sty
```

**Or manually:**
1. Visit https://github.com/posquit0/Awesome-CV
2. Download `awesome-cv.cls`
3. Download `fontawesome.sty`
4. Place both in `templates/` directory

### Required Files
- ✅ `awesome-cv.cls` - Main template class
- ✅ `fontawesome.sty` - Icon package

### Compilation
- **Engine:** xelatex
- **Packages:** Requires xelatex and fonts (included in texlive-xetex)

## Quick Setup Script

Create `setup_templates.sh`:

```bash
#!/bin/bash
# Setup LaTeX templates

set -e

echo "Setting up LaTeX templates..."

# Create templates directory
mkdir -p templates

# Modern Deedy
echo "Downloading Modern Deedy template..."
curl -sL -o templates/resume-openfont.cls \
  https://raw.githubusercontent.com/Aarif123456/modern-deedy/master/resume-openfont.cls

# Awesome CV
echo "Downloading Awesome CV template..."
curl -sL -o templates/awesome-cv.cls \
  https://raw.githubusercontent.com/posquit0/Awesome-CV/master/awesome-cv.cls

curl -sL -o templates/fontawesome.sty \
  https://raw.githubusercontent.com/posquit0/Awesome-CV/master/fontawesome.sty

echo "✓ Templates downloaded successfully!"
echo ""
echo "Templates directory contents:"
ls -lh templates/

echo ""
echo "You can now use --compile-pdf flag to generate PDFs"
```

Make executable and run:
```bash
chmod +x setup_templates.sh
./setup_templates.sh
```

## Verification

Check that template files are present:

```bash
ls -la templates/

# Should show:
# resume-openfont.cls    # For Modern Deedy
# awesome-cv.cls         # For Awesome CV
# fontawesome.sty        # For Awesome CV
```

## How It Works

### During PDF Compilation

1. **Generate LaTeX file:**
   ```
   output/20260109/dcs_senior_systems_engineer.tex
   ```

2. **Copy template files:**
   ```
   templates/resume-openfont.cls → output/20260109/resume-openfont.cls
   ```

3. **Compile PDF:**
   ```bash
   cd output/20260109
   xelatex dcs_senior_systems_engineer.tex
   # Output: dcs_senior_systems_engineer.pdf
   ```

4. **Clean up:**
   - Remove `.aux`, `.log`, `.out` files
   - Keep `.cls` file for future re-compilation

### Template File Copying

The compiler automatically copies template files from `templates/` to the output directory during compilation:

```python
# From latex_compiler.py
def _copy_template_files(self, work_dir: Path):
    """Copy template .cls and .sty files to output directory."""
    # Finds all .cls and .sty files in templates/
    # Copies to output/YYYYMMDD/
```

## Docker Setup

### Update Dockerfile

Template files should be included in the Docker image:

```dockerfile
# Copy templates
COPY templates/ /app/templates/
```

### Update docker-compose.yml

Or mount as volume:

```yaml
volumes:
  - ./templates:/app/templates:ro
```

### Complete Docker Setup

```bash
# 1. Download templates
./setup_templates.sh

# 2. Rebuild Docker image
docker-compose build

# 3. Test compilation
./generate_resume.sh jobs/test_job.json --compile-pdf
```

## Troubleshooting

### "Template directory not found"

```bash
# Check templates directory exists
ls -la templates/

# Create if missing
mkdir -p templates

# Download templates
./setup_templates.sh
```

### "No template files found"

```bash
# Check files are present
ls templates/*.cls templates/*.sty

# Should show:
# templates/resume-openfont.cls
# templates/awesome-cv.cls
# templates/fontawesome.sty
```

### "File resume-openfont.cls not found" during compilation

```bash
# Verify template files are being copied
./generate_resume.sh jobs/test_job.json --compile-pdf

# Should see output:
#   Copied template: resume-openfont.cls

# Manual check
ls output/20260109/*.cls

# Should show .cls file in output directory
```

### Modern Deedy compilation fails

```bash
# Ensure using pdflatex (automatic for modern-deedy)
./generate_resume.sh jobs/test.json --template modern-deedy --compile-pdf

# Check LaTeX installation
docker-compose run --rm resume-generator which pdflatex
# Should output: /usr/bin/pdflatex
```

### Awesome CV compilation fails

```bash
# Ensure using xelatex (automatic for awesome-cv)
./generate_resume.sh jobs/test.json --template awesome-cv --compile-pdf

# Check xelatex installation
docker-compose run --rm resume-generator which xelatex
# Should output: /usr/bin/xelatex

# Verify fontawesome.sty is present
ls templates/fontawesome.sty
```

## Manual Compilation

If you want to compile PDFs manually:

```bash
# Navigate to output directory
cd output/20260109

# Ensure template files are present
ls *.cls

# Compile with appropriate engine
# For Modern Deedy:
pdflatex dcs_senior_systems_engineer.tex

# For Awesome CV:
xelatex dcs_senior_systems_engineer.tex

# Run twice for references
xelatex dcs_senior_systems_engineer.tex
```

## Template Customization

### Modify Templates

You can customize templates by editing the `.cls` files:

```bash
# Edit Modern Deedy colors
vim templates/resume-openfont.cls

# Edit Awesome CV fonts
vim templates/awesome-cv.cls
```

Changes apply to all future compilations.

### Add New Templates

To add a custom template:

1. **Create `.cls` file:**
   ```bash
   # Place in templates/
   templates/my-custom-template.cls
   ```

2. **Update template generator:**
   ```python
   # resume_pipeline/templates/my_custom.py
   class MyCustomTemplate(BaseTemplate):
       def get_template_string(self):
           return r"""..."""
   ```

3. **Register in config:**
   ```python
   # config.py
   if self.template not in ["modern-deedy", "awesome-cv", "my-custom"]:
       raise ValueError(...)
   ```

## Alternative: System-wide Installation

Instead of `templates/` directory, you can install templates system-wide:

```bash
# Find LaTeX home
kpsewhich -var-value TEXMFHOME
# Example: /home/user/texmf

# Copy templates
mkdir -p $(kpsewhich -var-value TEXMFHOME)/tex/latex/local
cp templates/*.cls $(kpsewhich -var-value TEXMFHOME)/tex/latex/local/
cp templates/*.sty $(kpsewhich -var-value TEXMFHOME)/tex/latex/local/

# Update LaTeX database
texhash

# Now .cls files available globally
```

**Not recommended for Docker:** The local `templates/` approach is simpler and more portable.

## Best Practices

1. ✅ **Keep templates in version control**
   ```bash
   git add templates/
   git commit -m "Add LaTeX templates"
   ```

2. ✅ **Document template versions**
   ```bash
   # templates/README.md
   - resume-openfont.cls: From modern-deedy commit abc123
   - awesome-cv.cls: From Awesome-CV v1.6.0
   ```

3. ✅ **Test both templates**
   ```bash
   ./generate_resume.sh jobs/test.json --template modern-deedy --compile-pdf
   ./generate_resume.sh jobs/test.json --template awesome-cv --compile-pdf
   ```

4. ✅ **Backup customizations**
   - If you customize templates, keep original versions
   - Document changes in comments

## FAQ

**Q: Do I need both templates?**
A: Only download templates you plan to use. If you only use Modern Deedy, you only need `resume-openfont.cls`.

**Q: Can I use different template versions?**
A: Yes, but ensure compatibility with the pipeline's template code.

**Q: Why copy files instead of using TEXINPUTS?**
A: Copying ensures portability and makes output directories self-contained for manual re-compilation.

**Q: Can I compile without Docker?**
A: Yes, if you have LaTeX installed locally:
```bash
python -m resume_pipeline jobs/job.json career_profile.json --compile-pdf
```

**Q: Do templates need updating?**
A: Template repositories are stable. Update only if you want new features or bug fixes.

## Summary

**Quick Start:**
```bash
# 1. Download templates
mkdir -p templates
curl -o templates/resume-openfont.cls https://raw.githubusercontent.com/Aarif123456/modern-deedy/master/resume-openfont.cls
curl -o templates/awesome-cv.cls https://raw.githubusercontent.com/posquit0/Awesome-CV/master/awesome-cv.cls
curl -o templates/fontawesome.sty https://raw.githubusercontent.com/posquit0/Awesome-CV/master/fontawesome.sty

# 2. Verify
ls templates/

# 3. Generate PDF
./generate_resume.sh jobs/job.json --compile-pdf

# Done! PDF will be in output/YYYYMMDD/
```

---

**Need Help?**
- Template issues: Check repository documentation
- Compilation errors: Review LaTeX log in output directory
- Pipeline issues: See main README.md

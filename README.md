# AI Resume Pipeline - Refactored & Simplified

**Major Improvements in This Version:**
- ✅ All configuration via `.env` file (no command-line arguments needed)
- ✅ Google Drive integration removed (MinIO and Nextcloud remain)
- ✅ LaTeX `.tex` files always generated (but compilation is optional)
- ✅ Streamlined Docker build (removed LaTeX packages and excessive fonts)
- ✅ Fixed template caching issues with proper volume mounts
- ✅ WeasyPrint as default PDF generator (faster, simpler)

## 🎯 Quick Start

### 1. Setup Configuration

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your settings
nano .env
```

**Minimal .env configuration:**
```bash
# Required
OPENAI_API_KEY=sk-your-key-here
JOB_JSON_PATH=jobs/my_job.json
CAREER_PROFILE_PATH=career_profile.json

# Optional (defaults shown)
MODEL=gpt-4o-mini
OUTPUT_BACKEND=weasyprint
USE_CACHE=true
ENABLE_NEXTCLOUD=true
NEXTCLOUD_ENDPOINT=https://your-nextcloud.com
NEXTCLOUD_USER=username
NEXTCLOUD_PASSWORD=password
```

### 2. Build and Run

```bash
# Build the Docker image
docker-compose build

# Run the pipeline (reads from .env)
docker-compose run --rm resume-generator
```

That's it! No command-line arguments needed.

## 📁 Project Structure

```
resume-pipeline/
├── .env                          # All configuration here!
├── .env.example                  # Template with all options
├── docker-compose.yml            # Simplified (no font mounts)
├── Dockerfile                    # Streamlined (no LaTeX packages)
├── requirements.txt              # Reduced dependencies
├── career_profile.json           # Your career data
├── jobs/                         # Job descriptions
│   └── company_position.json
├── output/                       # Generated outputs
│   ├── .cache/                   # Cached states (shared)
│   ├── 20260111/                 # Today's outputs
│   │   ├── company_position.tex  # LaTeX source (always generated)
│   │   ├── company_position.pdf  # PDF (if using WeasyPrint)
│   │   └── *.json                # Checkpoints
└── templates/                    # HTML/CSS/LaTeX templates
    ├── resume.html.j2            # Jinja2 template for WeasyPrint
    ├── resume.css                # Styling for PDF
    └── *.cls                     # LaTeX class files
```

## 🔧 Configuration Options

All settings are controlled via `.env` file. Here are the key options:

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `JOB_JSON_PATH` | jobs/example_job.json | Path to job description |
| `CAREER_PROFILE_PATH` | career_profile.json | Path to your career profile |
| `OUTPUT_DIR` | ./output | Base output directory |
| `MODEL` | gpt-4o-mini | Base AI model |
| `STRONG_MODEL` | gpt-4o-mini | Strong model for drafts |
| `USE_CACHE` | true | Enable/disable caching |

### Output Backend

| Variable | Options | Description |
|----------|---------|-------------|
| `OUTPUT_BACKEND` | weasyprint, latex | PDF generation method |
| `LATEX_TEMPLATE` | modern-deedy, awesome-cv | LaTeX template choice |
| `TEMPLATE_NAME` | resume.html.j2 | HTML template for WeasyPrint |
| `CSS_FILE` | resume.css | CSS file for WeasyPrint |

### Cloud Upload

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_NEXTCLOUD` | false | Enable Nextcloud upload |
| `NEXTCLOUD_ENDPOINT` | - | Nextcloud server URL |
| `NEXTCLOUD_USER` | - | Username |
| `NEXTCLOUD_PASSWORD` | - | Password |
| `ENABLE_MINIO` | false | Enable MinIO/S3 upload |
| `MINIO_ENDPOINT` | - | MinIO endpoint |
| `MINIO_ACCESS_KEY` | - | Access key |
| `MINIO_SECRET_KEY` | - | Secret key |
| `MINIO_BUCKET` | resumes | Bucket name |

See `.env.example` for complete list of options.

## 🎨 Output Backends Explained

### WeasyPrint (Recommended - Default)

**What it does:**
- Generates PDF directly from HTML/CSS
- Creates `.tex` file for archival/manual compilation
- Faster than LaTeX compilation
- No external LaTeX installation needed

**When to use:**
- You want quick PDF generation
- You're happy with HTML/CSS styling
- You want to upload PDFs to Nextcloud/MinIO immediately

**Output files:**
- `company_position.pdf` - Ready-to-use PDF
- `company_position.tex` - LaTeX source for archival

### LaTeX (Traditional)

**What it does:**
- Generates `.tex` file only (no PDF compilation in Docker)
- You upload `.tex` to Overleaf or compile manually
- Professional LaTeX typesetting

**When to use:**
- You prefer LaTeX's typesetting quality
- You want to manually tweak the `.tex` file
- You're comfortable with Overleaf or local LaTeX

**Output files:**
- `company_position.tex` - LaTeX source file

**To use LaTeX backend:**
```bash
# In .env file
OUTPUT_BACKEND=latex
LATEX_TEMPLATE=modern-deedy  # or awesome-cv
```

**Manual compilation:**
```bash
cd output/20260111/
xelatex company_position.tex  # for awesome-cv
# or
pdflatex company_position.tex  # for modern-deedy
```

## 🔄 Migration from Old Version

### Changes You Need to Make

1. **Remove command-line arguments** from your scripts
   ```bash
   # OLD WAY
   ./generate_resume.sh jobs/job.json --template awesome-cv --compile-pdf
   
   # NEW WAY
   # Set in .env instead:
   # JOB_JSON_PATH=jobs/job.json
   # LATEX_TEMPLATE=awesome-cv
   # OUTPUT_BACKEND=latex
   docker-compose run --rm resume-generator
   ```

2. **Update your `.env` file**
   ```bash
   cp .env.example .env
   # Fill in your settings
   ```

3. **Remove Google Drive configuration**
   - Delete `credentials.json`
   - Delete `token.json`
   - Remove `--upload-gdrive` from any scripts
   - Use Nextcloud or MinIO instead

4. **Update docker-compose.yml**
   - Remove font volume mounts
   - Remove credentials.json mount
   - Use the new simplified version

5. **Rebuild Docker image**
   ```bash
   docker-compose build --no-cache
   ```

### What Was Removed

- ❌ Google Drive upload functionality
- ❌ Command-line argument parsing (except `--from-json`)
- ❌ LaTeX compilation in Docker (manual only)
- ❌ Font file mounts in docker-compose.yml
- ❌ LaTeX packages in Dockerfile (texlive-xetex, etc.)

### What Was Added

- ✅ Comprehensive `.env` configuration
- ✅ Better error messages with configuration hints
- ✅ Config summary printed at startup
- ✅ Always generate `.tex` files (even with WeasyPrint)
- ✅ Proper volume mount for templates (fixes caching)

## 🐛 Troubleshooting

### Template Changes Not Reflecting in Output

**Problem:** You updated `templates/resume.html.j2` or `resume.css` but the PDF looks the same.

**Root Cause:** Docker was caching template files in the image instead of reading from the mounted volume.

**Solution (Already Fixed):**
The new `docker-compose.yml` mounts templates as a volume:
```yaml
volumes:
  - ./templates:/app/templates:ro  # Read from host, not image
```

**To apply the fix:**
```bash
# Rebuild without cache
docker-compose build --no-cache

# Or pull fresh
docker-compose down
docker-compose up --build
```

**Verify it's working:**
```bash
# Make a small change to templates/resume.html.j2
echo "<!-- Test change $(date) -->" >> templates/resume.html.j2

# Run pipeline
docker-compose run --rm resume-generator

# Check the generated PDF - change should be visible
# (or check intermediate HTML if debugging)
```

### Configuration Not Loading

**Problem:** Pipeline can't find job file or career profile.

**Solution:**
```bash
# Check paths in .env
cat .env | grep -E '(JOB_JSON_PATH|CAREER_PROFILE_PATH)'

# Verify files exist
ls -la jobs/
ls -la career_profile.json

# Make sure paths are relative to project root
# ✅ JOB_JSON_PATH=jobs/my_job.json
# ❌ JOB_JSON_PATH=/full/path/to/jobs/my_job.json
```

### Permission Errors

**Problem:** Can't write to output directory.

**Solution:**
```bash
# Set your user ID in .env
echo "USER_ID=$(id -u)" >> .env
echo "GROUP_ID=$(id -g)" >> .env

# Or in docker-compose
docker-compose run --rm -e USER_ID=$(id -u) -e GROUP_ID=$(id -g) resume-generator
```

### Cache Not Working

**Problem:** Pipeline regenerates everything even when job hasn't changed.

**Solution:**
```bash
# Verify caching is enabled in .env
grep USE_CACHE .env
# Should show: USE_CACHE=true

# Check cache directory exists
ls -la output/.cache/

# Clear corrupted cache
rm -rf output/.cache/*

# Run again
docker-compose run --rm resume-generator
```

### PDF Not Generated

**Problem:** Pipeline completes but no PDF file.

**Check:**
1. Which backend are you using?
   ```bash
   grep OUTPUT_BACKEND .env
   ```

2. If `latex`: PDFs are NOT generated automatically
   - You'll get a `.tex` file only
   - Upload to Overleaf or compile manually

3. If `weasyprint`: Check for errors
   ```bash
   # Look for WeasyPrint errors in output
   docker-compose run --rm resume-generator 2>&1 | grep -i weasy
   ```

### API Key Errors

**Problem:** OpenAI or Google API key not found.

**Solution:**
```bash
# Check .env file
cat .env | grep API_KEY

# Verify it's loaded
docker-compose run --rm resume-generator env | grep API_KEY

# Make sure no spaces around =
# ✅ OPENAI_API_KEY=sk-abc123
# ❌ OPENAI_API_KEY = sk-abc123
```

## 🚀 Advanced Usage

### Switching Between Jobs

Just update `.env`:
```bash
# Edit .env
JOB_JSON_PATH=jobs/different_company.json

# Run pipeline
docker-compose run --rm resume-generator
```

### Batch Processing

```bash
# Create a script
for job in jobs/*.json; do
  echo "Processing $job"
  sed -i "s|JOB_JSON_PATH=.*|JOB_JSON_PATH=$job|" .env
  docker-compose run --rm resume-generator
done
```

### Using Different Models

```bash
# In .env
MODEL=gpt-4o              # More capable but slower/expensive
STRONG_MODEL=gpt-4o       # Same model for all steps
```

### Compiling Existing JSON to PDF

If you have a saved `structured_resume.json`:
```bash
docker-compose run --rm resume-generator \
  python -m resume_pipeline --from-json output/20260110/structured_resume.json
```

### Disable Caching for Testing

```bash
# In .env
USE_CACHE=false

# Or temporarily
echo "USE_CACHE=false" > .env.local
docker-compose run --rm --env-file .env.local resume-generator
```

## 📦 Docker Build Optimization

### Size Comparison

**Old Dockerfile:**
- Base: python:3.11-slim
- + texlive-xetex (~300MB)
- + texlive-latex-extra (~200MB)
- + Custom fonts (~50MB)
- **Total: ~900MB**

**New Dockerfile:**
- Base: python:3.11-slim
- + WeasyPrint deps (~50MB)
- + Minimal fonts (~10MB)
- **Total: ~350MB** ✅

### Build Time

```bash
# Cold build (no cache)
time docker-compose build --no-cache
# Old: ~5 minutes
# New: ~2 minutes ✅

# Warm build (with cache)
time docker-compose build
# Old: ~30 seconds
# New: ~15 seconds ✅
```

### Rebuild Only When Needed

```bash
# Rebuild when:
# - requirements.txt changes
# - Python code changes
# - Dockerfile changes

docker-compose build

# Don't rebuild when:
# - Templates change (mounted as volume)
# - .env changes (also mounted)
# - Job files change (also mounted)
```

## 🎯 Best Practices

1. **Use WeasyPrint for iteration speed**
   - Switch to LaTeX only for final production version
   
2. **Keep cache enabled during development**
   - Clear cache when you update career profile significantly

3. **Use environment-specific .env files**
   ```bash
   .env.dev    # Development settings
   .env.prod   # Production settings
   
   # Use with:
   docker-compose --env-file .env.prod run --rm resume-generator
   ```

4. **Version control your .env.example**
   - But never commit `.env` (contains secrets)
   - Add to .gitignore

5. **Back up important outputs**
   ```bash
   # Archive a successful version
   tar -czf resume_archive_$(date +%Y%m%d).tar.gz \
     output/20260111/company_position.*
   ```

## 📝 File Output Reference

After running the pipeline, you'll find these files in `output/YYYYMMDD/`:

| File | Description | Always Created? |
|------|-------------|-----------------|
| `jd_requirements.json` | Job analysis | ✅ |
| `matched_achievements.json` | Ranked achievements | ✅ |
| `draft_resume.json` | Initial draft | ✅ |
| `critique.json` | Quality scores | ✅ |
| `final_resume.json` | Refined text | ✅ |
| `structured_resume.json` | Parsed structure | ✅ |
| `company_position.tex` | LaTeX source | ✅ |
| `company_position.pdf` | PDF output | Only with WeasyPrint |

## 🔍 Debugging

### Enable Verbose Output

```bash
# Add to .env
DEBUG=true

# Or run with Python debug
docker-compose run --rm resume-generator python -m pdb -m resume_pipeline
```

### Inspect Intermediate Files

```bash
# Check what the AI generated
cat output/20260111/draft_resume.json | jq

# See critique scores
cat output/20260111/critique.json | jq '.score'

# View matched achievements
cat output/20260111/matched_achievements.json | jq '.[].description'
```

### Check Template Rendering

```bash
# If using WeasyPrint, you can manually render HTML
docker-compose run --rm resume-generator python -c "
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import json

env = Environment(loader=FileSystemLoader('templates'))
template = env.get_template('resume.html.j2')

with open('output/20260111/structured_resume.json') as f:
    context = json.load(f)

html = template.render(**context)
Path('debug_output.html').write_text(html)
print('HTML written to debug_output.html')
"
```

## 📚 Additional Resources

- **WeasyPrint Docs**: https://doc.courtbouillon.org/weasyprint/
- **Jinja2 Templates**: https://jinja.palletsprojects.com/
- **LaTeX Overleaf**: https://www.overleaf.com/
- **Nextcloud API**: https://docs.nextcloud.com/server/latest/developer_manual/

## 🆘 Getting Help

If you encounter issues:

1. Check this troubleshooting section
2. Review your `.env` configuration
3. Check the console output for specific error messages
4. Inspect checkpoint files in `output/YYYYMMDD/*.json`
5. Try rebuilding Docker image: `docker-compose build --no-cache`

## 📄 License

MIT License - customize as needed.

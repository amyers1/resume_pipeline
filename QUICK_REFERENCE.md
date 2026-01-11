# Quick Reference Guide

## 🚀 Common Tasks

### Run Pipeline
```bash
docker-compose run --rm resume-generator
```

### Change Job
Edit `.env`:
```bash
JOB_JSON_PATH=jobs/different_job.json
```

### Switch to LaTeX Backend
Edit `.env`:
```bash
OUTPUT_BACKEND=latex
LATEX_TEMPLATE=awesome-cv
```

### Disable Caching
Edit `.env`:
```bash
USE_CACHE=false
```

### Clear Cache
```bash
rm -rf output/.cache/*
```

### Compile Existing JSON
```bash
docker-compose run --rm resume-generator \
  python -m resume_pipeline --from-json output/20260111/structured_resume.json
```

### Rebuild Docker Image
```bash
docker-compose build --no-cache
```

### View Output Files
```bash
ls -lh output/$(date +%Y%m%d)/
```

## 📝 .env Quick Reference

### Minimal Configuration
```bash
OPENAI_API_KEY=sk-xxx
JOB_JSON_PATH=jobs/my_job.json
CAREER_PROFILE_PATH=career_profile.json
```

### With Nextcloud Upload
```bash
ENABLE_NEXTCLOUD=true
NEXTCLOUD_ENDPOINT=https://cloud.example.com
NEXTCLOUD_USER=username
NEXTCLOUD_PASSWORD=password
```

### LaTeX Backend
```bash
OUTPUT_BACKEND=latex
LATEX_TEMPLATE=modern-deedy
```

### WeasyPrint Backend (Default)
```bash
OUTPUT_BACKEND=weasyprint
TEMPLATE_NAME=resume.html.j2
CSS_FILE=resume.css
```

## 🐛 Troubleshooting Quick Fixes

### Template Not Updating
```bash
# Rebuild without cache
docker-compose build --no-cache
```

### Permission Errors
Add to `.env`:
```bash
USER_ID=$(id -u)
GROUP_ID=$(id -g)
```

### API Key Not Found
Check `.env`:
```bash
cat .env | grep OPENAI_API_KEY
# Should have: OPENAI_API_KEY=sk-xxx
```

### Cache Issues
```bash
rm -rf output/.cache/*
```

### PDF Not Generated
Check backend:
```bash
grep OUTPUT_BACKEND .env
# If latex: No PDF (only .tex)
# If weasyprint: PDF generated
```

## 📂 File Locations

| File | Location |
|------|----------|
| Configuration | `.env` |
| Job descriptions | `jobs/*.json` |
| Career profile | `career_profile.json` |
| Templates | `templates/` |
| Output | `output/YYYYMMDD/` |
| Cache | `output/.cache/` |

## 🎯 Output Files

After running, find in `output/YYYYMMDD/`:
- `company_position.tex` - LaTeX source (always)
- `company_position.pdf` - PDF (if WeasyPrint)
- `structured_resume.json` - Structured data
- `critique.json` - Quality scores
- Other checkpoint files

## 🔄 Typical Workflow

1. Update `.env` with job path
2. Run: `docker-compose run --rm resume-generator`
3. Check: `ls output/$(date +%Y%m%d)/`
4. Review PDF or upload .tex to Overleaf

## 📊 Model Selection

| Model | Speed | Quality | Cost | Use Case |
|-------|-------|---------|------|----------|
| gpt-4o-mini | Fast | Good | Low | Default, iteration |
| gpt-4o | Slow | Best | High | Final production |
| gemini-1.5-flash | Fast | Good | Low | Alternative to mini |
| gemini-1.5-pro | Medium | Better | Medium | Alternative to gpt-4o |

Set in `.env`:
```bash
MODEL=gpt-4o-mini          # Base model
STRONG_MODEL=gpt-4o-mini   # Strong model
```

## 🎨 Template Customization

1. Edit template:
   ```bash
   vim templates/resume.html.j2
   # or
   vim templates/resume.css
   ```

2. Run immediately (no rebuild):
   ```bash
   docker-compose run --rm resume-generator
   ```

3. Changes reflected in output

## 📦 Backup Important Versions

```bash
# Archive today's output
tar -czf backup_$(date +%Y%m%d).tar.gz output/$(date +%Y%m%d)/

# Archive all outputs
tar -czf backup_all.tar.gz output/
```

## 🔍 Debugging

### Check Configuration
```bash
# View current config
cat .env

# Test config loading
docker-compose run --rm resume-generator python -c "
from resume_pipeline.config import PipelineConfig
config = PipelineConfig()
config.print_config_summary()
"
```

### View Intermediate Files
```bash
# See what AI generated
cat output/20260111/draft_resume.json | jq

# Check scores
cat output/20260111/critique.json | jq '.score'

# View matched achievements
cat output/20260111/matched_achievements.json | jq
```

### Manual Template Rendering
```bash
docker-compose run --rm resume-generator python << 'EOF'
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import json

env = Environment(loader=FileSystemLoader('templates'))
template = env.get_template('resume.html.j2')

with open('output/20260111/structured_resume.json') as f:
    context = json.load(f)

html = template.render(**context)
Path('debug.html').write_text(html)
print('Rendered to debug.html')
EOF
```

## 🌐 Cloud Upload Setup

### Nextcloud
```bash
# In .env
ENABLE_NEXTCLOUD=true
NEXTCLOUD_ENDPOINT=https://your-cloud.com
NEXTCLOUD_USER=username
NEXTCLOUD_PASSWORD=password
```

### MinIO
```bash
# In .env
ENABLE_MINIO=true
MINIO_ENDPOINT=play.min.io:9000
MINIO_ACCESS_KEY=your-key
MINIO_SECRET_KEY=your-secret
MINIO_BUCKET=resumes
```

## 📚 Documentation

- Full guide: `README.md`
- Technical details: `REFACTORING_SUMMARY.md`
- This guide: `QUICK_REFERENCE.md`
- Example config: `.env.example`

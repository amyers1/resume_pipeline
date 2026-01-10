# AI Resume Generation Pipeline

Automatically generate tailored, ATS-optimized resumes for specific job postings using AI with intelligent caching, date-based organization, and multi-template support.

## Features

- 🎯 **Job-Specific Tailoring**: Matches your experience to job requirements
- 📊 **Achievement Ranking**: AI selects your most relevant accomplishments
- ✍️ **Professional Writing**: Generates polished, ATS-safe resume content
- 🔄 **Iterative Refinement**: Critiques and improves output automatically
- 💾 **Smart Caching**: Reuses job analysis, matching, and drafts to save time and API costs
- 📅 **Experience Grouping**: Emphasizes recent 8-10 years, groups older experience
- 📄 **Multi-Template Support**: Choose between Modern Deedy or Awesome CV
- 📏 **Length Control**: Optimized for 2-page maximum
- 🗂️ **Date-Based Organization**: Outputs organized by date (YYYYMMDD) for easy version tracking
- 📝 **Clean Filenames**: Lowercase, abbreviated company names, no timestamps
- 🔒 **Truth & Accuracy**: Built-in safeguards prevent fabrication
- ⚡ **Efficient Model**: Uses gpt-4o-mini for fast, cost-effective generation

## Prerequisites

- Docker and Docker Compose installed
- OpenAI API key

## Project Structure

```
resume-pipeline/
├── docker-compose.yml
├── Dockerfile
├── docker-entrypoint.sh
├── requirements.txt
├── resume_pipeline.py
├── generate_resume.sh
├── career_profile.json          # Your career data
├── .env                          # API keys
├── jobs/                         # Job descriptions (JSON)
│   ├── company_position1.json
│   └── company_position2.json
└── output/                       # Generated resumes
    ├── .cache/                   # Cached pipeline states (shared)
    ├── 20260109/                 # Date-based directory (YYYYMMDD)
    │   ├── dcs_senior_systems_engineer.tex
    │   ├── jd_requirements.json
    │   ├── matched_achievements.json
    │   ├── draft_resume.json
    │   ├── critique.json
    │   ├── final_resume.json
    │   └── structured_resume.json
    └── 20260110/                 # Next day's outputs
        └── ...
```

## Setup

### 1. Create Required Files

**`.env`** - Add your OpenAI API key:
```bash
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4o-mini
```

**`career_profile.json`** - Your career data (see schema below)

**`jobs/`** - Create directory for job descriptions:
```bash
mkdir jobs
```

### 2. Build the Docker Image

```bash
docker-compose build
```

### 3. Make Helper Script Executable

```bash
chmod +x generate_resume.sh
```

## Usage

### Basic Usage

Generate a resume for a specific job:

```bash
# Modern Deedy template (default)
./generate_resume.sh jobs/your_job.json

# Awesome CV template
./generate_resume.sh jobs/your_job.json --template awesome-cv

# Disable caching (force fresh generation)
./generate_resume.sh jobs/your_job.json --no-cache
```

### Direct Docker Command

```bash
docker-compose run --rm resume-generator \
  python resume_pipeline.py jobs/your_job.json career_profile.json \
  --template modern-deedy
```

### Template Options

- `modern-deedy` (default): Clean, modern single-column design
- `awesome-cv`: Professional two-column LaTeX resume/CV template

### Output Organization

Each run creates outputs in a date-stamped directory (`YYYYMMDD`):
- Files within the same day overwrite previous versions
- Different days create separate directories for version history
- Easy comparison across dates

### Filename Convention

All output files use lowercase with smart company abbreviations:
- **Format**: `{company_abbrev}_{job_title_keywords}.{ext}`
- **Example**: `dcs_senior_systems_engineer.tex`
- **No timestamps** in filenames for cleaner file management

**Recognized company abbreviations:**
| Company | Abbreviation | Example Output |
|---------|--------------|----------------|
| Lockheed Martin | `lm` | `lm_principal_engineer.tex` |
| Northrop Grumman | `ng` | `ng_systems_engineer_senior.tex` |
| Raytheon Technologies | `rtx` | `rtx_software_engineer.tex` |
| General Dynamics | `gd` | `gd_systems_engineer.tex` |
| Boeing | `boeing` | `boeing_senior_engineer.tex` |
| BAE Systems | `bae` | `bae_principal_engineer.tex` |
| L3Harris | `l3harris` | `l3harris_rf_engineer.tex` |
| Leidos | `leidos` | `leidos_systems_engineer.tex` |
| CACI | `caci` | `caci_software_engineer.tex` |
| Booz Allen Hamilton | `bah` | `bah_senior_consultant.tex` |
| DCS Corporation | `dcs` | `dcs_senior_systems_engineer.tex` |

*Unknown companies use first letters of each word or the full first word.*

### Caching Behavior

The pipeline automatically caches:
- Job description analysis
- Achievement matching
- Initial draft generation

**Cache is reused when:**
- Same job file (unchanged content)
- Same career profile (unchanged content)

**Cache is bypassed when:**
- Job description changes
- Career profile updates
- `--no-cache` flag is used

**Benefits:**
- Saves 60-80% of API calls on re-runs
- Faster iteration on critique/refinement
- Lower costs when experimenting with templates

**Cache location:** `output/.cache/`

### Clear Cache

```bash
# Clear all cached states
rm -rf output/.cache/*

# Clear specific date's outputs
rm -rf output/20260109/

# Keep cache, clear old date directories
find output -maxdepth 1 -type d -name "202*" -mtime +30 -exec rm -rf {} \;
```

## Experience Grouping

Resumes automatically emphasize your most recent experience:

**Recent Experience (Last 8-10 years):**
- Full detailed entries
- 4-6 high-impact bullets per role
- Comprehensive scope and metrics

**Other Relevant Experience (2006-2016):**
- Grouped under single heading
- 2-3 key bullets per role
- Condensed format: Organization | Title | Location | Dates

This structure keeps resumes focused and within 2 pages while showcasing depth of experience.

## Quality Scoring

The pipeline uses **best-effort scoring** with length constraints:

- **Target Score:** 0.80+ (relaxed from 0.87)
- **Keyword Coverage:** 0.70+ (allows for concise writing)
- **Length Limit:** 2 pages maximum (strictly enforced)

**Philosophy:** Quality and impact over keyword density. A concise, powerful resume at 0.82 score beats a verbose 0.90 score at 3 pages.

## Input Schemas

### Job Description JSON (`jobs/*.json`)

```json
{
  "job_details": {
    "source": "Indeed",
    "platform": "indeed",
    "job_title": "Senior Systems Engineer",
    "company": "DCS Corporation",
    "location": "Tinker AFB, OK",
    "employment_type": "Full-time",
    "security_clearance_required": "Secret",
    "job_post_url": "https://...",
    "apply_url": "https://..."
  },
  "job_description": {
    "headline": "Senior Systems Engineer",
    "short_summary": "Brief role summary...",
    "full_text": "Complete job description...",
    "must_have_skills": [
      "Systems Engineering",
      "DoD Experience",
      "..."
    ],
    "nice_to_have_skills": [
      "Electronic Warfare",
      "..."
    ]
  },
  "benefits": {
    "listed_benefits": ["Health insurance", "..."]
  }
}
```

### Career Profile JSON (`career_profile.json`)

```json
{
  "full_name": "Your Name",
  "clearance": "TS/SCI with Polygraph",
  "email": "your.email@example.com",
  "phone": "(555) 123-4567",
  "linkedin": "linkedin.com/in/yourprofile",
  "location": "City, State",
  "core_domains": [
    "Systems Engineering",
    "Program Management",
    "..."
  ],
  "roles": [
    {
      "title": "Senior Engineer",
      "organization": "Company Name",
      "location": "City, State",
      "start_date": "2020-01",
      "end_date": "present",
      "seniority": "Senior",
      "achievements": [
        {
          "description": "Led 100-person team...",
          "impact_metric": "$50M program; 3x efficiency gain",
          "domain_tags": ["Program_Mgmt", "Leadership"]
        }
      ]
    }
  ],
  "education": [
    "M.S., Electrical Engineering – University (2020)",
    "B.S., Electrical Engineering – University (2015)"
  ],
  "certifications": [
    "PMP – Project Management Institute (2024)"
  ],
  "awards": [
    "Outstanding Engineer Award (2023)"
  ]
}
```

## Output

The pipeline generates files in date-based directories:

### Directory Structure
```
output/
├── .cache/                    # Shared cache across all dates
│   └── a1b2c3d4e5f6g7h8.json  # Cached pipeline states
└── 20260109/                  # Today's date (YYYYMMDD)
    ├── dcs_senior_systems_engineer.tex         # Main LaTeX output
    ├── jd_requirements.json                     # Parsed job requirements
    ├── matched_achievements.json                # Selected achievements
    ├── draft_resume.json                        # Initial draft
    ├── critique.json                            # Quality scores/feedback
    ├── final_resume.json                        # Refined markdown
    └── structured_resume.json                   # Structured data
```

### Filename Format

All filenames are lowercase with company abbreviation:
- **DCS Corporation** → `dcs_senior_systems_engineer.tex`
- **Lockheed Martin** → `lm_principal_engineer.tex`
- **Northrop Grumman** → `ng_systems_engineer_senior.tex`
- **General Dynamics** → `gd_software_engineer.tex`

### Checkpoint Files
All checkpoint files are named without timestamps for easy access:
- `jd_requirements.json` - Parsed job requirements
- `matched_achievements.json` - Selected achievements
- `draft_resume.json` - Initial draft
- `critique.json` - Quality scores and feedback
- `final_resume.json` - Refined markdown
- `structured_resume.json` - Structured data

## Pipeline Stages

1. **Job Analysis**: Parses and structures job requirements
2. **Achievement Matching**: Scores and ranks your experience (heuristic + AI)
3. **Draft Generation**: Creates initial ATS-optimized resume with experience grouping
4. **Critique & Refine**: Iteratively improves quality (target score ≥0.80, ≤2 pages)
5. **LaTeX Generation**: Produces professionally formatted output in selected template

**With Caching:** Stages 1-3 are reused if job and career profile unchanged.

## Configuration

### Model Configuration

Default model: **gpt-4o-mini** (fast and cost-effective)

Edit `.env` to change:
```bash
OPENAI_MODEL=gpt-4o-mini
```

Or override via command line:
```bash
./generate_resume.sh jobs/job.json --model gpt-4o
```

### User/Group Configuration

Edit `docker-compose.yml` to customize:

```yaml
environment:
  - USER_ID=${USER_ID:-1000}      # Match host user
  - GROUP_ID=${GROUP_ID:-1000}    # Match host group
```

Or set in your shell:
```bash
export USER_ID=$(id -u)
export GROUP_ID=$(id -g)
```

## Compiling LaTeX

### Modern Deedy

Requires the Modern Deedy class file:

```bash
cd output/20260109  # Use today's date
# Ensure resume-openfont.cls is in the same directory
pdflatex dcs_senior_systems_engineer.tex
```

### Awesome CV

Requires Awesome CV class files:

```bash
cd output/20260109  # Use today's date
# Ensure awesome-cv.cls and font files are in the same directory
xelatex lm_principal_engineer.tex
```

### Using Overleaf

Upload the `.tex` file and required template files to Overleaf for easy compilation.

## Troubleshooting

### Permission Issues
Ensure USER_ID and GROUP_ID are set:
```bash
export USER_ID=$(id -u)
export GROUP_ID=$(id -g)
docker-compose run --rm resume-generator ...
```

### API Key Not Found
Check `.env` file exists and contains:
```
OPENAI_API_KEY=sk-...
```

### Cache Not Working
Verify cache directory exists:
```bash
ls -la output/.cache/
```

Clear cache if corrupted:
```bash
rm -rf output/.cache/*
```

### Wrong Output Directory
Ensure you're checking the correct date:
```bash
# Check today's date
date +%Y%m%d

# List all output directories
ls -l output/

# Look in correct date directory
ls -l output/$(date +%Y%m%d)/
```

### Files Being Overwritten
Same-date runs overwrite files in that day's directory. To preserve:
```bash
# Copy before regenerating
cp -r output/20260109 output/20260109_backup

# Or manually rename specific files
mv output/20260109/dcs_position.tex \
   output/20260109/dcs_position_v1.tex
```

### Resume Too Long
The pipeline enforces 2-page limit. If still too long:
1. Review matched achievements - ensure only most relevant selected
2. Check "Other Relevant Experience" grouping is working
3. Reduce number of awards/certifications in career profile

### Low Critique Scores
- Add more specific achievements to `career_profile.json`
- Ensure achievements include domain_tags matching job requirements
- Review matched_achievements checkpoint to verify relevance
- Remember: 0.80+ score with 2-page limit is excellent

## Advanced Usage

### Custom Parameters

Modify `resume_pipeline.py` directly or pass arguments:

```bash
docker-compose run --rm resume-generator \
  python resume_pipeline.py jobs/job.json career_profile.json \
  --template awesome-cv \
  --model gpt-4o \
  --strong-model gpt-4o
```

### Batch Processing

```bash
for job in jobs/*.json; do
  echo "Processing $job..."
  ./generate_resume.sh "$job" --template modern-deedy
done
```

### Working with Multiple Versions

Since files are organized by date, you can easily manage and compare versions:

```bash
# Generate initial version on 2026-01-09
./generate_resume.sh jobs/dcs_position.json
# Creates: output/20260109/dcs_senior_systems_engineer.tex

# Same day: regenerate with updates (overwrites in same directory)
./generate_resume.sh jobs/dcs_position.json --no-cache
# Overwrites: output/20260109/dcs_senior_systems_engineer.tex

# Next day: generate fresh version (new directory)
./generate_resume.sh jobs/dcs_position.json
# Creates: output/20260110/dcs_senior_systems_engineer.tex

# Compare versions across dates
diff output/20260109/dcs_senior_systems_engineer.tex \
     output/20260110/dcs_senior_systems_engineer.tex

# View critique changes
diff output/20260109/critique.json \
     output/20260110/critique.json

# Archive old versions
tar -czf resumes_january.tar.gz output/202601*/
```

### Generate Both Templates for Same Job

```bash
# Modern Deedy version
./generate_resume.sh jobs/job.json --template modern-deedy

# Awesome CV version (overwrites in same directory)
./generate_resume.sh jobs/job.json --template awesome-cv

# Keep both: manually copy and rename
cp output/20260109/company_position.tex \
   output/20260109/company_position_modern_deedy.tex
```

## Best Practices

1. **Career Profile**: Keep detailed achievements with quantified impacts
2. **Domain Tags**: Tag achievements with relevant technical domains
3. **Job Files**: Organize by `company_position.json` naming convention
4. **Review Output**: Always review and customize the generated resume
5. **Truth First**: The AI won't fabricate; ensure your profile has relevant content
6. **Cache Management**: Clear cache when making major career profile updates
7. **Template Selection**: Try both templates and see which fits your style
8. **Length Awareness**: Trust the 2-page constraint - recruiters prefer concise resumes
9. **Version Control**: Use date directories to track resume evolution over time
10. **Backup Important Versions**: Copy critical versions before regenerating same-day
11. **Clean Old Outputs**: Periodically archive or delete old date directories
12. **Filename Readability**: Lowercase filenames are easier to work with in CLI

## Template Comparison

| Feature | Modern Deedy | Awesome CV |
|---------|--------------|------------|
| Style | Modern, clean | Professional, classic |
| Layout | Single column | Two column |
| Font | Sans-serif | Mix of serif/sans-serif |
| Density | Medium | High |
| Best For | Tech roles, startups | Traditional, enterprise |
| Compile | pdflatex | xelatex |
| Output Example | `dcs_senior_systems_engineer.tex` | `lm_principal_engineer.tex` |

## File Naming Examples

**Before (Old System):**
```
DCS_Corporation_Systems_Engineer_Senior_Secret_20260109_143022.tex
Lockheed_Martin_Principal_RF_Engineer_20260109_150321.tex
```

**After (New System):**
```
output/20260109/dcs_senior_systems_engineer.tex
output/20260109/lm_principal_rf_engineer.tex
output/20260110/dcs_senior_systems_engineer.tex  # Next day's version
```

**Benefits:**
- ✅ Shorter, cleaner filenames
- ✅ Consistent lowercase formatting
- ✅ Date-based version tracking via directories
- ✅ Same filename across versions (easier to script)
- ✅ Smart company abbreviations (industry standard)

## Workflow Examples

### Initial Application
```bash
# Generate resume for new opportunity
./generate_resume.sh jobs/dcs_senior_se.json

# Review output
cd output/20260109
cat critique.json | jq '.score'
pdflatex dcs_senior_systems_engineer.tex
```

### Iterative Refinement
```bash
# Update career profile with new achievement
vim career_profile.json

# Regenerate with fresh data (no cache)
./generate_resume.sh jobs/dcs_senior_se.json --no-cache

# Compare changes
diff output/20260109/draft_resume.json \
     output/20260109/final_resume.json
```

### Multi-Company Campaign
```bash
# Generate for multiple positions
for job in jobs/*.json; do
  ./generate_resume.sh "$job"
done

# Results organized by date
ls output/20260109/
# dcs_senior_systems_engineer.tex
# lm_principal_engineer.tex
# ng_systems_engineer_senior.tex
```

## License

MIT License - feel free to customize for your needs.

## Support

For issues or questions, review the checkpoint files in `output/{date}/` to debug pipeline stages.

Cache location: `output/.cache/` - inspect to verify caching behavior.

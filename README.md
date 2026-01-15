# AI Resume Pipeline

An intelligent, containerized resume generation system that leverages LLMs (OpenAI GPT or Google Gemini) to create tailored resumes. The pipeline analyzes job descriptions, matches them against your career profile, generates customized content, and produces professional PDFs using WeasyPrint or LaTeX.

## ✨ Features

- **Intelligent Job Analysis**: Extracts requirements, skills, and keywords from job descriptions
- **Smart Achievement Matching**: Automatically selects and tailors your most relevant experience
- **Multi-Stage Generation**: Draft → Critique → Refine workflow for high-quality output
- **Flexible Backends**: WeasyPrint (fast CSS-based) or LaTeX (professional typesetting)
- **Job Queue System**: Optional RabbitMQ integration for asynchronous batch processing
- **Cloud Integration**: Optional uploads to Nextcloud and MinIO/S3
- **CLI Tools**: Command-line scripts for job submission and monitoring
- **Intelligent Caching**: LLM response caching to reduce API costs
- **Professional Templates**: Modern and classic resume styles

---

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API key or Google Gemini API key

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd resume-pipeline

# Copy the example configuration
cp .env.example .env

# Edit configuration with your API keys
nano .env
```

### 2. Configure Environment

Edit `.env` with your settings:

```ini
# Required: API Keys
OPENAI_API_KEY=sk-your-key-here
# OR
GOOGLE_API_KEY=your-gemini-key

# Required: File Paths
CAREER_PROFILE_PATH=career_profile.json
JOB_JSON_PATH=jobs/example_job.json

# Model Selection
MODEL=gpt-4o-mini          # Base model for most tasks
STRONG_MODEL=gpt-4o-mini   # For complex critique/refinement

# Output Configuration
OUTPUT_BACKEND=weasyprint   # Options: weasyprint, latex
LATEX_TEMPLATE=modern-deedy # Options: modern-deedy, awesome-cv

# Features
USE_CACHE=true
ENABLE_RABBITMQ=false
ENABLE_NEXTCLOUD=false
ENABLE_MINIO=false
```

### 3. Prepare Your Data

**Career Profile (`career_profile.json`):**

This is your master career data source containing:
- Contact information
- Work experience with detailed achievements
- Education and certifications
- Skills and domain expertise

See the included `career_profile.json` for the expected structure.

**Job Description (`jobs/*.json`):**

Create a JSON file for each target position containing the job posting details. Example:

```json
{
  "job_details": {
    "company": "Acme Corp",
    "job_title": "Senior Software Engineer",
    "location": "Remote",
    "security_clearance_required": "Secret"
  },
  "job_description": {
    "headline": "Build next-gen cloud infrastructure",
    "must_have_skills": ["Python", "AWS", "Docker"],
    "nice_to_have_skills": ["Kubernetes", "Terraform"],
    "full_text": "Complete job posting text here..."
  }
}
```

### 4. Build and Run

```bash
# Build the Docker image
docker-compose build

# Generate a resume
docker-compose run --rm resume-generator

# The output will be in: output/YYYYMMDD/
```

---

## 🐳 Docker Deployment

### Architecture

The project uses Docker for consistent, reproducible builds with all dependencies:

- **Base Image**: Python 3.14-slim
- **System Dependencies**: Pango, HarfBuzz (for WeasyPrint), fonts
- **User Permissions**: Automatically matches your host user ID to avoid permission issues
- **Volume Mounts**: Templates and outputs are mounted for easy access

### Docker Compose Configuration

```yaml
services:
  resume-generator:
    build: .
    container_name: resume-pipeline
    environment:
      - USER_ID=${USER_ID:-1000}
      - GROUP_ID=${GROUP_ID:-1000}
    volumes:
      - ./career_profile.json:/app/career_profile.json:ro
      - ./.env:/app/.env:ro
      - ./output:/app/output:rw
      - ./jobs:/app/jobs:ro
      - ./templates:/app/templates:ro
```

### Building the Image

```bash
# Standard build
docker-compose build

# Force rebuild without cache
docker-compose build --no-cache

# Build with specific platform (for M1/M2 Macs)
docker-compose build --platform linux/amd64
```

### Running Containers

```bash
# Single-shot resume generation
docker-compose run --rm resume-generator

# Run with custom job file
docker-compose run --rm resume-generator python submit_job.py jobs/my_job.json

# Run the worker for queue processing
docker-compose run --rm resume-generator python resume_worker.py

# Monitor job queue status
docker-compose run --rm resume-generator python monitor_jobs.py --continuous
```

### Managing Permissions

The container automatically creates a user matching your host UID/GID:

```bash
# Set custom user/group IDs
export USER_ID=$(id -u)
export GROUP_ID=$(id -g)
docker-compose run --rm resume-generator
```

### Volume Management

Key mounted directories:

| Host Path | Container Path | Purpose | Mode |
|-----------|---------------|---------|------|
| `./career_profile.json` | `/app/career_profile.json` | Your career data | Read-only |
| `./.env` | `/app/.env` | Configuration | Read-only |
| `./jobs/` | `/app/jobs` | Job descriptions | Read-only |
| `./templates/` | `/app/templates` | Resume templates | Read-only |
| `./output/` | `/app/output` | Generated files | Read-write |

---

## 📋 How to Use

### Basic Workflow

1. **Create Job File**: Save target job description to `jobs/position_name.json`
2. **Update Config**: Set `JOB_JSON_PATH` in `.env` to point to your job file
3. **Run Pipeline**: Execute `docker-compose run --rm resume-generator`
4. **Review Output**: Check `output/YYYYMMDD/` for generated resume and artifacts

### Advanced Usage with CLI Tools

#### 1. Submit Jobs (`submit_job.py`)

Submit specific jobs without editing `.env`:

```bash
# Basic submission
docker-compose run --rm resume-generator python submit_job.py jobs/senior_dev.json

# Custom template and high priority
docker-compose run --rm resume-generator \
  python submit_job.py jobs/manager.json \
  --template awesome-cv \
  --priority 10 \
  --backend latex

# Submit without cloud uploads
docker-compose run --rm resume-generator \
  python submit_job.py jobs/position.json \
  --no-upload
```

**Arguments:**
- `job_json`: Path to job description file (required)
- `--profile`: Path to career profile (default: `career_profile.json`)
- `--template`: Template choice: `modern-deedy` or `awesome-cv`
- `--backend`: Output backend: `weasyprint` or `latex`
- `--priority`: Queue priority 0-10 (higher = sooner, default: 0)
- `--no-upload`: Skip cloud storage uploads

#### 2. Monitor Queue (`monitor_jobs.py`)

Watch job processing in real-time:

```bash
# Single status check
docker-compose run --rm resume-generator python monitor_jobs.py

# Continuous monitoring (updates every 5 seconds)
docker-compose run --rm resume-generator \
  python monitor_jobs.py --continuous

# Continuous with custom interval
docker-compose run --rm resume-generator \
  python monitor_jobs.py --continuous --interval 10
```

**Sample Output:**
```
📊 Resume Pipeline Status Monitor
════════════════════════════════════════════════════════════════════

Job ID: abc123
Status: ⏳ GENERATING_DRAFT
Progress: 45%
Message: Writing professional summary...
Started: 2025-01-15 10:30:00
Updated: 2025-01-15 10:32:15
Duration: 2m 15s

Job ID: def456
Status: ✅ COMPLETED
Progress: 100%
Message: Resume generated successfully
Output: output/20250115/acme_corp_senior_engineer.pdf
Started: 2025-01-15 10:25:00
Completed: 2025-01-15 10:28:30
Duration: 3m 30s
```

#### 3. Run as Worker (`resume_worker.py`)

Process jobs from RabbitMQ queue:

```bash
# Start worker (requires ENABLE_RABBITMQ=true in .env)
docker-compose run --rm resume-generator python resume_worker.py

# Worker will:
# - Connect to RabbitMQ
# - Listen for job requests
# - Process jobs sequentially
# - Publish progress updates
# - Handle errors gracefully
```

### Pipeline Stages

The resume generation follows these stages with progress tracking:

1. **Analyzing JD** (15%): Extracts requirements and keywords
2. **Matching Achievements** (20%): Selects relevant experience
3. **Generating Draft** (25%): Creates initial resume content
4. **Critiquing** (15%): AI review and scoring
5. **Refining** (10%): Iterative improvements
6. **Generating Output** (10%): Creates PDF/LaTeX files
7. **Post-Processing** (5%): Cloud uploads and cleanup

### Understanding Output

Generated files in `output/YYYYMMDD/`:

```
output/20250115/
├── company_position.pdf              # Final PDF resume
├── company_position.tex              # LaTeX source (if backend=latex)
├── structured_resume.json            # Parsed resume data
├── jd_requirements.json              # Job analysis checkpoint
├── matched_achievements.json         # Selected experience checkpoint
├── draft_resume.txt                  # Initial draft checkpoint
├── final_resume.txt                  # Refined content checkpoint
└── critique.json                     # AI evaluation and scoring
```

### Customizing Templates

Templates are in the `templates/` directory:

**For WeasyPrint (HTML/CSS):**
- Edit `templates/resume.html.j2` (structure)
- Edit `templates/resume.css` (styling)
- Changes apply immediately (no rebuild needed)

**For LaTeX:**
- Edit `templates/resume-openfont.cls` or `templates/awesome-cv.cls`
- Changes apply immediately (no rebuild needed)

### Working with Cache

The pipeline caches LLM responses to save time and money:

```bash
# Enable caching (in .env)
USE_CACHE=true

# Cache location
output/.cache/

# Clear cache
rm -rf output/.cache/*

# Disable caching for fresh generation
USE_CACHE=false
```

Cache is keyed by job description + career profile hash. Changes to either will invalidate cache.

---

## 🔧 Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes* | - | OpenAI API key for GPT models |
| `GOOGLE_API_KEY` | Yes* | - | Google API key for Gemini models |
| `MODEL` | No | `gpt-4o-mini` | Base LLM model |
| `STRONG_MODEL` | No | `gpt-4o-mini` | Model for complex tasks |
| `JOB_JSON_PATH` | Yes | - | Path to job description JSON |
| `CAREER_PROFILE_PATH` | Yes | `career_profile.json` | Path to career profile |
| `OUTPUT_DIR` | No | `./output` | Output directory |
| `OUTPUT_BACKEND` | No | `weasyprint` | PDF backend: `weasyprint` or `latex` |
| `LATEX_TEMPLATE` | No | `modern-deedy` | LaTeX template: `modern-deedy` or `awesome-cv` |
| `USE_CACHE` | No | `true` | Enable LLM response caching |
| `TIMEZONE` | No | `America/New_York` | Timezone for timestamps |
| `ENABLE_RABBITMQ` | No | `false` | Enable job queue system |
| `ENABLE_NEXTCLOUD` | No | `false` | Enable Nextcloud uploads |
| `ENABLE_MINIO` | No | `false` | Enable MinIO/S3 uploads |

*One API key required depending on model choice

### RabbitMQ Configuration (Optional)

```ini
ENABLE_RABBITMQ=true
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USERNAME=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_VHOST=/
RABBITMQ_JOB_QUEUE=resume.jobs
RABBITMQ_STATUS_QUEUE=resume.status
```

### Cloud Storage Configuration (Optional)

**Nextcloud:**
```ini
ENABLE_NEXTCLOUD=true
NEXTCLOUD_URL=https://cloud.example.com
NEXTCLOUD_USERNAME=user
NEXTCLOUD_PASSWORD=password
NEXTCLOUD_FOLDER=/Resumes
```

**MinIO/S3:**
```ini
ENABLE_MINIO=true
MINIO_ENDPOINT=s3.amazonaws.com
MINIO_ACCESS_KEY=your-access-key
MINIO_SECRET_KEY=your-secret-key
MINIO_BUCKET=resumes
MINIO_SECURE=true
```

### Output Backends

| Backend | Speed | Quality | Use Case |
|---------|-------|---------|----------|
| **WeasyPrint** | Fast | Good | Quick iterations, modern styling |
| **LaTeX** | Slower | Excellent | Final versions, academic positions |

---

## 📁 Project Structure

```
resume-pipeline/
├── .env                          # Configuration (create from .env.example)
├── .env.example                  # Example configuration template
├── docker-compose.yml            # Docker orchestration
├── Dockerfile                    # Container definition
├── docker-entrypoint.sh          # Container initialization script
├── requirements.txt              # Python dependencies
│
├── career_profile.json           # Your career data (master source)
│
├── jobs/                         # Job description files
│   ├── example_job.json
│   └── your_positions/
│
├── templates/                    # Resume templates
│   ├── resume.html.j2           # HTML template (WeasyPrint)
│   ├── resume.css               # Styles (WeasyPrint)
│   ├── resume-openfont.cls      # Modern Deedy LaTeX class
│   └── awesome-cv.cls           # Awesome CV LaTeX class
│
├── output/                       # Generated resumes
│   ├── .cache/                  # LLM response cache
│   └── YYYYMMDD/                # Dated output folders
│
├── resume_pipeline/              # Core Python package
│   ├── __init__.py
│   ├── __main__.py              # CLI entry point
│   ├── config.py                # Configuration management
│   ├── pipeline.py              # Main orchestrator
│   ├── models.py                # Data models
│   ├── cache.py                 # Caching system
│   ├── rabbitmq.py              # Queue integration
│   ├── analyzers/               # Job analysis
│   ├── matchers/                # Achievement matching
│   ├── generators/              # Content generation
│   ├── critics/                 # Review and refinement
│   ├── parsers/                 # Output parsing
│   └── renderers/               # PDF generation
│
├── submit_job.py                 # CLI: Submit job to queue
├── monitor_jobs.py               # CLI: Monitor job status
├── resume_worker.py              # Worker: Process queued jobs
└── example_downstream.py         # Example: Workflow chaining
```

---

## 🐛 Troubleshooting

### Common Issues

**1. "Connection failed" to RabbitMQ**

If you get connection errors when using CLI tools:

```bash
# Solution 1: Disable RabbitMQ for standalone use
echo "ENABLE_RABBITMQ=false" >> .env
docker-compose run --rm resume-generator

# Solution 2: Start RabbitMQ service
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```

**2. API Key Errors**

```bash
# Check your .env file has the correct key
cat .env | grep API_KEY

# Verify the key is loaded
docker-compose run --rm resume-generator env | grep API_KEY
```

**3. Template Changes Not Showing**

Templates are mounted as volumes, so changes should appear immediately:

```bash
# Verify volume mount
docker-compose config | grep -A 5 volumes

# If needed, force reload
docker-compose down
docker-compose run --rm resume-generator
```

**4. Permission Errors in Output Directory**

```bash
# Ensure USER_ID and GROUP_ID match your host
export USER_ID=$(id -u)
export GROUP_ID=$(id -g)

# Fix existing file permissions
sudo chown -R $(id -u):$(id -g) output/

# Run container
docker-compose run --rm resume-generator
```

**5. PDF Generation Fails**

```bash
# Check WeasyPrint dependencies
docker-compose run --rm resume-generator python -c "import weasyprint; print('OK')"

# Try LaTeX backend instead
echo "OUTPUT_BACKEND=latex" >> .env
```

**6. Cache Taking Too Much Space**

```bash
# Check cache size
du -sh output/.cache

# Clear cache
rm -rf output/.cache/*

# Or disable caching
echo "USE_CACHE=false" >> .env
```

### Debugging Tips

**Enable Verbose Logging:**

```bash
# Run with Python logging
docker-compose run --rm resume-generator python -m resume_pipeline -v
```

**Inspect Container:**

```bash
# Open shell in container
docker-compose run --rm resume-generator /bin/bash

# Check installed packages
pip list

# Check file locations
ls -la /app/
```

**Test Individual Components:**

```bash
# Test job analyzer only
docker-compose run --rm resume-generator \
  python -c "from resume_pipeline.analyzers import JobAnalyzer; print('OK')"

# Test template rendering
docker-compose run --rm resume-generator \
  python -c "from jinja2 import Template; print('OK')"
```

---

## 🔄 Workflow Integration

### Chaining with Other Services

The pipeline can integrate with downstream services via RabbitMQ:

```python
# example_downstream.py
# Listen for completed resumes and trigger next workflow step
def process_completed_resume(job_result):
    pdf_path = job_result['output_files']['pdf']
    # Archive, email, or upload to applicant tracking system
```

### Batch Processing

Process multiple positions efficiently:

```bash
# Submit all jobs in directory
for job in jobs/*.json; do
  docker-compose run --rm resume-generator \
    python submit_job.py "$job" --priority 5
done

# Start worker to process queue
docker-compose run --rm resume-generator python resume_worker.py
```

### CI/CD Integration

```yaml
# .github/workflows/generate-resume.yml
name: Generate Resume
on:
  push:
    paths:
      - 'career_profile.json'
      - 'jobs/**'

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Generate Resume
        run: |
          docker-compose build
          docker-compose run --rm resume-generator
      - name: Upload Artifact
        uses: actions/upload-artifact@v3
        with:
          name: resume
          path: output/
```

---

## 🎯 Best Practices

### Career Profile Maintenance

- **Update regularly**: Add achievements as they happen
- **Use metrics**: Include numbers, percentages, dollar amounts
- **Tag domains**: Helps with relevant matching
- **Keep detailed**: More data = better tailoring

### Job Description Quality

- **Complete information**: Include full job posting text
- **Required vs. Nice-to-have**: Separate must-have from preferred skills
- **Company context**: Add company culture and values

### Template Selection

- **Modern Deedy**: Tech/startup positions, creative roles
- **Awesome CV**: Academic, research, traditional corporate
- **Custom**: Edit templates for your industry

### Cost Optimization

- **Enable caching**: Reuse responses for similar jobs
- **Choose base model**: Use `gpt-4o-mini` for cost-effectiveness
- **Batch processing**: Group similar positions

### Quality Assurance

- **Review checkpoints**: Check intermediate outputs
- **Validate achievements**: Ensure claims are accurate
- **Test templates**: Preview before final generation
- **Proofread**: AI-generated content needs human review

---

## 📚 Additional Resources

### Documentation

- **OpenAI API**: https://platform.openai.com/docs
- **Google Gemini**: https://ai.google.dev/docs
- **WeasyPrint**: https://doc.courtbouillon.org/weasyprint/
- **RabbitMQ**: https://www.rabbitmq.com/documentation.html

### Template Resources

- **LaTeX Resume Templates**: https://www.overleaf.com/gallery/tagged/cv
- **CSS Typography**: https://fonts.google.com
- **Design Inspiration**: https://www.canva.com/resumes/templates/

---

## 📝 License

MIT License - see LICENSE file for details

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

---

## 💬 Support

For issues and questions:

- **GitHub Issues**: Report bugs and request features
- **Discussions**: Ask questions and share tips
- **Documentation**: Check this README and inline code comments

---

## 🎓 Credits

Built with:
- Python & LangChain
- OpenAI GPT & Google Gemini
- WeasyPrint & LaTeX
- Docker & RabbitMQ
- Jinja2 templating

---

**Happy job hunting! 🚀**

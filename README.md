Here is the updated `README.md` file content, incorporating the new RabbitMQ worker scripts and CLI tools into the documentation.

```markdown
# AI Resume Pipeline

A robust, containerized pipeline that generates tailored resumes using LLMs (OpenAI or Google Gemini). This system analyzes job descriptions, matches them against your career profile, generates tailored content, and renders professional PDFs using WeasyPrint or LaTeX.

**New in this version:**
* **Job Queue System:** Optional RabbitMQ integration for asynchronous processing.
* **CLI Tools:** New `submit_job.py` and `monitor_jobs.py` scripts for managing resume generation.
* **WeasyPrint Default:** High-speed PDF generation with CSS styling (LaTeX source still generated for archival).
* **Streamlined Docker:** Optimized build size (~350MB) and improved caching.

---

## 🚀 Quick Start (Docker)

The easiest way to run the pipeline is via Docker Compose. This handles all dependencies, including WeasyPrint fonts and Python libraries.

### 1. Setup Configuration

```bash
# 1. Copy the example configuration
cp .env.example .env

# 2. Edit the .env file with your API keys and paths
nano .env

```

**Minimal `.env` configuration:**

```ini
# API Keys (Required)
OPENAI_API_KEY=sk-your-key-here
# or
GOOGLE_API_KEY=your-gemini-key

# Input Paths (Relative to project root)
CAREER_PROFILE_PATH=career_profile.json
JOB_JSON_PATH=jobs/my_job.json

# Settings
MODEL=gpt-4o-mini
OUTPUT_BACKEND=weasyprint  # or 'latex'
USE_CACHE=true

```

### 2. Prepare Data

1. **Career Profile:** Ensure `career_profile.json` is populated with your master work history.
2. **Job Description:** Save the text of the job you are applying for into a JSON file (e.g., `jobs/software_engineer.json`).

### 3. Build & Run

```bash
# Build the container
docker-compose build

# Run the pipeline (Single Shot Mode)
docker-compose run --rm resume-generator

```

*The output PDF and artifacts will appear in the `output/YYYYMMDD/` directory.*

---

## 🛠️ Advanced Usage & CLI Tools

This version includes scripts to manage job submission and monitoring, useful for batch processing or integrating with a queue system (RabbitMQ).

### Using the CLI Scripts inside Docker

You can execute the Python scripts directly inside the container using `docker-compose run`.

#### 1. Submit a Job (`submit_job.py`)

Submit a specific job file with custom options without editing `.env` every time.

```bash
# Basic submission
docker-compose run --rm resume-generator python submit_job.py jobs/senior_dev.json

# Submit with custom template and high priority
docker-compose run --rm resume-generator python submit_job.py jobs/manager.json \
  --template awesome-cv \
  --priority 10 \
  --backend latex

```

**Arguments:**

* `job_json`: Path to job description file.
* `--profile`: Path to career profile (default: `career_profile.json`).
* `--template`: `modern-deedy` or `awesome-cv`.
* `--backend`: `weasyprint` or `latex`.
* `--priority`: 0-10 (Higher = processed sooner).
* `--no-upload`: Skip cloud uploads.

#### 2. Monitor Progress (`monitor_jobs.py`)

Watch the status of the resume generation queue in real-time.

```bash
# continuous monitoring
docker-compose run --rm resume-generator python monitor_jobs.py --continuous

```

#### 3. Run the Worker (`resume_worker.py`)

Run the pipeline as a persistent worker that listens for jobs from RabbitMQ.

```bash
docker-compose run --rm resume-generator python resume_worker.py

```

*Note: The CLI tools and Worker require a running RabbitMQ instance if `ENABLE_RABBITMQ=true` is set in your `.env`.*

---

## 📁 Project Structure

```text
resume-pipeline/
├── .env                     # Configuration secrets
├── career_profile.json      # Master data source (Your history)
├── jobs/                    # Directory for target job descriptions
│   └── example_job.json
├── templates/               # Visual templates
│   ├── resume.html.j2       # HTML template (WeasyPrint)
│   ├── resume.css           # Styles (WeasyPrint)
│   └── *.cls                # LaTeX class files
├── output/                  # Generated results
│   └── YYYYMMDD/            # Dated folder per run
├── resume_pipeline/         # Core Python package
├── resume_worker.py         # RabbitMQ Worker entrypoint
├── submit_job.py            # CLI Job Submitter
├── monitor_jobs.py          # CLI Status Monitor
├── Dockerfile               # Python environment definition
├── docker-compose.yml       # Container orchestration
└── requirements.txt         # Python dependencies

```

## ⚙️ Configuration Reference

### Output Backends

| Backend | Description | Pros | Cons |
| --- | --- | --- | --- |
| **WeasyPrint** | (Default) HTML-to-PDF | Fast, easy to style with CSS, no LaTeX install needed. | Typesetting is slightly less "academic" than LaTeX. |
| **LaTeX** | Uses `.cls` templates | Industry standard typesetting, high precision. | Slower generation, harder to customize styling. |

### Key Environment Variables

| Variable | Description |
| --- | --- |
| `JOB_JSON_PATH` | Default job file to process in direct mode. |
| `CAREER_PROFILE_PATH` | Path to your master profile JSON. |
| `USE_CACHE` | `true`/`false`. Caches LLM responses to save costs. |
| `ENABLE_RABBITMQ` | `true`/`false`. Enables queue integration. |
| `ENABLE_NEXTCLOUD` | `true`/`false`. Uploads final PDF to Nextcloud. |
| `ENABLE_MINIO` | `true`/`false`. Uploads final PDF to S3/MinIO. |

## 🐛 Troubleshooting

**1. "Connection failed" to RabbitMQ**
If you run `submit_job.py` without a RabbitMQ broker available, it will fail.

* *Solution:* For standalone usage, use the standard command: `docker-compose run --rm resume-generator`.

**2. Template changes not showing**
Templates are mounted as volumes in `docker-compose.yml`.

* *Solution:* You do not need to rebuild the container to change CSS or HTML. Just save the file and run the generator again.

**3. Permissions issues in `output/**`

* *Solution:* The `docker-compose.yml` uses `USER_ID` and `GROUP_ID`. Ensure these match your host user:
```bash
# Add to .env or export in shell
export USER_ID=$(id -u)
export GROUP_ID=$(id -g)

```



## 📄 License

MIT License - customize as needed.

```

```

# AI Resume Pipeline

A full-stack, containerized application that leverages LLMs (OpenAI GPT or Google Gemini) to generate tailored, professional resumes. The system features a modern React frontend, a robust FastAPI backend, and persistent storage with PostgreSQL, allowing you to manage career profiles, track job applications, and generate optimized PDFs using WeasyPrint or LaTeX.

## ✨ Features

- **Full-Stack Web Interface**: Modern React/Vite dashboard for managing profiles and jobs.
- **Persistent Storage**: PostgreSQL database stores your career history, job descriptions, and past resumes.
- **Real-Time Progress**: Live updates during resume generation (Drafting → Critiquing → Refining → Compiling) via Server-Sent Events (SSE).
- **Intelligent Analysis**: Extracts requirements from job descriptions and matches them against your career profile.
- **Multi-Stage AI Pipeline**:
  - **Draft**: Creates initial content based on relevant experience.
  - **Critique**: AI reviewer scores the resume and suggests improvements.
  - **Refine**: Automatically applies improvements to increase ATS scores.
- **Flexible Output**: Generates professional PDFs via WeasyPrint (HTML/CSS) or LaTeX (for academic/technical styles).
- **Cloud Integration**: Optional automated uploads to S3-compatible storage or Nextcloud.
- **Dockerized**: Fully containerized architecture for easy deployment.

---

## 🏗 Architecture

The project is composed of several microservices orchestrated via Docker Compose:

- **Frontend**: React + Vite + Tailwind CSS (served on port `3000`)
- **API**: FastAPI (served on port `8000`)
- **Worker**: Background process for handling AI generation tasks
- **Database**: PostgreSQL for persistent data storage
- **Cache/Queue**: Redis for caching and message brokerage

---

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API Key **OR** Google Gemini API Key

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd resume-pipeline

# Create the environment file
cp .env.example .env

```

### 2. Configure Environment

Edit `.env` to add your API keys and configuration. Ensure you have the database credentials set (defaults provided in docker-compose are sufficient for local dev).

```ini
# --- AI Providers ---
OPENAI_API_KEY=sk-your-key
# OR
GOOGLE_API_KEY=your-gemini-key

# --- Model Configuration ---
MODEL=gpt-4o-mini
STRONG_MODEL=gpt-4-turbo

# --- Database (PostgreSQL) ---
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=resume_pipeline

# --- Storage (Optional) ---
ENABLE_S3=false
# ENABLE_NEXTCLOUD=false

```

### 3. Launch the Application

Build and start the services using Docker Compose:

```bash
docker-compose up -d --build

```

* **Frontend**: Access the dashboard at `http://localhost:3000`
* **API Docs**: Explore the backend API at `http://localhost:8000/docs`

---

## 📋 How to Use

### 1. Create a Career Profile

Navigate to the **Profiles** tab in the UI. You can create a master profile containing all your:

* Work Experience
* Education & Certifications
* Projects & Skills
* Achievements (with metrics)

### 2. Add a Target Job

Navigate to the **New Job** page. You can:

* Paste a Job URL (if scraping is enabled)
* Paste the raw Job Description text
* Upload a JSON job file

The system will analyze the job description to extract required skills, keywords, and experience levels.

### 3. Generate Resume

Click **Generate** on the job details page. You can customize:

* **Template**: Choose between `modern-deedy` (LaTeX), `awesome-cv` (LaTeX), or `Standard` (HTML/PDF).
* **Model**: Select which AI model to use for this specific run.
* **Refinement**: Enable AI critique loops to improve content quality.

Watch the **Live Logs** to see the AI drafting, critiquing, and compiling your document in real-time.

### 4. Download & Edit

Once complete, download the generated PDF or the source files (.tex/.json). You can also view the AI's critique score and feedback directly in the dashboard.

---

## 🔧 Development

### Project Structure

```
resume-pipeline/
├── backend/                # FastAPI application
│   ├── resume_pipeline/    # Core logic (analyzers, generators)
│   ├── api.py              # API Endpoints
│   ├── worker.py           # Background task worker
│   ├── models.py           # SQLAlchemy Database Models
│   └── templates/          # Resume templates (Jinja2 & LaTeX)
│
├── frontend/               # React application
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   ├── pages/          # Application views
│   │   └── services/       # API client
│   └── Dockerfile
│
├── docker-compose.yml      # Service orchestration
└── .env                    # Configuration secrets

```

### Local Development

The `docker-compose.yml` mounts the `backend/` directory into the container, enabling hot-reloading for the API.

To rebuild specific services after adding dependencies:

```bash
docker-compose up -d --build api worker

```

---

## 🐳 Docker Services

| Service | Internal Port | Host Port | Description |
| --- | --- | --- | --- |
| `frontend` | 80 | 3000 | Web Dashboard |
| `api` | 8000 | 8000 | REST API |
| `db` | 5432 | 5432 | PostgreSQL Database |
| `redis` | 6379 | 6379 | Caching & Message Queue |
| `worker` | - | - | Background Processing |

---

## 📝 License

MIT License - see LICENSE file for details.

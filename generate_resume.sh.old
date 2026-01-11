#!/bin/bash
#
# Resume Generation Helper Script
# Usage: ./generate_resume.sh jobs/company_position.json [options]
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Display usage
usage() {
  echo "Usage: $0 <path-to-job.json> [options]"
  echo ""
  echo "Options:"
  echo "  --template TEMPLATE     LaTeX template: modern-deedy (default) or awesome-cv"
  echo "  --model MODEL           Base model (default: gpt-5-mini)"
  echo "  --strong-model MODEL    Strong model for refinement (default: gpt-4o-mini)"
  echo "  --output-dir DIR        Output directory (default: ./output)"
  echo "  --no-cache              Disable caching (force fresh generation)"
  echo ""
  echo "Examples:"
  echo "  $0 jobs/dcs_senior_engineer.json"
  echo "  $0 jobs/lockheed_rf_engineer.json --template awesome-cv"
  echo "  $0 jobs/job.json --no-cache"
  exit 1
}

# Check arguments
if [ -z "$1" ]; then
  echo -e "${RED}Error: Job file path required${NC}"
  usage
fi

JOB_FILE="$1"
shift

# Verify job file exists
if [ ! -f "$JOB_FILE" ]; then
  echo -e "${RED}Error: Job file not found: $JOB_FILE${NC}"
  exit 1
fi

# Verify required files exist
if [ ! -f "career_profile.json" ]; then
  echo -e "${RED}Error: career_profile.json not found in current directory${NC}"
  exit 1
fi

if [ ! -f ".env" ]; then
  echo -e "${RED}Error: .env file not found in current directory${NC}"
  echo "Create .env with: OPENAI_API_KEY=sk-your-key-here"
  exit 1
fi

# Set user/group IDs to match host
export USER_ID=$(id -u)
export GROUP_ID=$(id -g)

# Create output directory if it doesn't exist
mkdir -p output

# Extract job details for display
COMPANY=$(jq -r '.job_details.company // "Unknown"' "$JOB_FILE")
JOB_TITLE=$(jq -r '.job_details.job_title // "Unknown"' "$JOB_FILE")

# Parse template from args (default: modern-deedy)
TEMPLATE="modern-deedy"
for arg in "$@"; do
  if [[ "$arg" == "--template" ]]; then
    TEMPLATE_NEXT=true
  elif [[ "$TEMPLATE_NEXT" == true ]]; then
    TEMPLATE="$arg"
    TEMPLATE_NEXT=false
  fi
done

# Check if cache is disabled
CACHE_STATUS="${GREEN}enabled${NC}"
for arg in "$@"; do
  if [[ "$arg" == "--no-cache" ]]; then
    CACHE_STATUS="${YELLOW}disabled${NC}"
  fi
done

echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Resume Generation Pipeline          ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Company:${NC}   $COMPANY"
echo -e "${BLUE}Position:${NC}  $JOB_TITLE"
echo -e "${BLUE}Job File:${NC}  $JOB_FILE"
echo -e "${BLUE}Template:${NC}  $TEMPLATE"
echo -e "${BLUE}Cache:${NC}     $CACHE_STATUS"
echo -e "${BLUE}User ID:${NC}   $USER_ID:$GROUP_ID"
echo ""
echo -e "${YELLOW}Starting pipeline...${NC}"
echo ""

# Run the pipeline (updated to use Python module)
docker compose run --rm resume-generator \
  python -m resume_pipeline "$JOB_FILE" career_profile.json "$@"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
  echo ""
  echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║   ✓ Resume Generation Complete!       ║${NC}"
  echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
  echo ""

  # Get today's date directory (EST to match Python)
  TODAY=$(TZ='America/New_York' date +%Y%m%d)
  OUTPUT_PATH="output/$TODAY"

  echo "Output directory: ${BLUE}$OUTPUT_PATH${NC}"
  echo ""

  # Find the most recent .tex file in today's directory
  LATEST_TEX=$(ls -t "$OUTPUT_PATH"/*.tex 2>/dev/null | head -1)
  if [ -n "$LATEST_TEX" ]; then
    echo -e "${YELLOW}LaTeX file:${NC} $(basename "$LATEST_TEX")"
    echo ""

    if [[ "$TEMPLATE" == "modern-deedy" ]]; then
      echo "To compile to PDF:"
      echo "  ${BLUE}cd $OUTPUT_PATH${NC}"
      echo "  ${BLUE}pdflatex $(basename "$LATEST_TEX")${NC}"
    elif [[ "$TEMPLATE" == "awesome-cv" ]]; then
      echo "To compile to PDF:"
      echo "  ${BLUE}cd $OUTPUT_PATH${NC}"
      echo "  ${BLUE}xelatex $(basename "$LATEST_TEX")${NC}"
    fi
    echo ""
  fi

  # Check cache directory
  CACHE_FILES=$(ls -1 output/.cache/*.json 2>/dev/null | wc -l)
  if [ "$CACHE_FILES" -gt 0 ]; then
    echo -e "${BLUE}Cache:${NC} $CACHE_FILES cached pipeline state(s)"
    echo ""
  fi
else
  echo -e "${RED}╔════════════════════════════════════════╗${NC}"
  echo -e "${RED}║   ✗ Pipeline Failed                    ║${NC}"
  echo -e "${RED}╚════════════════════════════════════════╝${NC}"
  echo -e "${RED}Exit code: $EXIT_CODE${NC}"
  exit $EXIT_CODE
fi

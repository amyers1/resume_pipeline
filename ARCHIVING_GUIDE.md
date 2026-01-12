# Multiple Runs Per Day - New Archiving Architecture

## Overview

The pipeline now supports **multiple runs per day** without overwriting previous outputs. Each run is stored in a time-stamped subdirectory within the date folder.

## Directory Structure

```
output/
├── .cache/                           # Shared cache across all dates/runs
│   └── a1b2c3d4e5f6g7h8.json        # Cached pipeline states
│
└── 20260109/                         # Date folder (YYYYMMDD)
    ├── run_093045/                   # First run: 9:30:45 AM
    │   ├── dcs_senior_systems_engineer.tex
    │   ├── dcs_senior_systems_engineer.pdf
    │   ├── jd_requirements.json
    │   ├── matched_achievements.json
    │   ├── draft_resume.json
    │   ├── critique.json
    │   ├── final_resume.json
    │   └── structured_resume.json
    │
    ├── run_140312/                   # Second run: 2:03:12 PM
    │   ├── dcs_senior_systems_engineer.tex
    │   ├── dcs_senior_systems_engineer.pdf
    │   └── ...
    │
    ├── run_183520/                   # Third run: 6:35:20 PM
    │   └── ...
    │
    └── latest -> run_183520/         # Symlink to most recent run
```

## How It Works

### Run Subdirectories

Each pipeline execution creates a new subdirectory named `run_HHMMSS` where:
- `HH` = Hour (00-23, 24-hour format)
- `MM` = Minute (00-59)
- `SS` = Second (00-59)

Example: A run at 2:03:12 PM creates `run_140312/`

### Latest Symlink

The `latest` symlink always points to the most recent run within that day's directory:
- **Linux/Mac**: Use `cd output/20260109/latest` to access latest run
- **Windows**: Symlink may not work; use the actual `run_HHMMSS` directory

### Accessing Outputs

**Most Recent Run:**
```bash
# Navigate to latest run
cd output/20260109/latest

# Or use full path
ls output/20260109/latest/*.tex
```

**Specific Run:**
```bash
# Access a specific run by timestamp
cd output/20260109/run_093045

# List all runs for a date
ls -d output/20260109/run_*
```

**All Runs Chronologically:**
```bash
# List runs in order
ls -dt output/20260109/run_*

# Count runs for today
ls -d output/20260109/run_* | wc -l
```

## Benefits

### 1. No Data Loss
- Every run is preserved automatically
- Previous attempts are never overwritten
- Easy to compare different versions

### 2. Easy Comparison
```bash
# Compare two runs
diff output/20260109/run_093045/final_resume.json \
     output/20260109/run_140312/final_resume.json

# View first and last runs side-by-side
code -d output/20260109/run_093045/dcs_senior_systems_engineer.tex \
        output/20260109/latest/dcs_senior_systems_engineer.tex
```

### 3. Debugging Multiple Iterations
- Track how resume evolved throughout the day
- Identify when specific changes were made
- Rollback to previous version if needed

### 4. Experimentation Friendly
```bash
# Try different templates for same job
./generate_resume.sh jobs/job.json --template modern-deedy
./generate_resume.sh jobs/job.json --template awesome-cv

# Compare outputs
ls output/20260109/run_*/dcs_*.tex
```

## Usage Examples

### Basic Run
```bash
# Creates: output/20260109/run_153012/
./generate_resume.sh jobs/dcs_position.json
```

### Multiple Runs Same Day
```bash
# Run 1 - Morning version
./generate_resume.sh jobs/dcs_position.json

# Run 2 - After updating career profile
vim career_profile.json
./generate_resume.sh jobs/dcs_position.json

# Run 3 - Different template
./generate_resume.sh jobs/dcs_position.json --template awesome-cv

# All three runs preserved in separate directories
```

### With PDF Compilation
```bash
# Each run creates both .tex and .pdf in its own directory
./generate_resume.sh jobs/job.json --compile-pdf

# Output: output/20260109/run_143025/dcs_senior_systems_engineer.pdf
```

### With Google Drive Upload
```bash
# Upload includes run timestamp in Google Drive folder structure
./generate_resume.sh jobs/job.json --compile-pdf --upload-gdrive

# Creates in Google Drive:
# Resumes/20260109/run_143025/dcs_senior_systems_engineer.pdf
```

## Cleanup Strategies

### Keep Last N Runs Per Day
```bash
# Keep only last 3 runs for each date
for date_dir in output/202*; do
  cd "$date_dir"
  ls -dt run_* | tail -n +4 | xargs rm -rf
  cd ..
done
```

### Delete Old Dates
```bash
# Delete date directories older than 30 days
find output -maxdepth 1 -type d -name "202*" -mtime +30 -exec rm -rf {} \;
```

### Keep Only Latest Per Day
```bash
# For each date, keep only the latest run
for date_dir in output/202*/; do
  latest=$(ls -t "$date_dir"/run_* 2>/dev/null | head -1)
  if [ -n "$latest" ]; then
    find "$date_dir" -maxdepth 1 -name "run_*" ! -samefile "$latest" -exec rm -rf {} \;
  fi
done
```

### Selective Archiving
```bash
# Archive runs older than 7 days to compressed format
tar -czf archive_$(date +%Y%m%d).tar.gz output/*/run_* --mtime +7
find output -name "run_*" -mtime +7 -exec rm -rf {} \;
```

## Disk Space Considerations

### Typical Run Size
- Without PDF: ~50-100 KB (JSON + LaTeX)
- With PDF: ~200-500 KB (includes compiled PDF)
- Cache files: ~100-200 KB (shared, not per-run)

### Estimate Daily Usage
- 5 runs/day × 500 KB = ~2.5 MB/day
- 30 days × 2.5 MB = ~75 MB/month

### Monitor Usage
```bash
# Check size of all output
du -sh output/

# Check size per date
du -sh output/202*/

# Check size per run
du -sh output/20260109/run_*
```

## Troubleshooting

### Symlink Not Created (Windows)
On Windows, symlink creation may fail without admin privileges:
```bash
# Workaround: Use the actual directory name
cd output/20260109/run_143025  # Instead of 'latest'
```

### Finding Latest Run Programmatically
```bash
# Shell script
LATEST_RUN=$(ls -t output/20260109/run_* | head -1)
echo "Latest run: $LATEST_RUN"

# Python
from pathlib import Path
date_dir = Path("output/20260109")
latest = max(date_dir.glob("run_*"), key=lambda p: p.name)
print(f"Latest run: {latest}")
```

### Accidentally Deleted a Run
If you delete a run directory:
- Other runs are unaffected
- Cache is preserved (shared across all runs)
- Can regenerate by re-running with same inputs

### Cache Behavior with Multiple Runs
- Cache is **shared** across all runs and dates
- Multiple runs of the same job will hit cache (faster)
- Each run still gets its own output directory
- Use `--no-cache` to bypass cache and force fresh generation

## Migration from Old Structure

If you have existing outputs in the old format (`output/20260109/*.tex`), they remain accessible:

```bash
# Old structure (still works if you haven't updated)
output/20260109/dcs_senior_systems_engineer.tex

# New structure (after update)
output/20260109/run_143025/dcs_senior_systems_engineer.tex
output/20260109/latest/dcs_senior_systems_engineer.tex
```

No manual migration needed - old files remain in place and new runs use the new structure.

## Best Practices

1. **Use `latest` symlink** for quick access to most recent run
2. **Name runs descriptively** if comparing many versions (use git tags or notes)
3. **Clean up periodically** to manage disk space
4. **Archive before cleanup** if you need historical record
5. **Check cache** before running multiple times - may want `--no-cache` for true A/B testing

## Summary

The new time-based subdirectory architecture:
- ✅ Preserves all runs automatically
- ✅ Easy to access latest via symlink
- ✅ Simple chronological organization
- ✅ Enables side-by-side comparison
- ✅ No configuration changes needed
- ✅ Works with existing cache system
- ✅ Minimal disk space overhead

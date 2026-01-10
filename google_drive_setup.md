# Google Drive Integration Setup

This guide explains how to set up Google Drive integration for automatic resume uploads.

## Overview

The pipeline can automatically upload generated PDF and LaTeX files to Google Drive, organized in date-based folders.

**Folder Structure:**
```
Google Drive/
└── Resumes/              # Configurable root folder
    ├── 20260109/         # Date-based subfolders
    │   ├── dcs_senior_systems_engineer.pdf
    │   └── dcs_senior_systems_engineer.tex
    └── 20260110/
        └── ...
```

## Prerequisites

- Google account
- Access to Google Cloud Console
- Python 3.11+

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Name your project (e.g., "Resume Pipeline")
4. Click "Create"

## Step 2: Enable Google Drive API

1. In your project, go to "APIs & Services" → "Library"
2. Search for "Google Drive API"
3. Click on it and click "Enable"

## Step 3: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - User Type: External (for personal use)
   - App name: Resume Pipeline
   - User support email: Your email
   - Developer contact: Your email
   - Scopes: Leave default
   - Test users: Add your email
   - Click "Save and Continue"

4. Back to "Create OAuth client ID":
   - Application type: Desktop app
   - Name: Resume Pipeline Desktop
   - Click "Create"

5. Download the credentials:
   - Click the download button (⬇) next to your new OAuth 2.0 Client ID
   - Save as `credentials.json` in your project root

## Step 4: Place Credentials File

```bash
# Your project structure should look like:
resume-pipeline/
├── credentials.json          # ← Place here
├── career_profile.json
├── .env
├── jobs/
└── resume_pipeline/
```

## Step 5: First-Time Authentication

The first time you run the pipeline with `--upload-gdrive`, a browser window will open:

```bash
./generate_resume.sh jobs/job.json --compile-pdf --upload-gdrive
```

1. Browser will open automatically
2. Log in to your Google account
3. Grant permission to "Resume Pipeline" to access Google Drive
4. The browser will show "The authentication flow has completed"
5. A `token.json` file will be created automatically

**Important:** The `token.json` file stores your authentication. Keep it secure!

## Step 6: Test the Integration

```bash
# Test with PDF compilation and upload
./generate_resume.sh jobs/test_job.json --compile-pdf --upload-gdrive

# Expected output:
# [7/7] Post-processing...
#   Compiling dcs_senior_systems_engineer.tex with xelatex...
#   ✓ PDF created: dcs_senior_systems_engineer.pdf
#
#   Uploading to Google Drive...
#   ✓ Created folder: Resumes (ID: ...)
#   ✓ Created folder: 20260109 (ID: ...)
#   ✓ Uploaded to Google Drive: dcs_senior_systems_engineer.tex
#     File ID: ...
#     Link: https://drive.google.com/file/d/.../view
#   ✓ Uploaded to Google Drive: dcs_senior_systems_engineer.pdf
#     File ID: ...
#     Link: https://drive.google.com/file/d/.../view
```

## Usage

### Basic Upload (LaTeX only, no PDF)

```bash
./generate_resume.sh jobs/job.json --upload-gdrive
```

### With PDF Compilation

```bash
./generate_resume.sh jobs/job.json --compile-pdf --upload-gdrive
```

### Custom Folder Name

```bash
./generate_resume.sh jobs/job.json --upload-gdrive --gdrive-folder "My Resumes"
```

### Custom Credentials Location

```bash
python -m resume_pipeline jobs/job.json career_profile.json \
  --upload-gdrive \
  --gdrive-credentials /path/to/credentials.json \
  --gdrive-token /path/to/token.json
```

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `--upload-gdrive` | Disabled | Enable Google Drive upload |
| `--gdrive-folder` | `Resumes` | Root folder name in Google Drive |
| `--gdrive-credentials` | `credentials.json` | Path to OAuth credentials |
| `--gdrive-token` | `token.json` | Path to save/load auth token |

## File Organization

### Automatic Folder Creation

The pipeline automatically creates:
1. **Root folder** (e.g., "Resumes") - Created once
2. **Date subfolder** (e.g., "20260109") - Created daily

### File Naming

Files use the same naming convention as local output:
- `dcs_senior_systems_engineer.tex`
- `dcs_senior_systems_engineer.pdf`

Multiple runs on the same day create new versions in Google Drive (Google Drive handles versioning automatically).

## Security Considerations

### Protect Your Credentials

```bash
# Add to .gitignore
echo "credentials.json" >> .gitignore
echo "token.json" >> .gitignore

# Set restrictive permissions
chmod 600 credentials.json
chmod 600 token.json
```

### Token Expiration

- Tokens expire after ~7 days of inactivity
- Pipeline will automatically refresh expired tokens
- If refresh fails, re-authenticate by deleting `token.json`

### Revoke Access

To revoke pipeline access to Google Drive:
1. Go to [Google Account Permissions](https://myaccount.google.com/permissions)
2. Find "Resume Pipeline"
3. Click "Remove Access"

## Troubleshooting

### "credentials.json not found"

```bash
# Check file exists
ls -la credentials.json

# Ensure it's in project root
pwd
# Should show /path/to/resume-pipeline
```

### "Authentication failed"

```bash
# Delete token and re-authenticate
rm token.json
./generate_resume.sh jobs/job.json --upload-gdrive
```

### "Permission denied" errors

```bash
# Check file permissions
ls -la credentials.json token.json

# Fix if needed
chmod 600 credentials.json token.json
```

### "API has not been used" error

1. Ensure Google Drive API is enabled in Cloud Console
2. Wait 1-2 minutes for API activation
3. Retry

### Upload succeeds but files not visible

1. Check your Google Drive "Resumes" folder
2. Files are uploaded to the authenticated account
3. Verify you're logged into the correct Google account

## Docker Usage

### Mount Credentials

```yaml
# docker-compose.yml
volumes:
  - ./credentials.json:/app/credentials.json:ro
  - ./token.json:/app/token.json:rw
```

### Run with Upload

```bash
docker-compose run --rm resume-generator \
  python -m resume_pipeline jobs/job.json career_profile.json \
  --compile-pdf --upload-gdrive
```

### First-Time Setup in Docker

The OAuth flow requires a browser, which may not work in Docker. Recommended approach:

1. **Authenticate locally first:**
   ```bash
   python -m resume_pipeline jobs/job.json career_profile.json --upload-gdrive
   # Complete browser authentication
   ```

2. **Then use Docker with existing token:**
   ```bash
   # token.json now exists
   docker-compose run --rm resume-generator \
     python -m resume_pipeline jobs/job.json career_profile.json --upload-gdrive
   ```

## Advanced Usage

### Custom Upload Logic

```python
from resume_pipeline.uploaders import GoogleDriveUploader

# Initialize uploader
uploader = GoogleDriveUploader(
    credentials_file="credentials.json",
    token_file="token.json"
)

# Create custom folder structure
projects_folder = uploader.create_folder("Projects")
resume_folder = uploader.create_folder("Resumes", parent_id=projects_folder)

# Upload file
file_id = uploader.upload_file(
    Path("output/20260109/resume.pdf"),
    folder_id=resume_folder
)
```

### Disable Upload for Specific Runs

```bash
# Upload enabled by default in config
python -m resume_pipeline jobs/job.json career_profile.json
# No --upload-gdrive flag = no upload
```

## FAQ

**Q: Do I need a Google Workspace account?**
A: No, a free personal Google account works fine.

**Q: What are the storage limits?**
A: Free Google Drive accounts have 15 GB. Resume PDFs are typically <100 KB each.

**Q: Can I share uploaded resumes?**
A: Yes, use Google Drive's built-in sharing features after upload.

**Q: Can multiple users share one credentials.json?**
A: No, each user should create their own OAuth credentials for security.

**Q: Does this work with shared Google Drive folders?**
A: Yes, as long as you have write permission to the shared folder.

## Support

For issues with Google Drive integration:
1. Check this guide's troubleshooting section
2. Verify OAuth credentials are correctly configured
3. Ensure Google Drive API is enabled
4. Check Python Google API client documentation

For general pipeline issues, see main README.md.

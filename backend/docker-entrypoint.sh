#!/bin/bash
set -e

# Get user and group IDs from environment (defaults to 1000)
USER_ID=${USER_ID:-1000}
GROUP_ID=${GROUP_ID:-1000}

# Create a user/group with the same IDs as the host
groupadd -g $GROUP_ID appgroup 2>/dev/null || true
useradd -u $USER_ID -g $GROUP_ID -m appuser 2>/dev/null || true

# Make sure font cache sees mounted fonts (e.g., /usr/share/fonts/custom)
fc-cache -f -v &>/dev/null || true

# Change ownership of output directory to match host user
chown -R $USER_ID:$GROUP_ID /app/output 2>/dev/null || true

# Execute the command as the created user
exec gosu $USER_ID:$GROUP_ID "$@"

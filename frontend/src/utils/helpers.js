/**
 * Format file size in bytes to human-readable format
 */
export const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};

/**
 * Format ISO timestamp to readable date
 */
export const formatDate = (isoString) => {
  if (!isoString) return 'N/A';
  const date = new Date(isoString);
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

/**
 * Format duration in seconds to readable format
 */
export const formatDuration = (seconds) => {
  if (!seconds) return '0s';
  const minutes = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return minutes > 0 ? `${minutes}m ${secs}s` : `${secs}s`;
};

/**
 * Get relative time (e.g., "2 minutes ago")
 */
export const getRelativeTime = (isoString) => {
  if (!isoString) return 'Unknown';
  const date = new Date(isoString);
  const now = new Date();
  const seconds = Math.floor((now - date) / 1000);

  if (seconds < 60) return 'Just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
  const days = Math.floor(hours / 24);
  return `${days} day${days > 1 ? 's' : ''} ago`;
};

/**
 * Debounce function
 */
export const debounce = (func, wait) => {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
};

/**
 * Validate job ID format
 */
export const isValidJobId = (jobId) => {
  if (!jobId || typeof jobId !== 'string') return false;
  if (jobId.includes('..') || jobId.includes('/') || jobId.includes('\\')) return false;
  if (jobId.length > 200) return false;
  return true;
};

/**
 * Parse error from API response
 */
export const parseError = (error) => {
  if (error.response?.data?.message) {
    return error.response.data.message;
  }
  if (error.message) {
    return error.message;
  }
  return 'An unexpected error occurred';
};

/**
 * Get status icon
 */
export const getStatusIcon = (status) => {
  const icons = {
    completed: '✅',
    processing: '⏳',
    failed: '❌',
    queued: '⏸️',
  };
  return icons[status] || '•';
};

/**
 * Calculate estimated time remaining based on progress and elapsed time
 */
export const estimateTimeRemaining = (progressPercent, startedAt) => {
  if (!startedAt || progressPercent <= 0 || progressPercent >= 100) {
    return null;
  }

  const elapsed = (new Date() - new Date(startedAt)) / 1000; // seconds
  const rate = progressPercent / elapsed; // percent per second
  const remaining = (100 - progressPercent) / rate; // seconds

  return formatDuration(remaining);
};

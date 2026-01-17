import { Link } from 'react-router-dom';
import { STATUS_COLORS } from '../utils/constants';
import { formatDate, getStatusIcon } from '../utils/helpers';

export default function JobCard({ job }) {
  const { job_id, company, job_title, created_at, status, template, priority } = job;

  return (
    <Link
      to={`/jobs/${job_id}`}
      className="block bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-primary-500 dark:hover:border-primary-400 transition-all hover:shadow-lg"
    >
      <div className="p-5">
        {/* Header with status */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white truncate">
              {company}
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 truncate">
              {job_title}
            </p>
          </div>
          <span
            className={`ml-3 px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1 flex-shrink-0 ${
              STATUS_COLORS[status] || STATUS_COLORS.queued
            }`}
          >
            <span>{getStatusIcon(status)}</span>
            <span className="capitalize">{status}</span>
          </span>
        </div>

        {/* Created date */}
        <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 mb-3">
          <span>Created:</span>
          <span>{formatDate(created_at)}</span>
        </div>

        {/* Details row */}
        <div className="flex items-center gap-4 text-sm">
          {priority !== undefined && (
            <div className="flex items-center gap-1 text-gray-600 dark:text-gray-400">
              <span>⚡</span>
              <span>Priority: {priority}</span>
            </div>
          )}
          {template && (
            <div className="flex items-center gap-1 text-gray-600 dark:text-gray-400">
              <span>📄</span>
              <span>{template}</span>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="mt-4 pt-3 border-t border-gray-200 dark:border-gray-700 flex items-center gap-3">
          <button className="text-sm font-medium text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300">
            View Details
          </button>
          {status === 'completed' && (
            <button
              onClick={(e) => {
                e.preventDefault();
                // Handle regenerate
              }}
              className="text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200"
            >
              Regenerate
            </button>
          )}
        </div>
      </div>
    </Link>
  );
}

import { Link } from "react-router-dom";
import { STATUS_COLORS } from "../utils/constants";
import { formatDate, getStatusIcon } from "../utils/helpers";

export default function JobCard({ job }) {
    const {
        id,
        company,
        job_title,
        created_at,
        status,
        template,
        priority,
        final_score,
    } = job;

    const score = final_score ? (final_score * 10).toFixed(1) : null;
    const scoreColor =
        score >= 8
            ? "text-green-600 dark:text-green-400"
            : score >= 6
              ? "text-yellow-600 dark:text-yellow-400"
              : "text-red-600 dark:text-red-400";

    return (
        <Link
            to={`/jobs/${id}`}
            className="block bg-white dark:bg-background-surface rounded-lg border border-gray-200 dark:border-gray-700 hover:border-primary-500 dark:hover:border-primary-400 transition-all duration-200 hover:shadow-lg"
        >
            <div className="p-5">
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                    <div className="flex-1 min-w-0">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white truncate">
                            {company}
                        </h3>
                        <p className="text-sm text-gray-600 dark:text-gray-400 truncate">
                            {job_title}
                        </p>
                    </div>
                    {/* Status Badge */}
                    <span
                        className={`ml-3 px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1.5 flex-shrink-0 ${
                            STATUS_COLORS[status] || STATUS_COLORS.queued
                        }`}
                    >
                        <span>{getStatusIcon(status)}</span>
                        <span className="capitalize">{status}</span>
                    </span>
                </div>

                {/* Score and Date */}
                <div className="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400 mb-4">
                    <div className="flex items-center gap-1.5">
                        <span className="font-medium text-gray-700 dark:text-gray-300">
                            Score:
                        </span>
                        <span className={`font-bold ${scoreColor}`}>
                            {score ? `${score}/10` : "N/A"}
                        </span>
                    </div>
                    <span>{formatDate(created_at)}</span>
                </div>

                {/* Details row */}
                <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
                    {template && (
                        <div className="flex items-center gap-1.5">
                            <span title="Template">📄</span>
                            <span className="bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded">
                                {template}
                            </span>
                        </div>
                    )}
                    {priority !== undefined && (
                        <div className="flex items-center gap-1.5">
                            <span title="Priority">⚡</span>
                            <span>{priority}</span>
                        </div>
                    )}
                </div>

                {/* Actions */}
                <div className="mt-5 pt-4 border-t border-gray-200 dark:border-gray-700">
                    <span className="text-sm font-medium text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300">
                        View Details →
                    </span>
                </div>
            </div>
        </Link>
    );
}

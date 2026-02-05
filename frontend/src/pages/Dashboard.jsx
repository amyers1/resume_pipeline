import { useEffect, useState, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import { apiService } from "../services/api";
import { useApp } from "../contexts/AppContext";
import JobCard from "../components/JobCard";

export default function Dashboard() {
    const { state, dispatch, actionTypes } = useApp();
    const [jobsList, setJobsList] = useState([]);
    const [loading, setLoading] = useState(true);
    const [pagination, setPagination] = useState({
        page: 1,
        pageSize: 20,
        totalPages: 1,
        totalCount: 0,
    });
    const [searchTerm, setSearchTerm] = useState("");
    const debounceTimer = useRef(null);

    const fetchJobs = useCallback(
        async (page = 1, search = "") => {
            try {
                setLoading(true);
                const response = await apiService.listJobs({
                    page,
                    pageSize: pagination.pageSize,
                    search: search.trim(),
                });

                const jobs = response.data.items || response.data || [];
                setJobsList(jobs);

                setPagination({
                    page: response.data.page || 1,
                    pageSize: response.data.page_size || 20,
                    totalPages: response.data.total_pages || 1,
                    totalCount: response.data.total_count || jobs.length,
                });

                dispatch({
                    type: actionTypes.SET_JOBS,
                    payload: jobs,
                });
            } catch (error) {
                console.error("Failed to fetch jobs:", error);
                setJobsList([]);
            } finally {
                setLoading(false);
            }
        },
        [pagination.pageSize, dispatch, actionTypes],
    );

    useEffect(() => {
        fetchJobs(1, searchTerm);
    }, []);

    const debouncedSearch = useCallback(
        (value) => {
            if (debounceTimer.current) {
                clearTimeout(debounceTimer.current);
            }

            debounceTimer.current = setTimeout(() => {
                setSearchTerm(value);
                fetchJobs(1, value);
            }, 300);
        },
        [fetchJobs],
    );

    const handlePageChange = (newPage) => {
        if (newPage >= 1 && newPage <= pagination.totalPages) {
            fetchJobs(newPage, searchTerm);
        }
    };

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
            {/* Header */}
            <div className="mb-6 sm:mb-8">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
                    <div>
                        <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white">
                            Resume Jobs
                        </h1>
                        <p className="text-sm sm:text-base text-slate-600 dark:text-slate-400 mt-1">
                            Manage and monitor your resume generation jobs
                        </p>
                    </div>
                    <Link
                        to="/new-job"
                        className="w-full sm:w-auto px-6 py-3 bg-primary-600 hover:bg-primary-700 dark:bg-primary-500 dark:hover:bg-primary-600 text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2 shadow-lg shadow-primary-500/20 hover:shadow-primary-500/40"
                    >
                        <span className="text-lg">+</span>
                        <span>New Resume</span>
                    </Link>
                </div>

                {/* Filters */}
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 sm:gap-4">
                    <div className="flex-1">
                        <input
                            type="text"
                            placeholder="Search by company..."
                            onChange={(e) => debouncedSearch(e.target.value)}
                            className="w-full px-4 py-2.5 sm:py-2 border border-slate-300 dark:border-slate-600 bg-white dark:bg-background-surface text-slate-900 dark:text-white placeholder-slate-500 dark:placeholder-slate-400 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent text-base sm:text-sm"
                        />
                    </div>
                </div>

                {/* Mobile: Show count */}
                <p className="text-xs text-slate-400 mt-3 sm:hidden">
                    {pagination.totalCount} total jobs
                </p>
            </div>

            {/* Job List */}
            {loading ? (
                <div className="flex items-center justify-center py-12">
                    <div className="w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
                </div>
            ) : jobsList.length === 0 ? (
                <div className="text-center py-12 px-4">
                    <div className="text-6xl mb-4">📄</div>
                    <h3 className="text-lg font-medium text-slate-900 dark:text-white mb-2">
                        No jobs yet
                    </h3>
                    <p className="text-slate-600 dark:text-slate-400 mb-6 text-sm sm:text-base">
                        Get started by creating your first resume generation job
                    </p>
                    <Link
                        to="/new-job"
                        className="inline-flex items-center gap-2 px-6 py-3 bg-primary-500 hover:bg-primary-400 text-white font-bold rounded-lg transition-all shadow-lg shadow-primary-500/20 hover:shadow-primary-500/40"
                    >
                        <span>+</span>
                        <span>New Resume</span>
                    </Link>
                </div>
            ) : (
                <>
                    {/* Grid - Responsive columns */}
                    <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
                        {jobsList.map((job) => (
                            <JobCard key={job.id || job.job_id} job={job} />
                        ))}
                    </div>

                    {/* Pagination */}
                    {pagination.totalPages > 1 && (
                        <div className="mt-8 flex flex-col sm:flex-row items-center justify-between gap-4">
                            <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 text-center sm:text-left">
                                Page {pagination.page} of{" "}
                                {pagination.totalPages} ({pagination.totalCount}{" "}
                                total)
                            </p>

                            <div className="flex items-center gap-2">
                                <button
                                    onClick={() =>
                                        handlePageChange(pagination.page - 1)
                                    }
                                    disabled={pagination.page === 1}
                                    className="px-3 sm:px-4 py-2 border border-slate-300 dark:border-slate-600 bg-white dark:bg-background-surface text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm touch-manipulation min-h-[44px]"
                                >
                                    Previous
                                </button>

                                {/* Page numbers - Hide on very small screens */}
                                <div className="hidden xs:flex items-center gap-1">
                                    {Array.from(
                                        {
                                            length: Math.min(
                                                5,
                                                pagination.totalPages,
                                            ),
                                        },
                                        (_, i) => {
                                            let pageNum;
                                            if (pagination.totalPages <= 5) {
                                                pageNum = i + 1;
                                            } else if (pagination.page <= 3) {
                                                pageNum = i + 1;
                                            } else if (
                                                pagination.page >=
                                                pagination.totalPages - 2
                                            ) {
                                                pageNum =
                                                    pagination.totalPages -
                                                    4 +
                                                    i;
                                            } else {
                                                pageNum =
                                                    pagination.page - 2 + i;
                                            }

                                            return (
                                                <button
                                                    key={pageNum}
                                                    onClick={() =>
                                                        handlePageChange(
                                                            pageNum,
                                                        )
                                                    }
                                                    className={`w-10 h-10 flex items-center justify-center rounded-lg text-sm font-medium transition-colors ${
                                                        pageNum ===
                                                        pagination.page
                                                            ? "bg-primary-600 text-white"
                                                            : "text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700"
                                                    }`}
                                                >
                                                    {pageNum}
                                                </button>
                                            );
                                        },
                                    )}
                                </div>

                                <button
                                    onClick={() =>
                                        handlePageChange(pagination.page + 1)
                                    }
                                    disabled={
                                        pagination.page >= pagination.totalPages
                                    }
                                    className="px-3 sm:px-4 py-2 border border-slate-300 dark:border-slate-600 bg-white dark:bg-background-surface text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm touch-manipulation min-h-[44px]"
                                >
                                    Next
                                </button>
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}

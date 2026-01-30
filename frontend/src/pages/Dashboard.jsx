import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useApp } from "../contexts/AppContext";
import { apiService, createAllJobsStatusSSE } from "../services/api";
import JobCard from "../components/JobCard";
import { debounce } from "../utils/helpers";

export default function Dashboard() {
    const { state, dispatch, actionTypes } = useApp();
    const [loading, setLoading] = useState(true);
    const [filters, setFilters] = useState({
        company: "",
        sortBy: "created_at",
        sortOrder: "desc",
    });
    const [currentPage, setCurrentPage] = useState(1);

    const fetchJobs = async (page = 1) => {
        try {
            setLoading(true);

            // Build query params
            const params = {
                page,
                size: 20,
                // Pass filters to API (even if backend support is partial)
                ...(filters.company && { company: filters.company }),
                ...(filters.sortBy && { sort_by: filters.sortBy }),
                ...(filters.sortOrder && { sort_order: filters.sortOrder }),
            };

            const response = await apiService.listJobs(params);
            const data = response.data;

            // FIX: Transform API response to match AppContext reducer expectations
            // API returns: { items, total, page, size }
            // Reducer expects: { jobs, total_count, total_pages, page_size, page }
            const payload = {
                jobs: data.items,
                total_count: data.total,
                page: data.page,
                page_size: data.size,
                total_pages: Math.ceil(data.total / data.size),
            };

            dispatch({ type: actionTypes.SET_JOBS, payload });
        } catch (error) {
            console.error("Failed to fetch jobs:", error);
            dispatch({
                type: actionTypes.SET_JOBS_ERROR,
                payload: "Failed to load jobs",
            });
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        const cleanup = createAllJobsStatusSSE({
            onMessage: (payload) => {
                // Update job in real-time with all its data
                if (payload.id) {
                    dispatch({
                        type: actionTypes.UPDATE_JOB,
                        payload: payload,
                    });
                }
            },
        });

        return () => {
            if (cleanup) cleanup();
        };
    }, [dispatch, actionTypes]);

    useEffect(() => {
        fetchJobs(currentPage);
    }, [currentPage, filters]);

    const debouncedSearch = debounce((value) => {
        setFilters((prev) => ({ ...prev, company: value }));
        setCurrentPage(1);
    }, 300);

    const handlePageChange = (newPage) => {
        setCurrentPage(newPage);
        window.scrollTo({ top: 0, behavior: "smooth" });
    };

    // FIX: Correctly access state from reducer structure
    // Reducer stores list in state.jobs.list
    const rawJobs = state.jobs.list || [];

    // Normalize job IDs to ensure consistency (handle id vs job_id)
    const jobsList = rawJobs.map((job) => ({
        ...job,
        id: job.id || job.job_id,
        job_id: job.id || job.job_id,
    }));

    // FIX: Correctly access pagination from reducer structure
    // Reducer stores pagination in state.jobs.pagination
    const paginationState = state.jobs.pagination || {};
    const pagination = {
        page: paginationState.page || currentPage,
        totalCount: paginationState.totalCount || 0,
        totalPages: paginationState.totalPages || 0,
    };

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {/* Header */}
            <div className="mb-8">
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900 dark:text-white">
                            Resume Jobs
                        </h1>
                        <p className="text-slate-600 dark:text-slate-400 mt-1">
                            Manage and monitor your resume generation jobs
                        </p>
                        {/* Debug info */}
                        <p className="text-xs text-slate-400 mt-1">
                            Showing {jobsList.length} of {pagination.totalCount}{" "}
                            total jobs
                        </p>
                    </div>
                    <Link
                        to="/new-job"
                        className="px-6 py-3 bg-primary-600 hover:bg-primary-700 dark:bg-primary-500 dark:hover:bg-primary-600 text-white font-medium rounded-lg transition-colors flex items-center gap-2"
                    >
                        <span>+</span>
                        <span>New Resume</span>
                    </Link>
                </div>

                {/* Filters */}
                <div className="flex items-center gap-4 flex-wrap">
                    <div className="flex-1 min-w-64">
                        <input
                            type="text"
                            placeholder="Search by company..."
                            onChange={(e) => debouncedSearch(e.target.value)}
                            className="w-full px-4 py-2 border border-slate-300 dark:border-slate-600 bg-white dark:bg-background-surface text-slate-900 dark:text-white rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        />
                    </div>

                    <select
                        value={filters.sortBy}
                        onChange={(e) =>
                            setFilters((prev) => ({
                                ...prev,
                                sortBy: e.target.value,
                            }))
                        }
                        className="px-4 py-2 border border-slate-300 dark:border-slate-600 bg-white dark:bg-background-surface text-slate-900 dark:text-white rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    >
                        <option value="created_at">Sort by Date</option>
                        <option value="company">Sort by Company</option>
                        <option value="status">Sort by Status</option>
                    </select>

                    <select
                        value={filters.sortOrder}
                        onChange={(e) =>
                            setFilters((prev) => ({
                                ...prev,
                                sortOrder: e.target.value,
                            }))
                        }
                        className="px-4 py-2 border border-slate-300 dark:border-slate-600 bg-white dark:bg-background-surface text-slate-900 dark:text-white rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    >
                        <option value="desc">Newest First</option>
                        <option value="asc">Oldest First</option>
                    </select>
                </div>
            </div>

            {/* Job List */}
            {loading && jobsList.length === 0 ? (
                <div className="flex items-center justify-center py-12">
                    <div className="w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
                </div>
            ) : jobsList.length === 0 ? (
                <div className="text-center py-12">
                    <div className="text-6xl mb-4">📄</div>
                    <h3 className="text-lg font-medium text-slate-900 dark:text-white mb-2">
                        No jobs yet
                    </h3>
                    <p className="text-slate-600 dark:text-slate-400 mb-6">
                        Get started by creating your first resume generation job
                    </p>
                    <Link
                        to="/new-job"
                        className="px-6 py-3 bg-primary-500 hover:bg-primary-400 text-white font-bold rounded-lg transition-all shadow-lg shadow-primary-500/20 hover:shadow-primary-500/40 flex items-center gap-2"
                    >
                        <span>+</span>
                        <span>New Resume</span>
                    </Link>
                </div>
            ) : (
                <>
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                        {jobsList.map((job) => (
                            <JobCard key={job.id || job.job_id} job={job} />
                        ))}
                    </div>

                    {/* Pagination */}
                    {pagination.totalPages > 1 && (
                        <div className="mt-8 flex items-center justify-between">
                            <p className="text-sm text-slate-600 dark:text-slate-400">
                                Showing page {pagination.page} of{" "}
                                {pagination.totalPages} ({pagination.totalCount}{" "}
                                total jobs)
                            </p>

                            <div className="flex items-center gap-2">
                                <button
                                    onClick={() =>
                                        handlePageChange(pagination.page - 1)
                                    }
                                    disabled={pagination.page === 1}
                                    className="px-4 py-2 border border-slate-300 dark:border-slate-600 bg-white dark:bg-background-surface text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                >
                                    Previous
                                </button>
                                <button
                                    onClick={() =>
                                        handlePageChange(pagination.page + 1)
                                    }
                                    disabled={
                                        pagination.page ===
                                        pagination.totalPages
                                    }
                                    className="px-4 py-2 border border-slate-300 dark:border-slate-600 bg-white dark:bg-background-surface text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
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

import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { apiService, createJobStatusSSE } from "../services/api";
import { useApp } from "../contexts/AppContext";
import ProgressBar from "../components/ProgressBar";
import StageTimeline from "../components/StageTimeline";
import LiveLog from "../components/LiveLog";
import ArtifactList from "../components/ArtifactList";
import ResubmitModal from "../components/ResubmitModal";
import { STATUS_COLORS } from "../utils/constants";
import {
    formatDate,
    formatDuration,
    getStatusIcon,
    estimateTimeRemaining,
} from "../utils/helpers";

export default function JobDetailPage() {
    const { jobId } = useParams();
    const navigate = useNavigate();
    const { dispatch, actionTypes } = useApp();

    const [job, setJob] = useState(null);
    const [files, setFiles] = useState([]);
    const [loading, setLoading] = useState(true);
    const [events, setEvents] = useState([]);
    const [currentStatus, setCurrentStatus] = useState(null);
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [showResubmitModal, setShowResubmitModal] = useState(false);
    const [deleting, setDeleting] = useState(false);
    const [resubmitting, setResubmitting] = useState(false);

    // Use ref to track if we've already fetched to avoid double-fetching
    const hasFetchedRef = useRef(false);

    // Fetch job details
    const fetchJobDetails = async () => {
        try {
            setLoading(true);
            const response = await apiService.getJobDetails(jobId);
            setJob(response.data);
            dispatch({
                type: actionTypes.SET_CURRENT_JOB,
                payload: response.data,
            });
        } catch (error) {
            console.error("Failed to fetch job details:", error);
            if (error.response?.status === 404) {
                navigate("/");
            }
        } finally {
            setLoading(false);
        }
    };

    // Fetch job files
    const fetchJobFiles = async () => {
        try {
            const response = await apiService.listJobFiles(jobId);
            // API returns direct array, not { files: [] }
            const fileList = Array.isArray(response.data)
                ? response.data
                : response.data.files || [];
            setFiles(fileList);
        } catch (error) {
            console.error("Failed to fetch job files:", error);
            setFiles([]);
        }
    };

    // FIX #2: Handle SSE status updates properly
    const handleStatusUpdate = (payload) => {
        console.log("SSE Update received:", payload);

        // Map backend SSE message fields to frontend state
        const statusUpdate = {
            stage: payload.stage || currentStatus?.stage || "queued",
            progress_percent: payload.progress_percent || payload.percent || 0,
            message: payload.message || "",
            status: payload.status,
            job_id: payload.job_id,
        };

        setCurrentStatus(statusUpdate);

        // Add event to log with timestamp
        setEvents((prev) => [
            ...prev,
            {
                timestamp: new Date().toISOString(),
                stage: statusUpdate.stage,
                message: statusUpdate.message,
                progress: statusUpdate.progress_percent,
                type: payload.status,
            },
        ]);

        // FIX #3: Update job status in state based on message type
        if (payload.status === "job_completed") {
            setJob((prev) => ({ ...prev, status: "completed" }));
            // Fetch files when job completes
            fetchJobFiles();
        } else if (payload.status === "job_failed") {
            setJob((prev) => ({
                ...prev,
                status: "failed",
                error: payload.error || payload.message,
            }));
        } else if (payload.status === "job_started") {
            setJob((prev) => ({ ...prev, status: "processing" }));
        } else if (payload.status === "job_progress") {
            // Keep status as processing during progress updates
            setJob((prev) => ({ ...prev, status: "processing" }));
        }
    };

    // FIX #4: Handle job resubmission with proper error handling
    const handleResubmit = async (config) => {
        try {
            setResubmitting(true);
            const response = await apiService.resubmitJob(jobId, config);

            // Reset state for new run
            setShowResubmitModal(false);
            setEvents([]);
            setCurrentStatus(null);

            // Navigate to the new job
            const newJobId = response.data.job_id || response.data.id;
            navigate(`/jobs/${newJobId}`);
        } catch (error) {
            console.error("Failed to resubmit job:", error);
            const errorMsg =
                error.response?.data?.detail ||
                "Failed to resubmit job. Please try again.";
            alert(errorMsg);
        } finally {
            setResubmitting(false);
        }
    };

    // FIX #5: Handle job deletion with proper error handling
    const handleDelete = async () => {
        try {
            setDeleting(true);
            await apiService.deleteJob(jobId);
            dispatch({ type: actionTypes.REMOVE_JOB, payload: jobId });
            navigate("/");
        } catch (error) {
            console.error("Failed to delete job:", error);
            const errorMsg =
                error.response?.data?.detail ||
                "Failed to delete job. Please try again.";
            alert(errorMsg);
            setDeleting(false);
        }
    };

    // Initial fetch on mount
    useEffect(() => {
        if (!hasFetchedRef.current) {
            hasFetchedRef.current = true;
            setEvents([]);
            setCurrentStatus(null);
            fetchJobDetails();
            fetchJobFiles();
        }
    }, [jobId]);

    // Setup SSE connection
    useEffect(() => {
        let cleanup;

        // Connect SSE for all states to catch updates even if page loads after job starts
        if (job) {
            cleanup = createJobStatusSSE(jobId, {
                onMessage: handleStatusUpdate,
                onError: (error) => {
                    console.error("SSE connection error:", error);
                },
            });
        }

        return () => {
            if (cleanup) cleanup();
        };
    }, [job?.id, jobId]);

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
        );
    }

    if (!job) {
        return (
            <div className="max-w-4xl mx-auto px-4 py-8">
                <div className="text-center">
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
                        Job Not Found
                    </h1>
                    <button
                        onClick={() => navigate("/")}
                        className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                    >
                        Back to Dashboard
                    </button>
                </div>
            </div>
        );
    }

    const isProcessing = job.status === "processing" || job.status === "queued";
    const isCompleted = job.status === "completed";
    const isFailed = job.status === "failed";

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {/* Header */}
            <div className="mb-8">
                <button
                    onClick={() => navigate("/")}
                    className="text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 mb-4 flex items-center gap-2"
                >
                    <span>←</span>
                    <span>Back to Dashboard</span>
                </button>

                <div className="flex items-start justify-between">
                    <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                                {job.company}
                            </h1>
                            <span
                                className={`px-3 py-1 rounded-full text-sm font-medium flex items-center gap-2 ${
                                    STATUS_COLORS[job.status] ||
                                    STATUS_COLORS.queued
                                }`}
                            >
                                <span>{getStatusIcon(job.status)}</span>
                                <span className="capitalize">{job.status}</span>
                            </span>
                        </div>
                        <p className="text-xl text-gray-600 dark:text-gray-400">
                            {job.job_title}
                        </p>
                        <p className="text-sm text-gray-500 dark:text-gray-500 mt-2">
                            Created {formatDate(job.created_at)}
                        </p>
                    </div>

                    <div className="flex items-center gap-3">
                        {(isCompleted || isFailed) && (
                            <button
                                onClick={() => setShowResubmitModal(true)}
                                disabled={resubmitting}
                                className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {resubmitting
                                    ? "Resubmitting..."
                                    : "Regenerate"}
                            </button>
                        )}
                        <button
                            onClick={() => setShowDeleteConfirm(true)}
                            disabled={deleting}
                            className="px-4 py-2 border border-red-600 text-red-600 dark:border-red-400 dark:text-red-400 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {deleting ? "Deleting..." : "Delete"}
                        </button>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Main Content */}
                <div className="lg:col-span-2 space-y-6">
                    {/* FIX #6: Progress Card - Show for processing AND queued */}
                    {(isProcessing || job.status === "queued") && (
                        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                                Generation Progress
                            </h2>
                            <ProgressBar
                                percent={currentStatus?.progress_percent || 0}
                                stage={currentStatus?.stage || "queued"}
                                message={
                                    currentStatus?.message ||
                                    "Waiting to start..."
                                }
                            />
                        </div>
                    )}

                    {/* FIX #7: Results Card - Only show when completed AND files exist */}
                    {isCompleted && files.length > 0 && (
                        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                                Results
                            </h2>
                            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                                Generated Files
                            </h3>
                            <ArtifactList jobId={jobId} files={files} />
                        </div>
                    )}

                    {/* Completion message when no files */}
                    {isCompleted && files.length === 0 && (
                        <div className="bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800 p-6">
                            <p className="text-green-700 dark:text-green-300 text-sm">
                                Job completed successfully. Files may still be
                                processing.
                            </p>
                        </div>
                    )}

                    {/* Error Card */}
                    {isFailed && (
                        <div className="bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800 p-6">
                            <h3 className="text-lg font-semibold text-red-900 dark:text-red-100 mb-2">
                                Generation Failed
                            </h3>
                            <p className="text-red-700 dark:text-red-300 text-sm">
                                {job.error ||
                                    "An error occurred during resume generation"}
                            </p>
                        </div>
                    )}

                    {/* Live Log - Show for all active jobs */}
                    {events.length > 0 && (
                        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                            <LiveLog events={events} />
                        </div>
                    )}
                </div>

                {/* Sidebar */}
                <div className="space-y-6">
                    {/* FIX #8: Pipeline Stages - Show for all non-failed jobs */}
                    {(isProcessing ||
                        job.status === "queued" ||
                        isCompleted) && (
                        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                                Pipeline Stages
                            </h2>
                            <StageTimeline
                                currentStage={
                                    currentStatus?.stage ||
                                    (isCompleted ? "completed" : "queued")
                                }
                                status={job.status}
                            />
                        </div>
                    )}

                    {/* Job Details Card */}
                    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                            Job Details
                        </h2>
                        <div className="space-y-3 text-sm">
                            <div>
                                <p className="text-gray-500 dark:text-gray-400">
                                    Job ID
                                </p>
                                <p className="text-gray-900 dark:text-white font-mono text-xs">
                                    {job.id || job.job_id}
                                </p>
                            </div>
                            <div>
                                <p className="text-gray-500 dark:text-gray-400">
                                    Template
                                </p>
                                <p className="text-gray-900 dark:text-white">
                                    {job.template}
                                </p>
                            </div>
                            {job.output_backend && (
                                <div>
                                    <p className="text-gray-500 dark:text-gray-400">
                                        Output Backend
                                    </p>
                                    <p className="text-gray-900 dark:text-white capitalize">
                                        {job.output_backend}
                                    </p>
                                </div>
                            )}
                            {job.priority !== undefined && (
                                <div>
                                    <p className="text-gray-500 dark:text-gray-400">
                                        Priority
                                    </p>
                                    <p className="text-gray-900 dark:text-white">
                                        {job.priority}
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* Delete Confirmation Modal */}
            {showDeleteConfirm && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                            Delete Job?
                        </h3>
                        <p className="text-gray-600 dark:text-gray-400 mb-6">
                            Are you sure you want to delete this job? This
                            action cannot be undone.
                        </p>
                        <div className="flex items-center gap-3 justify-end">
                            <button
                                onClick={() => setShowDeleteConfirm(false)}
                                disabled={deleting}
                                className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleDelete}
                                disabled={deleting}
                                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {deleting ? "Deleting..." : "Delete"}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Resubmit Modal */}
            {showResubmitModal && (
                <ResubmitModal
                    job={job}
                    onClose={() => setShowResubmitModal(false)}
                    onSubmit={handleResubmit}
                    isSubmitting={resubmitting}
                />
            )}
        </div>
    );
}

import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { apiService, createJobStatusSSE } from "../services/api";
import { useApp } from "../contexts/AppContext";
import ProgressBar from "../components/ProgressBar";
import StageTimeline from "../components/StageTimeline";
import LiveLog from "../components/LiveLog";
import ArtifactList from "../components/ArtifactList";
import ResubmitModal from "../components/ResubmitModal";
import { STATUS_COLORS } from "../utils/constants";
import { formatDate, getStatusIcon } from "../utils/helpers";

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

    // Viewer State
    const [viewingFile, setViewingFile] = useState(null); // { name, url, type }
    const [loadingFile, setLoadingFile] = useState(false);

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
            status: payload.type, // Use payload.type
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
                type: payload.type, // Use payload.type
            },
        ]);

        // FIX #3: Update job status in state based on message type
        if (payload.type === "JOB_COMPLETED") {
            setJob((prev) => ({ ...prev, status: "completed" }));
            // Fetch files when job completes
            fetchJobFiles();
        } else if (payload.type === "JOB_FAILED") {
            setJob((prev) => ({
                ...prev,
                status: "failed",
                error: payload.error || payload.message,
            }));
        } else if (payload.type === "JOB_STARTED") {
            setJob((prev) => ({ ...prev, status: "processing" }));
        } else if (payload.type === "JOB_PROGRESS") {
            // Keep status as processing during progress updates
            setJob((prev) => ({ ...prev, status: "processing" }));
        }
    };

    // Handle job resubmission with proper error handling
    const handleResubmit = async (config) => {
        try {
            setResubmitting(true);
            const response = await apiService.resubmitJob(jobId, config);

            // Hide modal
            setShowResubmitModal(false);

            // KEY CHANGE: Navigate to the new job ID.
            // This triggers useEffect -> fetchJobDetails -> resets state/logs automatically.
            const newJobId = response.data.job_id || response.data.id;
            navigate(`/jobs/${newJobId}`);
        } catch (error) {
            console.error("Failed to resubmit job:", error);
            // ... error handling ...
        } finally {
            setResubmitting(false);
        }
    };

    // Handle job deletion with proper error handling
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

    // Handle File Viewing
    const handleViewFile = async (file) => {
        try {
            setLoadingFile(true);

            // Determine MIME type
            let mimeType = "text/plain";
            if (file.name.endsWith(".pdf")) mimeType = "application/pdf";
            else if (file.name.endsWith(".json")) mimeType = "application/json";
            else if (file.name.endsWith(".html")) mimeType = "text/html";

            // Fetch blob from API
            const response = await apiService.downloadFile(jobId, file.name);

            // Create object URL
            const blob = new Blob([response.data], { type: mimeType });
            const url = window.URL.createObjectURL(blob);

            setViewingFile({
                name: file.name,
                url: url,
                type: mimeType,
            });
        } catch (error) {
            console.error("Failed to load file for viewing:", error);
            alert("Could not load file preview.");
        } finally {
            setLoadingFile(false);
        }
    };

    const closeViewer = () => {
        if (viewingFile?.url) {
            window.URL.revokeObjectURL(viewingFile.url);
        }
        setViewingFile(null);
    };

    // Initial fetch on mount or when jobId changes
    useEffect(() => {
        // Reset state for the new job ID
        setEvents([]);
        setCurrentStatus(null);
        setFiles([]); // Clear old files immediately

        // Fetch data for the new job
        fetchJobDetails();
        fetchJobFiles();

        // Optional: Close any open file viewers from the previous job
        setViewingFile(null);
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

    // Cleanup blob URL on unmount
    useEffect(() => {
        return () => {
            if (viewingFile?.url) {
                window.URL.revokeObjectURL(viewingFile.url);
            }
        };
    }, [viewingFile]);

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
    const formatTime = (dateStr) => {
        return new Date(dateStr).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
        });
    };

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 relative">
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
                    {/* Progress Card */}
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

                    {/* Results Card */}
                    {isCompleted && files.length > 0 && (
                        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                                Results
                            </h2>
                            <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                                Generated Files
                            </h3>
                            {/* Pass handleViewFile to enable in-page viewing */}
                            <ArtifactList
                                jobId={jobId}
                                files={files}
                                onFileSelect={handleViewFile}
                            />
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

                    {/* Live Log */}
                    {events.length > 0 && (
                        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                            <LiveLog events={events} />
                        </div>
                    )}
                </div>

                {/* Sidebar */}
                <div className="space-y-6">
                    {/* Job History / Versions Card */}
                    {job && job.history && job.history.length > 0 && (
                        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
                            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                                Version History
                            </h2>
                            <div className="space-y-2 max-h-60 overflow-y-auto">
                                {job.history.map((ver) => {
                                    const isCurrent = ver.id === job.id;
                                    return (
                                        <button
                                            key={ver.id}
                                            onClick={() =>
                                                navigate(`/jobs/${ver.id}`)
                                            }
                                            className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors flex items-center justify-between group ${
                                                isCurrent
                                                    ? "bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800"
                                                    : "hover:bg-gray-50 dark:hover:bg-gray-700 border border-transparent"
                                            }`}
                                        >
                                            <div className="flex flex-col">
                                                <span
                                                    className={`font-medium ${isCurrent ? "text-primary-700 dark:text-primary-300" : "text-gray-700 dark:text-gray-300"}`}
                                                >
                                                    {ver.template ||
                                                        "Standard Resume"}
                                                </span>
                                                <span className="text-xs text-gray-500">
                                                    {new Date(
                                                        ver.created_at,
                                                    ).toLocaleDateString()}{" "}
                                                    at{" "}
                                                    {formatTime(ver.created_at)}
                                                </span>
                                            </div>

                                            {/* Status Badge Mini */}
                                            <div className="flex items-center gap-2">
                                                <span
                                                    className={`w-2 h-2 rounded-full ${
                                                        ver.status ===
                                                        "completed"
                                                            ? "bg-green-500"
                                                            : ver.status ===
                                                                "failed"
                                                              ? "bg-red-500"
                                                              : "bg-blue-500 animate-pulse"
                                                    }`}
                                                />
                                            </div>
                                        </button>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    {/* Score Card */}
                    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                            Critique Score
                        </h2>
                        {job.final_score !== null &&
                        job.final_score !== undefined ? (
                            <>
                                <div className="flex items-baseline gap-2">
                                    <span
                                        className={`text-4xl font-bold ${
                                            job.final_score >= 8
                                                ? "text-green-600 dark:text-green-400"
                                                : job.final_score >= 6
                                                  ? "text-yellow-600 dark:text-yellow-400"
                                                  : "text-red-600 dark:text-red-400"
                                        }`}
                                    >
                                        {Number(job.final_score).toFixed(1)}
                                    </span>
                                    <span className="text-gray-500 dark:text-gray-400 font-medium">
                                        / 10
                                    </span>
                                </div>
                                <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                                    Generated by AI Critique
                                </p>
                            </>
                        ) : (
                            <div className="flex flex-col gap-2">
                                <span className="text-2xl font-bold text-gray-300 dark:text-gray-600">
                                    -- / 10
                                </span>
                                <p className="text-sm text-gray-500 dark:text-gray-400">
                                    {job.status === "completed"
                                        ? "No score available"
                                        : "Pending generation..."}
                                </p>
                            </div>
                        )}
                    </div>

                    {/* Pipeline Stages */}
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

            {/* Document Viewer Modal */}
            {(viewingFile || loadingFile) && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75 backdrop-blur-sm p-4 sm:p-6">
                    <div className="bg-white dark:bg-gray-900 rounded-xl shadow-2xl w-full max-w-5xl h-[90vh] flex flex-col overflow-hidden">
                        {/* Modal Header */}
                        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                            <h3 className="text-lg font-semibold text-gray-900 dark:text-white truncate">
                                {loadingFile ? "Loading..." : viewingFile?.name}
                            </h3>
                            <button
                                onClick={closeViewer}
                                className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
                            >
                                <span className="text-2xl">×</span>
                            </button>
                        </div>

                        {/* Modal Content */}
                        <div className="flex-1 bg-gray-100 dark:bg-gray-800 relative">
                            {loadingFile ? (
                                <div className="absolute inset-0 flex items-center justify-center">
                                    <div className="flex flex-col items-center gap-3">
                                        <div className="w-10 h-10 border-4 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
                                        <p className="text-gray-500 dark:text-gray-400">
                                            Fetching document...
                                        </p>
                                    </div>
                                </div>
                            ) : viewingFile?.type === "application/pdf" ? (
                                <iframe
                                    src={viewingFile.url}
                                    className="w-full h-full border-0"
                                    title="PDF Viewer"
                                />
                            ) : (
                                <iframe
                                    src={viewingFile.url}
                                    className="w-full h-full border-0 bg-white"
                                    title="Document Viewer"
                                />
                            )}
                        </div>
                    </div>
                </div>
            )}

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

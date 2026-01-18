// ... keep imports ...
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
import {
    formatDate,
    formatDuration,
    getStatusIcon,
    estimateTimeRemaining,
} from "../utils/helpers";

export default function JobDetailPage() {
    // ... keep existing state hooks ...
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

    // ... keep useEffects ...
    useEffect(() => {
        setEvents([]);
        setCurrentStatus(null);
        setLoading(true);
        fetchJobDetails();
        fetchJobFiles();
    }, [jobId]);

    useEffect(() => {
        let cleanup;

        if (job && (job.status === "processing" || job.status === "queued")) {
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
    }, [job?.status, jobId]);

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

    const fetchJobFiles = async () => {
        try {
            const response = await apiService.listJobFiles(jobId);
            // FIXED: API returns direct array, not { files: [] }
            const fileList = Array.isArray(response.data)
                ? response.data
                : response.data.files || [];
            setFiles(fileList);
        } catch (error) {
            console.error("Failed to fetch job files:", error);
            setFiles([]);
        }
    };

    // ... keep rest of the component exactly as is ...
    // (Copy handleStatusUpdate, handleResubmit, handleDelete, render logic from your original file)
    // Be sure to include the return statement!

    // For brevity, I am not repeating the unmodified render code.
    // Just replace the fetchJobFiles function and ensure imports are there.

    const handleStatusUpdate = (data) => {
        setCurrentStatus(data);
        setEvents((prev) => [
            ...prev,
            {
                ...data,
                timestamp: new Date().toISOString(),
            },
        ]);

        if (data.status === "job_completed" || data.status === "job_failed") {
            fetchJobDetails();
            fetchJobFiles();
        }
    };

    const handleResubmit = async (config) => {
        try {
            const response = await apiService.resubmitJob(jobId, config);
            setShowResubmitModal(false);
            setEvents([]);
            setCurrentStatus(null);
            navigate(`/jobs/${response.data.job_id}`);
        } catch (error) {
            console.error("Failed to resubmit job:", error);
            alert("Failed to resubmit job. Please try again.");
        }
    };

    const handleDelete = async () => {
        try {
            await apiService.deleteJob(jobId);
            dispatch({ type: actionTypes.REMOVE_JOB, payload: jobId });
            navigate("/");
        } catch (error) {
            console.error("Failed to delete job:", error);
            alert("Failed to delete job. Please try again.");
        }
    };

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
                        className="px-6 py-3 bg-primary-600 text-white rounded-lg"
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
                                className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
                            >
                                Regenerate
                            </button>
                        )}
                        <button
                            onClick={() => setShowDeleteConfirm(true)}
                            className="px-4 py-2 border border-red-600 text-red-600 dark:border-red-400 dark:text-red-400 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                        >
                            Delete
                        </button>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Main Content */}
                <div className="lg:col-span-2 space-y-6">
                    {/* Progress Card */}
                    {isProcessing && (
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
                    {isCompleted && (
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

                    {/* Error Card */}
                    {isFailed && (
                        <div className="bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800 p-6">
                            <p className="text-red-700 dark:text-red-300 text-sm">
                                {job.error || "Generation Failed"}
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
                    {isProcessing && (
                        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                                Pipeline Stages
                            </h2>
                            <StageTimeline
                                currentStage={currentStatus?.stage || "queued"}
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
                            <p className="text-gray-600 dark:text-gray-400">
                                ID: {job.id || job.job_id}
                            </p>
                            <p className="text-gray-600 dark:text-gray-400">
                                Template: {job.template}
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Modals */}
            {showDeleteConfirm && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4">
                        <h3 className="text-lg font-semibold mb-4">
                            Delete Job?
                        </h3>
                        <div className="flex gap-3">
                            <button
                                onClick={handleDelete}
                                className="px-4 py-2 bg-red-600 text-white rounded"
                            >
                                Delete
                            </button>
                            <button
                                onClick={() => setShowDeleteConfirm(false)}
                                className="px-4 py-2 border rounded"
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}
            {showResubmitModal && (
                <ResubmitModal
                    job={job}
                    onSubmit={handleResubmit}
                    onClose={() => setShowResubmitModal(false)}
                />
            )}
        </div>
    );
}

import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { apiService, createJobStatusSSE } from "../services/api";
import { useApp } from "../contexts/AppContext";
import ProgressBar from "../components/ProgressBar";
import StageTimeline from "../components/StageTimeline";
import LiveLog from "../components/LiveLog";
import ArtifactList from "../components/ArtifactList";
import ResubmitModal from "../components/ResubmitModal";
import CritiqueCard from "../components/CritiqueCard";
import DomainMatchCard from "../components/DomainMatchCard";
import CritiqueFeedbackCard from "../components/CritiqueFeedbackCard";
import LatexEditor from "../components/latex/LatexEditor";
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

    // Active tab state
    const [activeTab, setActiveTab] = useState("overview");

    // Viewer State
    const [viewingFile, setViewingFile] = useState(null);
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
            const fileList = Array.isArray(response.data)
                ? response.data
                : response.data.files || [];
            setFiles(fileList);
        } catch (error) {
            console.error("Failed to fetch job files:", error);
            setFiles([]);
        }
    };

    // Handle SSE status updates
    const handleStatusUpdate = (payload) => {
        console.log("SSE Update received:", payload);

        const statusUpdate = {
            stage: payload.stage || currentStatus?.stage || "queued",
            progress_percent: payload.progress_percent || payload.percent || 0,
            message: payload.message || "",
            status: payload.type,
            job_id: payload.job_id,
        };

        setCurrentStatus(statusUpdate);

        // Add event to log
        setEvents((prev) => [
            ...prev,
            {
                timestamp: new Date().toISOString(),
                stage: statusUpdate.stage,
                message: statusUpdate.message,
                progress: statusUpdate.progress_percent,
                type: payload.type,
            },
        ]);

        // Refetch when job completes or fails
        if (payload.type === "JOB_COMPLETED" || payload.type === "JOB_FAILED") {
            fetchJobDetails();
            fetchJobFiles();
        }

        // Update job status
        if (payload.type === "JOB_COMPLETED") {
            setJob((prev) => ({ ...prev, status: "completed" }));
        } else if (payload.type === "JOB_FAILED") {
            setJob((prev) => ({
                ...prev,
                status: "failed",
                error: payload.error || payload.message,
            }));
        } else if (payload.type === "JOB_STARTED") {
            setJob((prev) => ({ ...prev, status: "processing" }));
        } else if (payload.type === "JOB_PROGRESS") {
            setJob((prev) => ({ ...prev, status: "processing" }));
        }
    };

    // Handle job resubmission
    const handleResubmit = async (config) => {
        try {
            setResubmitting(true);
            const response = await apiService.resubmitJob(jobId, config);
            setShowResubmitModal(false);
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

    // Handle job deletion
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

    // Handle file viewing
    const handleFileView = async (file) => {
        try {
            setLoadingFile(true);

            let mimeType = "text/plain";
            if (file.name.endsWith(".pdf")) mimeType = "application/pdf";
            else if (file.name.endsWith(".json")) mimeType = "application/json";
            else if (file.name.endsWith(".html")) mimeType = "text/html";

            const response = await apiService.downloadFile(jobId, file.name);
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

    // Initial fetch on mount
    useEffect(() => {
        setEvents([]);
        setCurrentStatus(null);
        setFiles([]);
        setViewingFile(null);
        setActiveTab("overview"); // Reset to overview tab

        fetchJobDetails();
        fetchJobFiles();
    }, [jobId]);

    // Setup SSE connection
    useEffect(() => {
        let cleanup;

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

    // Computed values
    const isProcessing = job?.status === "processing";
    const isCompleted = job?.status === "completed";
    const isFailed = job?.status === "failed";
    const isQueued = job?.status === "queued";

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
        );
    }

    if (!job) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <div className="text-center">
                    <p className="text-slate-600 dark:text-slate-400 mb-4">
                        Job not found
                    </p>
                    <button
                        onClick={() => navigate("/")}
                        className="text-primary-600 hover:text-primary-700"
                    >
                        Return to Dashboard
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
            <div className="space-y-4 sm:space-y-6">
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                    <div className="flex-1">
                        <button
                            onClick={() => navigate("/")}
                            className="text-sm text-primary-600 hover:text-primary-700 mb-2 flex items-center gap-1"
                        >
                            ← Back to Dashboard
                        </button>
                        <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white break-words">
                            {job.company} - {job.job_title}
                        </h1>
                        <p className="text-sm sm:text-base text-slate-500 dark:text-slate-400 mt-1">
                            Created {formatDate(job.created_at)}
                        </p>
                    </div>

                    <div className="flex items-center gap-2 flex-shrink-0">
                        <span
                            className={`px-3 py-1 rounded-full text-xs sm:text-sm font-medium whitespace-nowrap ${STATUS_COLORS[job.status] || STATUS_COLORS.queued}`}
                        >
                            {getStatusIcon(job.status)} {job.status}
                        </span>
                    </div>
                </div>

                {/* Tab Navigation */}
                <div className="bg-white dark:bg-background-surface rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden">
                    {/* Tab Navigation - Horizontal scrollable on mobile */}
                    <div className="border-b border-slate-200 dark:border-slate-700 overflow-x-auto scrollbar-thin">
                        <div className="flex min-w-max sm:min-w-0">
                            <button
                                onClick={() => setActiveTab("overview")}
                                className={`px-4 sm:px-6 py-3 font-medium text-xs sm:text-sm border-b-2 transition-colors whitespace-nowrap ${
                                    activeTab === "overview"
                                        ? "border-primary-600 text-primary-600 bg-primary-50 dark:bg-primary-900/20"
                                        : "border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-50 dark:hover:bg-slate-800/50"
                                }`}
                            >
                                <span className="hidden sm:inline">
                                    📊 Overview
                                </span>
                                <span className="sm:hidden">📊</span>
                            </button>

                            <button
                                onClick={() => setActiveTab("artifacts")}
                                className={`px-4 sm:px-6 py-3 font-medium text-xs sm:text-sm border-b-2 transition-colors whitespace-nowrap ${
                                    activeTab === "artifacts"
                                        ? "border-primary-600 text-primary-600 bg-primary-50 dark:bg-primary-900/20"
                                        : "border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-50 dark:hover:bg-slate-800/50"
                                }`}
                            >
                                <span className="hidden sm:inline">
                                    📁 Files ({files.length})
                                </span>
                                <span className="sm:hidden">
                                    📁 {files.length}
                                </span>
                            </button>

                            <button
                                onClick={() => setActiveTab("latex")}
                                className={`px-4 sm:px-6 py-3 font-medium text-xs sm:text-sm border-b-2 transition-colors whitespace-nowrap ${
                                    activeTab === "latex"
                                        ? "border-primary-600 text-primary-600 bg-primary-50 dark:bg-primary-900/20"
                                        : "border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-50 dark:hover:bg-slate-800/50"
                                }`}
                            >
                                <span className="hidden sm:inline">
                                    📝 LaTeX Editor
                                </span>
                                <span className="sm:hidden">📝</span>
                            </button>

                            <button
                                onClick={() => setActiveTab("logs")}
                                className={`px-4 sm:px-6 py-3 font-medium text-xs sm:text-sm border-b-2 transition-colors whitespace-nowrap ${
                                    activeTab === "logs"
                                        ? "border-primary-600 text-primary-600 bg-primary-50 dark:bg-primary-900/20"
                                        : "border-transparent text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-50 dark:hover:bg-slate-800/50"
                                }`}
                            >
                                <span className="hidden sm:inline">
                                    📋 Logs ({events.length})
                                </span>
                                <span className="sm:hidden">
                                    📋 {events.length}
                                </span>
                            </button>
                        </div>
                    </div>

                    {/* Tab Content */}
                    <div className={activeTab === "latex" ? "" : "p-4 sm:p-6"}>
                        {/* Overview Tab */}
                        {activeTab === "overview" && (
                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
                                {/* Left Column - Main Info */}
                                <div className="lg:col-span-2 space-y-6">
                                    {/* Progress Bar */}
                                    {(isProcessing || isQueued) &&
                                        currentStatus && (
                                            <div className="bg-white dark:bg-background-surface rounded-lg border border-slate-200 dark:border-slate-700 p-6">
                                                <ProgressBar
                                                    stage={currentStatus.stage}
                                                    progress={
                                                        currentStatus.progress_percent
                                                    }
                                                    message={
                                                        currentStatus.message
                                                    }
                                                    status={job.status}
                                                />
                                            </div>
                                        )}

                                    {/* Pipeline Stages */}
                                    {(isProcessing ||
                                        isQueued ||
                                        isCompleted) && (
                                        <div className="bg-white dark:bg-background-surface rounded-lg border border-slate-200 dark:border-slate-700 p-6">
                                            <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
                                                Pipeline Stages
                                            </h2>
                                            <StageTimeline
                                                currentStage={
                                                    currentStatus?.stage ||
                                                    (isCompleted
                                                        ? "completed"
                                                        : "queued")
                                                }
                                                status={job.status}
                                            />
                                        </div>
                                    )}

                                    {/* Actions */}
                                    <div className="bg-white dark:bg-background-surface rounded-lg border border-slate-200 dark:border-slate-700 p-6">
                                        <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
                                            Actions
                                        </h2>
                                        <div className="flex flex-wrap gap-2">
                                            <button
                                                onClick={() =>
                                                    setShowResubmitModal(true)
                                                }
                                                disabled={isProcessing}
                                                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
                                            >
                                                🔄 Regenerate
                                            </button>

                                            <button
                                                onClick={() =>
                                                    setShowDeleteConfirm(true)
                                                }
                                                disabled={deleting}
                                                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
                                            >
                                                {deleting
                                                    ? "Deleting..."
                                                    : "🗑️ Delete Job"}
                                            </button>
                                        </div>
                                    </div>
                                </div>

                                {/* Right Column - Sidebar */}
                                <div className="space-y-6">
                                    {/* Job Details Card */}
                                    <div className="bg-white dark:bg-background-surface rounded-lg border border-slate-200 dark:border-slate-700 p-6">
                                        <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
                                            Job Details
                                        </h2>
                                        <div className="space-y-3 text-sm">
                                            <div>
                                                <p className="text-slate-500 dark:text-slate-400">
                                                    Job ID
                                                </p>
                                                <p className="text-slate-900 dark:text-white font-mono text-xs break-all">
                                                    {job.id || job.job_id}
                                                </p>
                                            </div>
                                            <div>
                                                <p className="text-slate-500 dark:text-slate-400">
                                                    Template
                                                </p>
                                                <p className="text-slate-900 dark:text-white">
                                                    {job.template}
                                                </p>
                                            </div>
                                            {job.output_backend && (
                                                <div>
                                                    <p className="text-slate-500 dark:text-slate-400">
                                                        Output Backend
                                                    </p>
                                                    <p className="text-slate-900 dark:text-white capitalize">
                                                        {job.output_backend}
                                                    </p>
                                                </div>
                                            )}
                                            {job.priority !== undefined && (
                                                <div>
                                                    <p className="text-slate-500 dark:text-slate-400">
                                                        Priority
                                                    </p>
                                                    <p className="text-slate-900 dark:text-white">
                                                        {job.priority}
                                                    </p>
                                                </div>
                                            )}
                                        </div>
                                    </div>

                                    {/* Critique Score */}
                                    <CritiqueCard
                                        critique={job.critique}
                                        status={job.status}
                                        fallbackScore={job.final_score}
                                    />

                                    {/* Domain Match */}
                                    {job.critique && job.jd_requirements && (
                                        <DomainMatchCard
                                            critique={job.critique}
                                            jdRequirements={job.jd_requirements}
                                        />
                                    )}

                                    {/* Critique Feedback */}
                                    {job.critique && (
                                        <CritiqueFeedbackCard
                                            critique={job.critique}
                                        />
                                    )}
                                </div>
                            </div>
                        )}

                        {/* Artifacts Tab */}
                        {activeTab === "artifacts" && (
                            <div>
                                <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
                                    Generated Files
                                </h2>
                                <ArtifactList
                                    files={files}
                                    onFileSelect={handleFileView}
                                />
                            </div>
                        )}

                        {/* LaTeX Editor Tab - Full height on mobile */}
                        {activeTab === "latex" && (
                            <div className="h-[calc(100vh-12rem)] sm:h-[calc(100vh-16rem)]">
                                <LatexEditor jobId={jobId} />
                            </div>
                        )}

                        {/* Logs Tab */}
                        {activeTab === "logs" && (
                            <div>
                                <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
                                    Activity Log
                                </h2>
                                <LiveLog events={events} />
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Modals */}
            {showResubmitModal && (
                <ResubmitModal
                    job={job}
                    onClose={() => setShowResubmitModal(false)}
                    onSubmit={handleResubmit}
                    isSubmitting={resubmitting}
                />
            )}

            {showDeleteConfirm && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white dark:bg-background-surface rounded-lg max-w-md w-full p-4 sm:p-6 mx-4">
                        <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
                            Delete Job?
                        </h3>
                        <p className="text-sm sm:text-base text-slate-600 dark:text-slate-400 mb-6">
                            This will permanently delete this job and all
                            associated files. This action cannot be undone.
                        </p>
                        <div className="flex flex-col sm:flex-row gap-3 sm:justify-end">
                            <button
                                onClick={() => setShowDeleteConfirm(false)}
                                disabled={deleting}
                                className="w-full sm:w-auto px-4 py-2 bg-slate-200 dark:bg-slate-700 text-slate-900 dark:text-white rounded-lg hover:bg-slate-300 dark:hover:bg-slate-600 min-h-[44px] touch-manipulation"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleDelete}
                                disabled={deleting}
                                className="w-full sm:w-auto px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 min-h-[44px] touch-manipulation"
                            >
                                {deleting ? "Deleting..." : "Delete Job"}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* File Viewer Modal */}
            {viewingFile && (
                <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
                    <div className="bg-white dark:bg-background-surface rounded-lg max-w-6xl w-full h-[90vh] flex flex-col">
                        <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-700">
                            <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                                {viewingFile.name}
                            </h3>
                            <button
                                onClick={closeViewer}
                                className="text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
                            >
                                ✕
                            </button>
                        </div>
                        <div className="flex-1 overflow-auto p-4">
                            {viewingFile.type === "application/pdf" && (
                                <iframe
                                    src={viewingFile.url}
                                    className="w-full h-full"
                                    title={viewingFile.name}
                                />
                            )}
                            {viewingFile.type === "application/json" && (
                                <pre className="text-sm bg-slate-100 dark:bg-slate-800 p-4 rounded overflow-auto">
                                    {JSON.stringify(
                                        JSON.parse(
                                            new TextDecoder().decode(
                                                viewingFile.url,
                                            ),
                                        ),
                                        null,
                                        2,
                                    )}
                                </pre>
                            )}
                            {viewingFile.type === "text/plain" && (
                                <pre className="text-sm bg-slate-100 dark:bg-slate-800 p-4 rounded overflow-auto whitespace-pre-wrap">
                                    {viewingFile.url}
                                </pre>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

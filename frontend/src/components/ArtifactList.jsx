import { useState } from "react";
import { apiService } from "../services/api";
import { FILE_ICONS } from "../utils/constants";
import { formatFileSize } from "../utils/helpers";

export default function ArtifactList({ jobId, files = [], onFileSelect }) {
    const [downloading, setDownloading] = useState(null);

    const handleDownload = async (filename) => {
        try {
            setDownloading(filename);
            const response = await apiService.downloadFile(jobId, filename);

            // Create download link
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement("a");
            link.href = url;
            link.setAttribute("download", filename);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error("Download failed:", error);
            alert("Failed to download file. Please try again.");
        } finally {
            setDownloading(null);
        }
    };

    const getFileIcon = (filename) => {
        const ext = filename.split(".").pop().toLowerCase();
        return FILE_ICONS[ext] || "📎";
    };

    const isPreviewable = (filename) => {
        return (
            filename.endsWith(".json") ||
            filename.endsWith(".pdf") ||
            filename.endsWith(".txt") ||
            filename.endsWith(".md") ||
            filename.endsWith(".html")
        );
    };

    const getPreviewUrl = (filename) => {
        // Construct URL manually to match Nginx proxy
        return `/api/jobs/${jobId}/files/${filename}`;
    };

    if (!files || files.length === 0) {
        return (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                No files available yet
            </div>
        );
    }

    return (
        <div className="space-y-3">
            {files.map((file) => {
                const fileType = file.name.split(".").pop().toLowerCase();

                return (
                    <div
                        key={file.name}
                        className="flex items-center justify-between p-4 bg-gray-50 dark:bg-background-surface rounded-lg border border-gray-200 dark:border-gray-700"
                    >
                        <div className="flex items-center gap-3 flex-1 min-w-0">
                            {/* FIXED: Infer icon from filename since API doesn't return type */}
                            <span className="text-2xl flex-shrink-0">
                                {getFileIcon(file.name)}
                            </span>
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                                    {file.name}
                                </p>
                                <p className="text-xs text-gray-500 dark:text-gray-400">
                                    {formatFileSize(file.size)}
                                </p>
                            </div>
                        </div>

                        <div className="flex items-center gap-2 ml-3">
                            {/* FIXED: Check extension for preview and construct URL manually */}
                            {isPreviewable(file.name) && (
                                <button
                                    onClick={() => {
                                        if (onFileSelect) {
                                            onFileSelect(file);
                                        } else {
                                            window.open(
                                                getPreviewUrl(file.name),
                                                "_blank",
                                            );
                                        }
                                    }}
                                    className="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
                                >
                                    View
                                </button>
                            )}
                            <button
                                onClick={() => handleDownload(file.name)}
                                disabled={downloading === file.name}
                                className="px-3 py-1.5 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 dark:bg-primary-500 dark:hover:bg-primary-600 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                            >
                                {downloading === file.name ? (
                                    <>
                                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                                        <span>Downloading...</span>
                                    </>
                                ) : (
                                    <>
                                        <span>↓</span>
                                        <span>Download</span>
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

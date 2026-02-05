import { useState, useEffect, useRef } from "react";
import {
    Panel,
    Group as PanelGroup,
    Separator as PanelResizeHandle,
} from "react-resizable-panels";
import { latexApi } from "../../services/latexApi";
import { createLatexCompilationSSE } from "../../services/latexSSE";
import { showToast } from "../../utils/toast";
import CodeEditor from "./CodeEditor";
import PdfViewer from "./PdfViewer";
import CompilationLog from "./CompilationLog";
import EditorToolbar from "./EditorToolbar";
import VersionHistory from "./VersionHistory";
import MobileActionSheet from "./MobileActionSheet";
import LayoutToggle from "./LayoutToggle";
import KeyboardShortcutsModal from "./KeyboardShortcutsModal";

export default function LatexEditor({ jobId }) {
    const [content, setContent] = useState("");
    const [originalContent, setOriginalContent] = useState("");
    const [isDirty, setIsDirty] = useState(false);
    const [isSaving, setSaving] = useState(false);
    const [isCompiling, setCompiling] = useState(false);
    const [lastSaved, setLastSaved] = useState(null);
    const [pdfUrl, setPdfUrl] = useState(null);
    const [compilationResult, setCompilationResult] = useState(null);
    const [error, setError] = useState(null);
    const [backups, setBackups] = useState([]);

    // Layout and UI state
    const [layout, setLayout] = useState("split"); // split, editor, preview
    const [mobileView, setMobileView] = useState("editor"); // editor, preview
    const [logCollapsed, setLogCollapsed] = useState(false);
    const [showActionSheet, setShowActionSheet] = useState(false);
    const [showShortcuts, setShowShortcuts] = useState(false);

    const autoSaveTimer = useRef(null);
    const sseCleanup = useRef(null);
    const compilationToastId = useRef(null);

    // Detect mobile viewport
    const [isMobile, setIsMobile] = useState(false);

    useEffect(() => {
        const checkMobile = () => {
            setIsMobile(window.innerWidth < 768);
        };
        checkMobile();
        window.addEventListener("resize", checkMobile);
        return () => window.removeEventListener("resize", checkMobile);
    }, []);

    // Load initial content
    useEffect(() => {
        loadSource();
        loadBackups();
        // Set initial PDF URL if job is completed
        setPdfUrl(`/api/jobs/${jobId}/files/resume.pdf?t=${Date.now()}`);
    }, [jobId]);

    // Auto-save every 30 seconds if dirty
    useEffect(() => {
        if (isDirty && !isSaving) {
            autoSaveTimer.current = setTimeout(() => {
                handleSave(false); // Silent save
            }, 30000);
        }

        return () => {
            if (autoSaveTimer.current) {
                clearTimeout(autoSaveTimer.current);
            }
        };
    }, [isDirty, content]);

    // Track dirty state
    useEffect(() => {
        setIsDirty(content !== originalContent);
    }, [content, originalContent]);

    // Keyboard shortcuts
    useEffect(() => {
        const handleKeyDown = (e) => {
            // Ctrl/Cmd + S: Save
            if ((e.ctrlKey || e.metaKey) && e.key === "s") {
                e.preventDefault();
                handleSave();
            }
            // Ctrl/Cmd + Enter: Compile
            if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                e.preventDefault();
                handleCompile();
            }
        };

        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [content]);

    // Cleanup SSE on unmount
    useEffect(() => {
        return () => {
            if (sseCleanup.current) {
                sseCleanup.current();
            }
        };
    }, []);

    const loadSource = async () => {
        try {
            const data = await latexApi.getSource(jobId);
            setContent(data.content);
            setOriginalContent(data.content);
            setError(null);
        } catch (err) {
            if (err.response?.status === 404) {
                setError("LaTeX source not found. Generate a resume first.");
                showToast.error("LaTeX source not found");
            } else {
                setError("Failed to load LaTeX source");
                showToast.error("Failed to load LaTeX source");
            }
            console.error("Load error:", err);
        }
    };

    const loadBackups = async () => {
        try {
            const data = await latexApi.listBackups(jobId);
            setBackups(data);
        } catch (err) {
            console.error("Failed to load backups:", err);
        }
    };

    const handleSave = async (showNotification = true) => {
        if (!isDirty) return;

        setSaving(true);
        try {
            await latexApi.saveSource(jobId, content, true);
            setOriginalContent(content);
            setLastSaved(new Date());
            setIsDirty(false);

            if (showNotification) {
                showToast.latex.saved();
            }

            loadBackups(); // Refresh backup list
        } catch (err) {
            setError("Failed to save");
            showToast.error("Failed to save LaTeX source");
            console.error("Save error:", err);
        } finally {
            setSaving(false);
        }
    };

    const handleCompile = async () => {
        setCompiling(true);
        setCompilationResult(null);
        setError(null);
        setLogCollapsed(false); // Expand log when compiling

        try {
            // Save first if dirty
            if (isDirty) {
                await handleSave(false);
            }

            // Show loading toast
            compilationToastId.current = showToast.latex.compiling();

            // Request compilation via RabbitMQ
            await latexApi.compile(jobId, content);

            // Set up SSE listener for real-time updates
            setupCompilationSSE();
        } catch (err) {
            setError("Compilation request failed");
            showToast.latex.compileFailed(err.message);
            setCompiling(false);

            // Dismiss loading toast
            if (compilationToastId.current) {
                showToast.dismiss(compilationToastId.current);
            }
        }
    };

    const setupCompilationSSE = () => {
        // Clean up existing SSE connection
        if (sseCleanup.current) {
            sseCleanup.current();
        }

        // Create new SSE connection
        sseCleanup.current = createLatexCompilationSSE(jobId, {
            onConnect: () => {
                console.log("Listening for LaTeX compilation updates...");
            },

            onProgress: (progress) => {
                console.log("Compilation progress:", progress);
                setCompilationResult({
                    status: "compiling",
                    message: progress.message,
                    stage: progress.stage,
                    percent: progress.percent,
                });
            },

            onComplete: (result) => {
                console.log("Compilation completed:", result);

                // Dismiss loading toast
                if (compilationToastId.current) {
                    showToast.dismiss(compilationToastId.current);
                }

                // Show success toast
                showToast.latex.compiled();

                // Update PDF URL with cache buster
                setPdfUrl(
                    `/api/jobs/${jobId}/files/resume.pdf?t=${Date.now()}`,
                );

                // Update compilation result
                setCompilationResult({
                    status: "success",
                    message: "Compilation completed successfully",
                    warnings: result.warnings || [],
                });

                setCompiling(false);

                // On mobile, switch to preview after successful compilation
                if (isMobile) {
                    setMobileView("preview");
                }

                // Clean up SSE connection
                if (sseCleanup.current) {
                    sseCleanup.current();
                    sseCleanup.current = null;
                }
            },

            onError: (result) => {
                console.error("Compilation failed:", result);

                // Dismiss loading toast
                if (compilationToastId.current) {
                    showToast.dismiss(compilationToastId.current);
                }

                // Show error toast
                const errorMsg =
                    result.errors?.[0]?.message || "Compilation failed";
                showToast.latex.compileFailed(errorMsg);

                // Update compilation result
                setCompilationResult({
                    status: "error",
                    errors: result.errors || [],
                    log: result.log,
                });

                setCompiling(false);

                // Clean up SSE connection
                if (sseCleanup.current) {
                    sseCleanup.current();
                    sseCleanup.current = null;
                }
            },
        });
    };

    const handleRestoreBackup = async (versionId) => {
        if (
            !confirm(
                "Restore this version? Current unsaved changes will be lost.",
            )
        ) {
            return;
        }

        try {
            const data = await latexApi.getBackup(jobId, versionId);
            setContent(data.content);
            setOriginalContent(data.content);
            setIsDirty(false);

            // Find backup name for toast
            const backup = backups.find((b) => b.version_id === versionId);
            showToast.latex.restored(backup?.filename || "backup");
        } catch (err) {
            setError("Failed to restore backup");
            showToast.error("Failed to restore backup");
            console.error("Restore error:", err);
        }
    };

    const handleDownload = () => {
        if (pdfUrl) {
            const link = document.createElement("a");
            link.href = pdfUrl;
            link.download = "resume.pdf";
            link.click();
        }
    };

    const getSaveIndicator = () => {
        if (isSaving) return "Saving...";
        if (isDirty) return "Unsaved changes";
        if (lastSaved) return `Saved ${formatTimeAgo(lastSaved)}`;
        return "All changes saved";
    };

    const formatTimeAgo = (date) => {
        const seconds = Math.floor((new Date() - date) / 1000);
        if (seconds < 60) return "just now";
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes}m ago`;
        const hours = Math.floor(minutes / 60);
        return `${hours}h ago`;
    };

    if (error && !content) {
        return (
            <div className="flex items-center justify-center h-96">
                <div className="text-center">
                    <p className="text-red-600 dark:text-red-400 mb-4">
                        {error}
                    </p>
                    <button
                        onClick={loadSource}
                        className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                    >
                        Retry
                    </button>
                </div>
            </div>
        );
    }

    // Mobile Layout
    if (isMobile) {
        return (
            <div className="flex flex-col h-full">
                {/* Mobile Header */}
                <div className="flex items-center justify-between px-4 py-3 bg-white dark:bg-background-surface border-b border-slate-200 dark:border-slate-700">
                    <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-slate-900 dark:text-white">
                            {mobileView === "editor" ? "Editor" : "Preview"}
                        </span>
                        {isDirty && (
                            <span className="w-2 h-2 bg-yellow-500 rounded-full" />
                        )}
                    </div>
                    <button
                        onClick={() => setShowActionSheet(true)}
                        className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700"
                    >
                        <svg
                            className="w-6 h-6 text-slate-600 dark:text-slate-300"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth="2"
                                d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"
                            />
                        </svg>
                    </button>
                </div>

                {/* Mobile Tab Switcher */}
                <div className="flex border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-background-elevated">
                    <button
                        onClick={() => setMobileView("editor")}
                        className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                            mobileView === "editor"
                                ? "text-primary-600 dark:text-primary-400 border-b-2 border-primary-600 dark:border-primary-400 bg-white dark:bg-background-surface"
                                : "text-slate-600 dark:text-slate-400"
                        }`}
                    >
                        Editor
                        {isDirty && mobileView !== "editor" && (
                            <span className="ml-2 w-2 h-2 inline-block bg-yellow-500 rounded-full" />
                        )}
                    </button>
                    <button
                        onClick={() => setMobileView("preview")}
                        className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                            mobileView === "preview"
                                ? "text-primary-600 dark:text-primary-400 border-b-2 border-primary-600 dark:border-primary-400 bg-white dark:bg-background-surface"
                                : "text-slate-600 dark:text-slate-400"
                        }`}
                    >
                        Preview
                    </button>
                </div>

                {/* Mobile Content */}
                <div className="flex-1 min-h-0">
                    {mobileView === "editor" ? (
                        <div className="flex flex-col h-full">
                            <div className="flex-1 min-h-0">
                                <CodeEditor
                                    value={content}
                                    onChange={setContent}
                                    language="latex"
                                />
                            </div>
                            {/* Compilation Log */}
                            {compilationResult && (
                                <CompilationLog
                                    result={compilationResult}
                                    collapsed={logCollapsed}
                                    onToggleCollapse={() =>
                                        setLogCollapsed(!logCollapsed)
                                    }
                                />
                            )}
                        </div>
                    ) : (
                        <PdfViewer pdfUrl={pdfUrl} isCompiling={isCompiling} />
                    )}
                </div>

                {/* Floating Compile Button */}
                {mobileView === "editor" && (
                    <button
                        onClick={handleCompile}
                        disabled={isCompiling}
                        className="fixed bottom-6 right-6 w-14 h-14 bg-primary-600 text-white rounded-full shadow-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center z-30"
                    >
                        {isCompiling ? (
                            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white" />
                        ) : (
                            <span className="text-xl">🔨</span>
                        )}
                    </button>
                )}

                {/* Mobile Action Sheet */}
                <MobileActionSheet
                    isOpen={showActionSheet}
                    onClose={() => setShowActionSheet(false)}
                    onSave={handleSave}
                    onCompile={handleCompile}
                    onDownload={handleDownload}
                    onToggleView={() =>
                        setMobileView(
                            mobileView === "editor" ? "preview" : "editor",
                        )
                    }
                    onShowShortcuts={() => setShowShortcuts(true)}
                    isSaving={isSaving}
                    isCompiling={isCompiling}
                    isDirty={isDirty}
                    currentView={mobileView}
                    pdfUrl={pdfUrl}
                />

                {/* Keyboard Shortcuts Modal */}
                <KeyboardShortcutsModal
                    isOpen={showShortcuts}
                    onClose={() => setShowShortcuts(false)}
                />
            </div>
        );
    }

    // Desktop Layout
    return (
        <div className="flex flex-col h-full">
            {/* Toolbar */}
            <EditorToolbar
                onSave={handleSave}
                onCompile={handleCompile}
                isSaving={isSaving}
                isCompiling={isCompiling}
                isDirty={isDirty}
                saveIndicator={getSaveIndicator()}
                pdfUrl={pdfUrl}
                layout={layout}
                onLayoutChange={setLayout}
                onShowShortcuts={() => setShowShortcuts(true)}
            />

            {/* Version History Dropdown */}
            {backups.length > 0 && (
                <div className="px-4 py-2 bg-slate-50 dark:bg-background-elevated border-b border-slate-200 dark:border-slate-700">
                    <VersionHistory
                        backups={backups}
                        onRestore={handleRestoreBackup}
                    />
                </div>
            )}

            {/* Split Pane: Editor + Preview */}
            <div className="flex-1 min-h-0">
                {layout === "split" ? (
                    <PanelGroup orientation="horizontal" className="h-full">
                        {/* Editor Panel */}
                        <Panel defaultSize={50} minSize={25}>
                            <div className="flex flex-col h-full border-r border-slate-200 dark:border-slate-700">
                                <div className="flex-1 min-h-0">
                                    <CodeEditor
                                        value={content}
                                        onChange={setContent}
                                        language="latex"
                                    />
                                </div>

                                {/* Compilation Log */}
                                {compilationResult && (
                                    <CompilationLog
                                        result={compilationResult}
                                        collapsed={logCollapsed}
                                        onToggleCollapse={() =>
                                            setLogCollapsed(!logCollapsed)
                                        }
                                    />
                                )}
                            </div>
                        </Panel>

                        {/* Resize Handle */}
                        <PanelResizeHandle className="w-1.5 bg-slate-200 dark:bg-slate-700 hover:bg-primary-500 dark:hover:bg-primary-500 transition-colors cursor-col-resize" />

                        {/* Preview Panel */}
                        <Panel defaultSize={50} minSize={25}>
                            <div className="h-full bg-slate-100 dark:bg-background">
                                <PdfViewer
                                    pdfUrl={pdfUrl}
                                    isCompiling={isCompiling}
                                />
                            </div>
                        </Panel>
                    </PanelGroup>
                ) : layout === "editor" ? (
                    <div className="flex flex-col h-full">
                        <div className="flex-1 min-h-0">
                            <CodeEditor
                                value={content}
                                onChange={setContent}
                                language="latex"
                            />
                        </div>

                        {/* Compilation Log */}
                        {compilationResult && (
                            <CompilationLog
                                result={compilationResult}
                                collapsed={logCollapsed}
                                onToggleCollapse={() =>
                                    setLogCollapsed(!logCollapsed)
                                }
                            />
                        )}
                    </div>
                ) : (
                    <div className="h-full bg-slate-100 dark:bg-background">
                        <PdfViewer pdfUrl={pdfUrl} isCompiling={isCompiling} />
                    </div>
                )}
            </div>

            {/* Keyboard Shortcuts Modal */}
            <KeyboardShortcutsModal
                isOpen={showShortcuts}
                onClose={() => setShowShortcuts(false)}
            />
        </div>
    );
}

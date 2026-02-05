import LayoutToggle from "./LayoutToggle";

export default function EditorToolbar({
    onSave,
    onCompile,
    isSaving,
    isCompiling,
    isDirty,
    saveIndicator,
    pdfUrl,
    layout,
    onLayoutChange,
    onShowShortcuts,
}) {
    return (
        <div className="flex items-center justify-between px-4 py-3 bg-white dark:bg-background-surface border-b border-slate-200 dark:border-slate-700">
            {/* Left side: Title, status, layout toggle */}
            <div className="flex items-center gap-4">
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white hidden sm:block">
                    LaTeX Editor
                </h3>

                {/* Layout Toggle - Desktop only */}
                {onLayoutChange && (
                    <div className="hidden lg:block">
                        <LayoutToggle
                            layout={layout}
                            onLayoutChange={onLayoutChange}
                        />
                    </div>
                )}

                {/* Save indicator */}
                <div className="flex items-center gap-2">
                    <span className="text-sm text-slate-500 dark:text-slate-400 hidden sm:inline">
                        {saveIndicator}
                    </span>
                    {isDirty && (
                        <span
                            className="w-2 h-2 bg-yellow-500 rounded-full flex-shrink-0"
                            title="Unsaved changes"
                        />
                    )}
                </div>
            </div>

            {/* Right side: Actions */}
            <div className="flex items-center gap-2">
                {/* Keyboard shortcuts button */}
                {onShowShortcuts && (
                    <button
                        onClick={onShowShortcuts}
                        className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400 hidden sm:flex"
                        title="Keyboard Shortcuts"
                    >
                        <svg
                            className="w-5 h-5"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth="2"
                                d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
                            />
                        </svg>
                    </button>
                )}

                {/* Save button */}
                <button
                    onClick={onSave}
                    disabled={!isDirty || isSaving}
                    className="px-3 py-2 sm:px-4 bg-slate-600 text-white rounded-lg hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 text-sm sm:text-base"
                >
                    {isSaving ? (
                        <>
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                            <span className="hidden sm:inline">Saving...</span>
                        </>
                    ) : (
                        <>
                            <span>💾</span>
                            <span className="hidden sm:inline">Save</span>
                            <span className="text-xs opacity-75 hidden md:inline">
                                (Ctrl+S)
                            </span>
                        </>
                    )}
                </button>

                {/* Compile button */}
                <button
                    onClick={onCompile}
                    disabled={isCompiling}
                    className="px-3 py-2 sm:px-4 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 text-sm sm:text-base"
                >
                    {isCompiling ? (
                        <>
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                            <span className="hidden sm:inline">
                                Compiling...
                            </span>
                        </>
                    ) : (
                        <>
                            <span>🔨</span>
                            <span className="hidden sm:inline">Compile</span>
                            <span className="text-xs opacity-75 hidden md:inline">
                                (Ctrl+Enter)
                            </span>
                        </>
                    )}
                </button>

                {/* Download button */}
                {pdfUrl && (
                    <a
                        href={pdfUrl}
                        download="resume.pdf"
                        className="px-3 py-2 sm:px-4 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center gap-2 text-sm sm:text-base"
                    >
                        <span>📥</span>
                        <span className="hidden sm:inline">Download PDF</span>
                    </a>
                )}
            </div>
        </div>
    );
}

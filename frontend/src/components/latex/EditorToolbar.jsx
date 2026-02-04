export default function EditorToolbar({
    onSave,
    onCompile,
    isSaving,
    isCompiling,
    isDirty,
    saveIndicator,
    pdfUrl,
}) {
    return (
        <div className="flex items-center justify-between px-4 py-3 bg-white dark:bg-background-surface border-b border-slate-200 dark:border-slate-700">
            <div className="flex items-center gap-4">
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                    LaTeX Editor
                </h3>
                <span className="text-sm text-slate-500 dark:text-slate-400">
                    {saveIndicator}
                </span>
                {isDirty && (
                    <span
                        className="w-2 h-2 bg-yellow-500 rounded-full"
                        title="Unsaved changes"
                    ></span>
                )}
            </div>

            <div className="flex items-center gap-2">
                <button
                    onClick={onSave}
                    disabled={!isDirty || isSaving}
                    className="px-4 py-2 bg-slate-600 text-white rounded-lg hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                    {isSaving ? (
                        <>
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                            Saving...
                        </>
                    ) : (
                        <>
                            💾 Save
                            <span className="text-xs opacity-75">(Ctrl+S)</span>
                        </>
                    )}
                </button>

                <button
                    onClick={onCompile}
                    disabled={isCompiling}
                    className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                    {isCompiling ? (
                        <>
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                            Compiling...
                        </>
                    ) : (
                        <>
                            🔨 Compile
                            <span className="text-xs opacity-75">
                                (Ctrl+Enter)
                            </span>
                        </>
                    )}
                </button>

                {pdfUrl && (
                    <a
                        href={pdfUrl}
                        download="resume.pdf"
                        className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center gap-2"
                    >
                        📥 Download PDF
                    </a>
                )}
            </div>
        </div>
    );
}

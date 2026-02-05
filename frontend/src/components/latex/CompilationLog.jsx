export default function CompilationLog({
    result,
    collapsed,
    onToggleCollapse,
}) {
    if (!result) return null;

    const { status, errors = [], warnings = [], log, message } = result;

    const errorCount = errors.length;
    const warningCount = warnings.length;

    // Determine status color
    const getStatusColor = () => {
        if (status === "success") return "bg-green-600";
        if (status === "error") return "bg-red-600";
        if (status === "compiling") return "bg-blue-600";
        return "bg-yellow-600";
    };

    const getStatusText = () => {
        if (status === "compiling") return message || "Compiling...";
        if (status === "success") return "Success";
        if (status === "error")
            return `${errorCount} Error${errorCount !== 1 ? "s" : ""}`;
        return status?.toUpperCase() || "Unknown";
    };

    return (
        <div
            className={`flex flex-col bg-slate-900 text-slate-100 transition-all duration-200 ${
                collapsed ? "h-10" : "h-48 sm:h-56"
            }`}
        >
            {/* Header - Always visible, clickable to toggle */}
            <button
                onClick={onToggleCollapse}
                className="flex items-center justify-between px-4 py-2 bg-slate-800 border-t border-b border-slate-700 hover:bg-slate-750 transition-colors w-full text-left"
            >
                <div className="flex items-center gap-3">
                    <h4 className="text-sm font-semibold">Compilation Log</h4>

                    {/* Status badges */}
                    <div className="flex items-center gap-2">
                        {status && (
                            <span
                                className={`text-xs px-2 py-0.5 rounded ${getStatusColor()}`}
                            >
                                {getStatusText()}
                            </span>
                        )}

                        {!collapsed && warningCount > 0 && (
                            <span className="text-xs px-2 py-0.5 rounded bg-yellow-600">
                                {warningCount} Warning
                                {warningCount !== 1 ? "s" : ""}
                            </span>
                        )}
                    </div>
                </div>

                {/* Collapse indicator */}
                <div className="flex items-center gap-2 text-slate-400">
                    <span className="text-xs hidden sm:inline">
                        {collapsed ? "Show details" : "Hide details"}
                    </span>
                    <svg
                        className={`w-4 h-4 transition-transform ${collapsed ? "" : "rotate-180"}`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth="2"
                            d="M19 9l-7 7-7-7"
                        />
                    </svg>
                </div>
            </button>

            {/* Content - Hidden when collapsed */}
            {!collapsed && (
                <div className="flex-1 overflow-auto p-4 font-mono text-sm">
                    {/* Compiling state */}
                    {status === "compiling" && (
                        <div className="flex items-center gap-3 text-blue-400">
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-400" />
                            <span>{message || "Compiling..."}</span>
                        </div>
                    )}

                    {/* Errors */}
                    {errors.length > 0 && (
                        <div className="mb-4">
                            <div className="text-red-400 font-bold mb-2 flex items-center gap-2">
                                <svg
                                    className="w-4 h-4"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth="2"
                                        d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                    />
                                </svg>
                                Errors ({errors.length})
                            </div>
                            {errors.map((err, idx) => (
                                <div
                                    key={idx}
                                    className="mb-2 pl-4 border-l-2 border-red-500 py-1"
                                >
                                    {err.line && (
                                        <span className="text-red-300 font-semibold">
                                            Line {err.line}:{" "}
                                        </span>
                                    )}
                                    <span className="text-red-200">
                                        {err.message}
                                    </span>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Warnings */}
                    {warnings.length > 0 && (
                        <div className="mb-4">
                            <div className="text-yellow-400 font-bold mb-2 flex items-center gap-2">
                                <svg
                                    className="w-4 h-4"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth="2"
                                        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                                    />
                                </svg>
                                Warnings ({warnings.length})
                            </div>
                            {warnings.map((warn, idx) => (
                                <div
                                    key={idx}
                                    className="mb-1 pl-4 text-yellow-200 border-l-2 border-yellow-500 py-1"
                                >
                                    {warn.message}
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Full Log */}
                    {log && (
                        <div>
                            <div className="text-slate-400 font-bold mb-2 flex items-center gap-2">
                                <svg
                                    className="w-4 h-4"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth="2"
                                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                                    />
                                </svg>
                                Full Log
                            </div>
                            <pre className="text-xs text-slate-300 whitespace-pre-wrap bg-slate-950 p-3 rounded border border-slate-700 max-h-32 overflow-auto">
                                {log}
                            </pre>
                        </div>
                    )}

                    {/* Success with no issues */}
                    {status === "success" &&
                        !errors.length &&
                        !warnings.length &&
                        !log && (
                            <div className="flex items-center gap-3 text-green-400">
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
                                        d="M5 13l4 4L19 7"
                                    />
                                </svg>
                                <span>
                                    {message ||
                                        "Compilation completed successfully"}
                                </span>
                            </div>
                        )}

                    {/* Fallback */}
                    {!errors.length &&
                        !warnings.length &&
                        !log &&
                        status !== "success" &&
                        status !== "compiling" && (
                            <div className="text-slate-400 italic">
                                {message || "No compilation output"}
                            </div>
                        )}
                </div>
            )}
        </div>
    );
}

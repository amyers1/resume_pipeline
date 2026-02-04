export default function CompilationLog({ result }) {
    if (!result) return null;

    const { status, errors = [], warnings = [], log } = result;

    return (
        <div className="h-full flex flex-col bg-slate-900 text-slate-100 overflow-hidden">
            <div className="px-4 py-2 bg-slate-800 border-b border-slate-700 flex items-center justify-between">
                <h4 className="text-sm font-semibold">Compilation Log</h4>
                {status && (
                    <span
                        className={`text-xs px-2 py-1 rounded ${
                            status === "success"
                                ? "bg-green-600"
                                : status === "error"
                                  ? "bg-red-600"
                                  : "bg-yellow-600"
                        }`}
                    >
                        {status.toUpperCase()}
                    </span>
                )}
            </div>

            <div className="flex-1 overflow-auto p-4 font-mono text-sm">
                {errors.length > 0 && (
                    <div className="mb-4">
                        <div className="text-red-400 font-bold mb-2">
                            Errors:
                        </div>
                        {errors.map((err, idx) => (
                            <div
                                key={idx}
                                className="mb-2 pl-4 border-l-2 border-red-500"
                            >
                                {err.line && (
                                    <span className="text-red-300">
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

                {warnings.length > 0 && (
                    <div className="mb-4">
                        <div className="text-yellow-400 font-bold mb-2">
                            Warnings:
                        </div>
                        {warnings.map((warn, idx) => (
                            <div
                                key={idx}
                                className="mb-1 pl-4 text-yellow-200"
                            >
                                {warn.message}
                            </div>
                        ))}
                    </div>
                )}

                {log && (
                    <div>
                        <div className="text-slate-400 font-bold mb-2">
                            Full Log:
                        </div>
                        <pre className="text-xs text-slate-300 whitespace-pre-wrap">
                            {log}
                        </pre>
                    </div>
                )}

                {!errors.length && !warnings.length && !log && (
                    <div className="text-slate-400 italic">
                        {result.message || "No compilation output"}
                    </div>
                )}
            </div>
        </div>
    );
}

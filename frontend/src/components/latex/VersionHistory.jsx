import { useState } from "react";

export default function VersionHistory({ backups, onRestore }) {
    const [isOpen, setIsOpen] = useState(false);

    if (backups.length === 0) return null;

    return (
        <div className="relative">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="text-sm px-3 py-1 bg-slate-200 dark:bg-slate-700 rounded hover:bg-slate-300 dark:hover:bg-slate-600"
            >
                📚 Version History ({backups.length})
            </button>

            {isOpen && (
                <>
                    <div
                        className="fixed inset-0 z-10"
                        onClick={() => setIsOpen(false)}
                    ></div>
                    <div className="absolute top-full left-0 mt-1 w-80 bg-white dark:bg-background-surface border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg z-20 max-h-96 overflow-auto">
                        <div className="p-2">
                            {backups.map((backup, idx) => (
                                <button
                                    key={idx}
                                    onClick={() => {
                                        onRestore(backup.version_id);
                                        setIsOpen(false);
                                    }}
                                    className="w-full text-left px-3 py-2 rounded hover:bg-slate-100 dark:hover:bg-slate-700 mb-1"
                                >
                                    <div className="flex items-center justify-between">
                                        <div className="flex-1">
                                            <div className="text-sm font-medium text-slate-900 dark:text-white">
                                                {backup.filename}
                                            </div>
                                            <div className="text-xs text-slate-500 dark:text-slate-400">
                                                {new Date(
                                                    backup.modified,
                                                ).toLocaleString()}
                                            </div>
                                        </div>
                                        <div className="text-xs text-slate-400">
                                            {(backup.size / 1024).toFixed(1)} KB
                                        </div>
                                    </div>
                                </button>
                            ))}
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}

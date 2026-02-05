import { useEffect } from "react";

export default function KeyboardShortcutsModal({ isOpen, onClose }) {
    // Close on escape key
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === "Escape") {
                onClose();
            }
        };

        if (isOpen) {
            window.addEventListener("keydown", handleKeyDown);
            document.body.style.overflow = "hidden";
        }

        return () => {
            window.removeEventListener("keydown", handleKeyDown);
            document.body.style.overflow = "";
        };
    }, [isOpen, onClose]);

    if (!isOpen) return null;

    const shortcuts = [
        { keys: ["Ctrl", "S"], description: "Save document" },
        { keys: ["Ctrl", "Enter"], description: "Compile LaTeX" },
        { keys: ["Ctrl", "Z"], description: "Undo" },
        { keys: ["Ctrl", "Shift", "Z"], description: "Redo" },
        { keys: ["Ctrl", "F"], description: "Find" },
        { keys: ["Ctrl", "H"], description: "Find and replace" },
        { keys: ["Ctrl", "/"], description: "Toggle comment" },
        { keys: ["Ctrl", "D"], description: "Select next occurrence" },
        { keys: ["Alt", "↑"], description: "Move line up" },
        { keys: ["Alt", "↓"], description: "Move line down" },
        { keys: ["Ctrl", "Shift", "K"], description: "Delete line" },
    ];

    const isMac =
        typeof navigator !== "undefined" &&
        navigator.platform.toUpperCase().indexOf("MAC") >= 0;

    const formatKey = (key) => {
        if (isMac) {
            return key
                .replace("Ctrl", "⌘")
                .replace("Alt", "⌥")
                .replace("Shift", "⇧");
        }
        return key;
    };

    return (
        <>
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-black/50 z-40 animate-fade-in"
                onClick={onClose}
            />

            {/* Modal */}
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
                <div
                    className="bg-white dark:bg-background-surface rounded-xl shadow-2xl w-full max-w-md max-h-[80vh] overflow-hidden animate-scale-in"
                    onClick={(e) => e.stopPropagation()}
                >
                    {/* Header */}
                    <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
                        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                            Keyboard Shortcuts
                        </h2>
                        <button
                            onClick={onClose}
                            className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500 dark:text-slate-400"
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
                                    d="M6 18L18 6M6 6l12 12"
                                />
                            </svg>
                        </button>
                    </div>

                    {/* Shortcuts List */}
                    <div className="px-6 py-4 overflow-y-auto max-h-[60vh]">
                        <div className="space-y-3">
                            {shortcuts.map((shortcut, index) => (
                                <div
                                    key={index}
                                    className="flex items-center justify-between py-2"
                                >
                                    <span className="text-slate-600 dark:text-slate-300">
                                        {shortcut.description}
                                    </span>
                                    <div className="flex items-center gap-1">
                                        {shortcut.keys.map((key, keyIndex) => (
                                            <span key={keyIndex}>
                                                <kbd className="px-2 py-1 text-xs font-mono bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 rounded border border-slate-300 dark:border-slate-600 shadow-sm">
                                                    {formatKey(key)}
                                                </kbd>
                                                {keyIndex < shortcut.keys.length - 1 && (
                                                    <span className="text-slate-400 mx-0.5">+</span>
                                                )}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Footer */}
                    <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                        <p className="text-xs text-slate-500 dark:text-slate-400 text-center">
                            {isMac
                                ? "On Mac, use ⌘ (Command) instead of Ctrl"
                                : "On Mac, use ⌘ (Command) instead of Ctrl"}
                        </p>
                    </div>
                </div>
            </div>
        </>
    );
}

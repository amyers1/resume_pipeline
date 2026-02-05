import { useEffect } from "react";

export default function MobileActionSheet({
    isOpen,
    onClose,
    onSave,
    onCompile,
    onDownload,
    onToggleView,
    onShowShortcuts,
    isSaving,
    isCompiling,
    isDirty,
    currentView,
    pdfUrl,
}) {
    // Close on escape key
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === "Escape") {
                onClose();
            }
        };

        if (isOpen) {
            window.addEventListener("keydown", handleKeyDown);
            // Prevent body scroll when open
            document.body.style.overflow = "hidden";
        }

        return () => {
            window.removeEventListener("keydown", handleKeyDown);
            document.body.style.overflow = "";
        };
    }, [isOpen, onClose]);

    if (!isOpen) return null;

    const actions = [
        {
            label: "Save",
            icon: "💾",
            onClick: () => {
                onSave();
                onClose();
            },
            disabled: !isDirty || isSaving,
            loading: isSaving,
        },
        {
            label: "Compile",
            icon: "🔨",
            onClick: () => {
                onCompile();
                onClose();
            },
            disabled: isCompiling,
            loading: isCompiling,
            primary: true,
        },
        {
            label: "Download PDF",
            icon: "📥",
            onClick: () => {
                onDownload();
                onClose();
            },
            disabled: !pdfUrl,
        },
        {
            label: currentView === "editor" ? "Show Preview" : "Show Editor",
            icon: "🔄",
            onClick: () => {
                onToggleView();
                onClose();
            },
        },
        {
            label: "Keyboard Shortcuts",
            icon: "⌨️",
            onClick: () => {
                onShowShortcuts();
                onClose();
            },
        },
    ];

    return (
        <>
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-black/50 z-40 animate-fade-in"
                onClick={onClose}
            />

            {/* Action Sheet */}
            <div className="fixed bottom-0 left-0 right-0 z-50 animate-slide-up">
                <div className="bg-white dark:bg-background-surface rounded-t-2xl shadow-2xl">
                    {/* Handle */}
                    <div className="flex justify-center py-3">
                        <div className="w-10 h-1 bg-slate-300 dark:bg-slate-600 rounded-full" />
                    </div>

                    {/* Actions */}
                    <div className="px-4 pb-8 space-y-2">
                        {actions.map((action, index) => (
                            <button
                                key={index}
                                onClick={action.onClick}
                                disabled={action.disabled}
                                className={`
                                    w-full flex items-center gap-4 px-4 py-4 rounded-xl
                                    transition-colors
                                    ${
                                        action.primary
                                            ? "bg-primary-600 text-white hover:bg-primary-700"
                                            : "bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-white hover:bg-slate-200 dark:hover:bg-slate-700"
                                    }
                                    ${action.disabled ? "opacity-50 cursor-not-allowed" : ""}
                                `}
                            >
                                {action.loading ? (
                                    <div className="w-6 h-6 flex items-center justify-center">
                                        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-current" />
                                    </div>
                                ) : (
                                    <span className="text-xl">{action.icon}</span>
                                )}
                                <span className="font-medium">{action.label}</span>
                            </button>
                        ))}

                        {/* Cancel */}
                        <button
                            onClick={onClose}
                            className="w-full px-4 py-4 mt-2 rounded-xl bg-slate-200 dark:bg-slate-700 text-slate-900 dark:text-white font-medium hover:bg-slate-300 dark:hover:bg-slate-600 transition-colors"
                        >
                            Cancel
                        </button>
                    </div>
                </div>
            </div>
        </>
    );
}

import toast from "react-hot-toast";

/**
 * Toast notification utility
 * Provides consistent toast notifications across the application
 */

export const showToast = {
    success: (message, options = {}) => {
        toast.success(message, {
            duration: 3000,
            position: "top-right",
            ...options,
        });
    },

    error: (message, options = {}) => {
        toast.error(message, {
            duration: 4000,
            position: "top-right",
            ...options,
        });
    },

    loading: (message, options = {}) => {
        return toast.loading(message, {
            position: "top-right",
            ...options,
        });
    },

    promise: (promise, messages, options = {}) => {
        return toast.promise(
            promise,
            {
                loading: messages.loading || "Loading...",
                success: messages.success || "Success!",
                error: messages.error || "Error occurred",
            },
            {
                position: "top-right",
                ...options,
            },
        );
    },

    dismiss: (toastId) => {
        toast.dismiss(toastId);
    },

    dismissAll: () => {
        toast.dismiss();
    },

    // Custom toast with icon
    custom: (message, icon, options = {}) => {
        toast(message, {
            icon: icon,
            duration: 3000,
            position: "top-right",
            ...options,
        });
    },

    // LaTeX-specific notifications
    latex: {
        saved: () => {
            toast.success("LaTeX source saved", {
                icon: "💾",
                duration: 2000,
                position: "top-right",
            });
        },

        compiling: () => {
            return toast.loading("Compiling LaTeX...", {
                icon: "🔨",
                position: "top-right",
            });
        },

        compiled: () => {
            toast.success("PDF compiled successfully", {
                icon: "✅",
                duration: 3000,
                position: "top-right",
            });
        },

        compileFailed: (error) => {
            toast.error(`Compilation failed: ${error}`, {
                icon: "❌",
                duration: 5000,
                position: "top-right",
            });
        },

        restored: (versionName) => {
            toast.success(`Restored version: ${versionName}`, {
                icon: "↩️",
                duration: 3000,
                position: "top-right",
            });
        },
    },
};

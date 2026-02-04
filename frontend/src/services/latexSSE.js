/**
 * LaTeX Compilation SSE Service
 *
 * Listens for real-time LaTeX compilation updates via Server-Sent Events (SSE)
 * from the latex_progress and latex_status queues.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";

/**
 * Create SSE connection for LaTeX compilation updates
 *
 * @param {string} jobId - The job ID to monitor
 * @param {Object} callbacks - Callback functions for different events
 * @param {Function} callbacks.onProgress - Called on compilation progress updates
 * @param {Function} callbacks.onComplete - Called when compilation succeeds
 * @param {Function} callbacks.onError - Called when compilation fails
 * @param {Function} callbacks.onConnect - Called when SSE connection established
 * @returns {Function} Cleanup function to close the SSE connection
 */
export function createLatexCompilationSSE(jobId, callbacks = {}) {
    const {
        onProgress = () => {},
        onComplete = () => {},
        onError = () => {},
        onConnect = () => {},
    } = callbacks;

    // Use the existing job status SSE endpoint which handles all queue messages
    // The backend already broadcasts latex_progress and latex_status messages
    const eventSource = new EventSource(
        `${API_BASE_URL}/jobs/${jobId}/status/stream`,
    );

    let isConnected = false;

    eventSource.onopen = () => {
        isConnected = true;
        console.log("LaTeX SSE connection opened");
        onConnect();
    };

    eventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);

            // Filter for LaTeX-specific messages
            if (data.type === "LATEX_PROGRESS") {
                onProgress({
                    stage: data.stage,
                    percent: data.percent,
                    message: data.message,
                    timestamp: data.timestamp,
                });
            } else if (data.type === "LATEX_COMPLETED") {
                onComplete({
                    success: data.result?.success,
                    pdf_s3_key: data.result?.pdf_s3_key,
                    pdf_url: data.result?.pdf_url,
                    warnings: data.result?.warnings || [],
                    compiled_at: data.result?.compiled_at,
                });
            } else if (data.type === "LATEX_FAILED") {
                onError({
                    success: false,
                    errors: data.result?.errors || [],
                    log: data.result?.log,
                });
            }
        } catch (err) {
            console.error("Error parsing LaTeX SSE message:", err);
        }
    };

    eventSource.onerror = (error) => {
        console.error("LaTeX SSE connection error:", error);
        if (eventSource.readyState === EventSource.CLOSED) {
            console.log("LaTeX SSE connection closed");
        }
    };

    // Return cleanup function
    return () => {
        if (isConnected) {
            console.log("Closing LaTeX SSE connection");
            eventSource.close();
        }
    };
}

/**
 * Simplified hook-like function for LaTeX compilation monitoring
 * Returns a function to start monitoring and a cleanup function
 */
export function useLatexCompilationMonitor(jobId) {
    let cleanup = null;

    const startMonitoring = (callbacks) => {
        // Clean up any existing connection
        if (cleanup) {
            cleanup();
        }

        // Start new monitoring
        cleanup = createLatexCompilationSSE(jobId, callbacks);
    };

    const stopMonitoring = () => {
        if (cleanup) {
            cleanup();
            cleanup = null;
        }
    };

    return {
        startMonitoring,
        stopMonitoring,
    };
}

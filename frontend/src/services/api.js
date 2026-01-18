import axios from "axios";
import { API_CONFIG } from "../utils/constants";

// Create axios instance
const api = axios.create(API_CONFIG);

// Request interceptor
api.interceptors.request.use(
    (config) => {
        return config;
    },
    (error) => {
        return Promise.reject(error);
    },
);

// Response interceptor
api.interceptors.response.use(
    (response) => {
        // Log request ID for debugging
        const requestId = response.headers["x-request-id"];
        if (requestId) {
            console.log("Request ID:", requestId);
        }
        return response;
    },
    (error) => {
        // Handle errors consistently
        if (error.response) {
            // Server responded with error
            console.error("API Error:", error.response.data);
        } else if (error.request) {
            // Request made but no response
            console.error("Network Error:", error.message);
        } else {
            // Something else happened
            console.error("Error:", error.message);
        }
        return Promise.reject(error);
    },
);

// API Methods
export const apiService = {
    // Health check
    checkHealth: () => api.get("/health"),

    // Job operations
    submitJob: (jobData) => api.post("/jobs", jobData),
    listJobs: (params) => api.get("/jobs", { params }),
    getJobDetails: (jobId) => api.get(`/jobs/${jobId}`),
    resubmitJob: (jobId, options) => api.post(`/jobs/${jobId}/submit`, options),
    deleteJob: (jobId) => api.delete(`/jobs/${jobId}`),

    // File operations
    listJobFiles: (jobId) => api.get(`/jobs/${jobId}/files`),
    downloadFile: (jobId, filename) => {
        return api.get(`/jobs/${jobId}/files/${filename}`, {
            responseType: "blob",
        });
    },

    // Profile operations
    listProfiles: () => api.get("/profiles"),
    uploadProfile: (formData) => {
        return api.post("/profiles", formData, {
            headers: {
                "Content-Type": "multipart/form-data",
            },
        });
    },
    deleteProfile: (filename) => api.delete(`/profiles/${filename}`),

    // Job template operations
    listJobTemplates: () => api.get("/job-templates"),
    getJobTemplate: (filename) => api.get(`/job-templates/${filename}`),
};

// =========================================================
// SHARED EVENT SOURCE (Broadcast Pattern)
// =========================================================

let globalEventSource = null;
const globalListeners = new Set();

const getGlobalEventSource = () => {
    if (!globalEventSource) {
        // Connect to the new single broadcast endpoint
        // Nginx will proxy '/api/events' -> 'http://api:8000/events'
        globalEventSource = new EventSource("/api/events");

        globalEventSource.onmessage = (event) => {
            try {
                // The data might be double-encoded depending on the backend serializer
                const raw = JSON.parse(event.data);
                // If the backend wraps it in {"data": ...}, unwrap it
                const payload = raw.data
                    ? typeof raw.data === "string"
                        ? JSON.parse(raw.data)
                        : raw.data
                    : raw;

                // Broadcast to all active listeners
                globalListeners.forEach((listener) => listener(payload));
            } catch (error) {
                console.error("Failed to parse SSE message:", error);
            }
        };

        globalEventSource.onerror = (error) => {
            console.error("SSE connection lost or error:", error);
            // EventSource automatically retries, so we just log it
        };
    }
    return globalEventSource;
};

// SSE connection for a SPECIFIC job
export const createJobStatusSSE = (jobId, callbacks) => {
    // Ensure the global connection is active
    getGlobalEventSource();

    const listener = (payload) => {
        // Only trigger callback if the message is for THIS job
        if (payload && payload.job_id === jobId) {
            callbacks.onMessage?.(payload);
        }
    };

    globalListeners.add(listener);

    // Return cleanup function
    return () => {
        globalListeners.delete(listener);
        // Note: We intentionally do NOT close the global connection
        // so other components (like the Dashboard) keep receiving updates.
    };
};

// SSE connection for ALL jobs (Dashboard)
export const createAllJobsStatusSSE = (callbacks) => {
    // Ensure the global connection is active
    getGlobalEventSource();

    const listener = (payload) => {
        callbacks.onMessage?.(payload);
    };

    globalListeners.add(listener);

    return () => {
        globalListeners.delete(listener);
    };
};

export default api;

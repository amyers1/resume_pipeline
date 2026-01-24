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

    // User operations
    listUsers: () => api.get("/users"),
    createUser: (userData) => api.post("/users", userData),

    // Profile operations (Updated)
    listUserProfiles: (userId) => api.get(`/users/${userId}/profiles`),
    getProfile: (userId, profileId) =>
        api.get(`/users/${userId}/profiles/${profileId}`),
    updateProfile: (userId, profileId, profileData) =>
        api.put(`/users/${userId}/profiles/${profileId}`, profileData),
    deleteProfile: (userId, profileId) =>
        api.delete(`/users/${userId}/profiles/${profileId}`),
    createProfile: (userId, profileData) =>
        api.post(`/users/${userId}/profiles`, profileData),

    // Create profile for specific user (Replaces uploadProfile)
    createProfile: (userId, profileData) => {
        return api.post(`/users/${userId}/profiles`, profileData);
    },

    // Job template operations
    listJobTemplates: () => api.get("/job-templates"),
    getJobTemplate: (filename) => api.get(`/job-templates/${filename}`),
};

// =========================================================
// SHARED EVENT SOURCE (Broadcast Pattern)
// =========================================================

let globalEventSource = null;
const globalListeners = new Set();
let reconnectTimer = null;

// Internal function to establish connection
const connectSSE = () => {
    // Prevent duplicate connections
    if (
        globalEventSource &&
        globalEventSource.readyState !== EventSource.CLOSED
    ) {
        return;
    }

    // Clean up existing closed connection if needed
    if (globalEventSource) {
        globalEventSource.close();
    }

    console.log("Connecting to SSE stream...");
    globalEventSource = new EventSource("/api/events");

    globalEventSource.onmessage = (event) => {
        try {
            // Heartbeats (comments) are automatically ignored by EventSource
            // We only process "data" messages
            const raw = JSON.parse(event.data);

            // Handle double-encoded data if present
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
        console.error("SSE connection error:", error);

        // If the connection is closed, attempt to reconnect after a delay
        if (globalEventSource.readyState === EventSource.CLOSED) {
            globalEventSource = null;
            clearTimeout(reconnectTimer);
            reconnectTimer = setTimeout(() => {
                console.log("Attempting SSE reconnection...");
                connectSSE();
            }, 3000); // Retry after 3 seconds
        }
    };

    // Explicitly handle open to clear any reconnect timers
    globalEventSource.onopen = () => {
        console.log("SSE Connected");
        clearTimeout(reconnectTimer);
    };
};

const getGlobalEventSource = () => {
    if (
        !globalEventSource ||
        globalEventSource.readyState === EventSource.CLOSED
    ) {
        connectSSE();
    }
    return globalEventSource;
};

// SSE connection for a SPECIFIC job
export const createJobStatusSSE = (jobId, callbacks) => {
    // Ensure connection exists
    getGlobalEventSource();

    const listener = (payload) => {
        if (payload && payload.job_id === jobId) {
            callbacks.onMessage?.(payload);
        }
    };

    globalListeners.add(listener);

    // Return cleanup function
    return () => {
        globalListeners.delete(listener);
        // We do NOT close the connection here as it is shared
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

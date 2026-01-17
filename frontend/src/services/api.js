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

// SSE connection for job status
export const createJobStatusSSE = (jobId, callbacks) => {
    const eventSource = new EventSource(`/api/jobs/${jobId}/status`);

    eventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            callbacks.onMessage?.(data);
        } catch (error) {
            console.error("Failed to parse SSE message:", error);
        }
    };

    eventSource.onerror = (error) => {
        console.error("SSE error:", error);
        callbacks.onError?.(error);
        eventSource.close();
    };

    // Return cleanup function
    return () => eventSource.close();
};

// SSE connection for all jobs
export const createAllJobsStatusSSE = (callbacks) => {
    const eventSource = new EventSource(`/api/jobs/status`);

    eventSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            callbacks.onMessage?.(data);
        } catch (error) {
            console.error("Failed to parse SSE message:", error);
        }
    };

    eventSource.onerror = (error) => {
        console.error("SSE error:", error);
        callbacks.onError?.(error);
        eventSource.close();
    };

    return () => eventSource.close();
};

export default api;

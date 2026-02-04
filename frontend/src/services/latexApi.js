import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";

export const latexApi = {
    /**
     * Get LaTeX source content from S3
     */
    getSource: async (jobId) => {
        const response = await axios.get(
            `${API_BASE_URL}/jobs/${jobId}/latex/source`,
        );
        return response.data;
    },

    /**
     * Save LaTeX source to S3
     */
    saveSource: async (jobId, content, createBackup = true) => {
        const response = await axios.put(
            `${API_BASE_URL}/jobs/${jobId}/latex/source`,
            {
                content,
                create_backup: createBackup,
            },
        );
        return response.data;
    },

    /**
     * Request compilation via RabbitMQ
     */
    compile: async (
        jobId,
        content,
        engine = "xelatex",
        createBackup = true,
    ) => {
        const response = await axios.post(
            `${API_BASE_URL}/jobs/${jobId}/latex/compile`,
            {
                content,
                engine,
                create_backup: createBackup,
                filename: "resume.tex",
            },
        );
        return response.data;
    },

    /**
     * List backup versions
     */
    listBackups: async (jobId) => {
        const response = await axios.get(
            `${API_BASE_URL}/jobs/${jobId}/latex/backups`,
        );
        return response.data;
    },

    /**
     * Get specific backup version
     */
    getBackup: async (jobId, versionId) => {
        // Note: Backend needs this endpoint implemented
        const response = await axios.get(
            `${API_BASE_URL}/jobs/${jobId}/latex/backups/${versionId}`,
        );
        return response.data;
    },
};

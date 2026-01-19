import { useState, useEffect } from "react";
import { apiService } from "../../services/api";

export default function JobDetailsStep({
    formData,
    setFormData,
    onNext,
    existingJobs,
    onDeleteJob,
}) {
    const [selectedJobId, setSelectedJobId] = useState("");

    // Handle Dropdown Selection
    const handleJobSelect = (e) => {
        const jobId = e.target.value;
        setSelectedJobId(jobId);

        if (!jobId) {
            // Clear fields if "New Job" selected
            setFormData((prev) => ({
                ...prev,
                company: "",
                job_title: "",
                job_description: "",
            }));
            return;
        }

        const job = existingJobs.find(
            (j) => j.id === jobId || j.job_id === jobId,
        );
        if (job) {
            // Flatten the nested description JSON
            const description =
                job.job_description_json?.job_details?.description ||
                job.job_description_json?.description ||
                JSON.stringify(job.job_description_json, null, 2);

            setFormData((prev) => ({
                ...prev,
                company: job.company,
                job_title: job.job_title,
                job_description:
                    typeof description === "string"
                        ? description
                        : JSON.stringify(description),
            }));
        }
    };

    const isFormValid =
        formData.company && formData.job_title && formData.job_description;

    return (
        <div className="space-y-6">
            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-100 dark:border-blue-800">
                <label className="block text-sm font-medium text-blue-900 dark:text-blue-100 mb-2">
                    Start from existing job?
                </label>
                <div className="flex gap-2">
                    <select
                        value={selectedJobId}
                        onChange={handleJobSelect}
                        className="flex-1 rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm focus:border-primary-500 focus:ring-primary-500"
                    >
                        <option value="">-- Create Fresh Job Listing --</option>
                        {existingJobs.map((job) => (
                            <option
                                key={job.id || job.job_id}
                                value={job.id || job.job_id}
                            >
                                {job.company} - {job.job_title}
                            </option>
                        ))}
                    </select>

                    {selectedJobId && (
                        <button
                            type="button"
                            onClick={() => onDeleteJob(selectedJobId)}
                            className="px-3 py-2 bg-red-600 text-white text-sm font-medium rounded hover:bg-red-700 transition-colors"
                        >
                            Delete Listing
                        </button>
                    )}
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Company Name
                    </label>
                    <input
                        type="text"
                        required
                        value={formData.company}
                        onChange={(e) =>
                            setFormData((prev) => ({
                                ...prev,
                                company: e.target.value,
                            }))
                        }
                        className="w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm focus:border-primary-500 focus:ring-primary-500"
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Job Title
                    </label>
                    <input
                        type="text"
                        required
                        value={formData.job_title}
                        onChange={(e) =>
                            setFormData((prev) => ({
                                ...prev,
                                job_title: e.target.value,
                            }))
                        }
                        className="w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm focus:border-primary-500 focus:ring-primary-500"
                    />
                </div>
            </div>

            <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Job Description
                </label>
                <textarea
                    required
                    rows={10}
                    value={formData.job_description}
                    onChange={(e) =>
                        setFormData((prev) => ({
                            ...prev,
                            job_description: e.target.value,
                        }))
                    }
                    className="w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm focus:border-primary-500 focus:ring-primary-500 font-mono text-sm"
                    placeholder="Paste the full job description here..."
                />
            </div>

            <div className="flex justify-end">
                <button
                    onClick={onNext}
                    disabled={!isFormValid}
                    className="px-6 py-2 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                    Next: Career Profile →
                </button>
            </div>
        </div>
    );
}

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { apiService } from "../services/api";
import { TEMPLATES, OUTPUT_BACKENDS } from "../utils/constants";

export default function NewJobPage() {
    const navigate = useNavigate();
    const [submitting, setSubmitting] = useState(false);
    const [errors, setErrors] = useState({});
    const [profiles, setProfiles] = useState([]);
    const [jobTemplates, setJobTemplates] = useState([]);
    const [selectedTemplate, setSelectedTemplate] = useState("");
    const [useTemplate, setUseTemplate] = useState(false);
    const [formData, setFormData] = useState({
        company: "",
        jobTitle: "",
        employmentType: "Full-time",
        location: "",
        securityClearance: "",
        listedBenefits: "",
        benefitsText: "",
        headline: "",
        shortSummary: "",
        fullText: "",
        mustHaveSkills: "",
        niceToHaveSkills: "",
        careerProfilePath: "career_profile.json",
        template: "awesome-cv",
        outputBackend: "weasyprint",
        priority: 5,
        enableUploads: true,
    });

    useEffect(() => {
        fetchProfiles();
        fetchJobTemplates();
    }, []);

    const fetchProfiles = async () => {
        try {
            const response = await apiService.listProfiles();
            setProfiles(response.data.profiles || []);
        } catch (error) {
            console.error("Failed to fetch profiles:", error);
        }
    };

    const fetchJobTemplates = async () => {
        try {
            const response = await apiService.listJobTemplates();
            setJobTemplates(response.data.templates || []);
        } catch (error) {
            console.error("Failed to fetch job templates:", error);
        }
    };

    const handleTemplateSelection = async (templateName) => {
        if (!templateName) {
            setSelectedTemplate("");
            setUseTemplate(false);
            return;
        }

        setSelectedTemplate(templateName);
        setUseTemplate(true);

        // Optionally fetch and preview template details
        try {
            const response = await apiService.getJobTemplate(templateName);
            const templateData = response.data;

            // Pre-populate form fields from template for preview
            setFormData((prev) => ({
                ...prev,
                company: templateData.job_details?.company || "",
                jobTitle: templateData.job_details?.job_title || "",
                employmentType:
                    templateData.job_details?.employment_type || "Full-time",
                location: templateData.job_details?.location || "",
                securityClearance:
                    templateData.job_details?.security_clearance_required || "",
                listedBenefits:
                    templateData.benefits?.listed_benefits?.join(", ") || "",
                benefitsText: templateData.benefits?.benefits_text || "",
                headline: templateData.job_description?.headline || "",
                shortSummary: templateData.job_description?.short_summary || "",
                fullText: templateData.job_description?.full_text || "",
                mustHaveSkills:
                    templateData.job_description?.must_have_skills?.join(
                        ", ",
                    ) || "",
                niceToHaveSkills:
                    templateData.job_description?.nice_to_have_skills?.join(
                        ", ",
                    ) || "",
            }));
        } catch (error) {
            console.error("Failed to fetch template details:", error);
        }
    };

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData((prev) => ({
            ...prev,
            [name]: type === "checkbox" ? checked : value,
        }));
        // Clear error when user starts typing
        if (errors[name]) {
            setErrors((prev) => ({ ...prev, [name]: null }));
        }
    };

    const validateForm = () => {
        const newErrors = {};

        if (!formData.company.trim()) newErrors.company = "Company is required";
        if (!formData.jobTitle.trim())
            newErrors.jobTitle = "Job title is required";
        if (!formData.fullText.trim())
            newErrors.fullText = "Job description is required";
        else if (formData.fullText.trim().length < 50) {
            newErrors.fullText =
                "Job description must be at least 50 characters";
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!validateForm()) {
            return;
        }

        try {
            setSubmitting(true);

            let jobData;

            if (useTemplate && selectedTemplate) {
                // Submit using existing template file
                jobData = {
                    job_template_path: selectedTemplate,
                    career_profile_path: formData.careerProfilePath,
                    template: formData.template,
                    output_backend: formData.outputBackend,
                    priority: parseInt(formData.priority),
                    enable_uploads: formData.enableUploads,
                };
            } else {
                // Submit with full job data from form
                jobData = {
                    job_data: {
                        job_details: {
                            company: formData.company,
                            job_title: formData.jobTitle,
                            employment_type: formData.employmentType,
                            location: formData.location,
                            security_clearance_required:
                                formData.securityClearance || null,
                        },
                        benefits: {
                            listed_benefits: formData.listedBenefits
                                ? formData.listedBenefits
                                      .split(",")
                                      .map((s) => s.trim())
                                : [],
                            benefits_text: formData.benefitsText,
                        },
                        job_description: {
                            headline: formData.headline,
                            short_summary: formData.shortSummary,
                            full_text: formData.fullText,
                            must_have_skills: formData.mustHaveSkills
                                ? formData.mustHaveSkills
                                      .split(",")
                                      .map((s) => s.trim())
                                : [],
                            nice_to_have_skills: formData.niceToHaveSkills
                                ? formData.niceToHaveSkills
                                      .split(",")
                                      .map((s) => s.trim())
                                : [],
                        },
                    },
                    career_profile_path: formData.careerProfilePath,
                    template: formData.template,
                    output_backend: formData.outputBackend,
                    priority: parseInt(formData.priority),
                    enable_uploads: formData.enableUploads,
                };
            }

            const response = await apiService.submitJob(jobData);
            const jobId = response.data.job_id;

            // Navigate to job detail page
            navigate(`/jobs/${jobId}`);
        } catch (error) {
            console.error("Job submission failed:", error);
            const errorMessage =
                error.response?.data?.message || "Failed to submit job";
            setErrors({ submit: errorMessage });
        } finally {
            setSubmitting(false);
        }
    };

    const parseJobDescription = () => {
        // Simple parser to extract company and title from pasted text
        const lines = formData.fullText.split("\n");
        if (lines.length >= 2 && !formData.company && !formData.jobTitle) {
            setFormData((prev) => ({
                ...prev,
                company: lines[0].trim(),
                jobTitle: lines[1].trim(),
            }));
        }
    };

    return (
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                    Create New Resume
                </h1>
                <p className="text-gray-600 dark:text-gray-400 mt-1">
                    Fill in the job details to generate a tailored resume
                </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-8">
                {/* Template Selection Section */}
                <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                    <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
                        Job Source
                    </h2>

                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                Use Existing Job Template (Optional)
                            </label>
                            <select
                                value={selectedTemplate}
                                onChange={(e) =>
                                    handleTemplateSelection(e.target.value)
                                }
                                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                            >
                                <option value="">
                                    -- Create New Job (Fill Form Below) --
                                </option>
                                {jobTemplates.map((template) => (
                                    <option key={template} value={template}>
                                        {template
                                            .replace(".json", "")
                                            .replace(/_/g, " ")}
                                    </option>
                                ))}
                            </select>
                            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                                {useTemplate
                                    ? "Using template as starting point. You can still adjust configuration below."
                                    : "Select a template or fill out the form below to create a new job."}
                            </p>
                        </div>
                    </div>
                </div>

                {/* Job Details Section - Show only if not using template */}
                {!useTemplate && (
                    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
                            Job Details
                        </h2>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    Company *
                                </label>
                                <input
                                    type="text"
                                    name="company"
                                    value={formData.company}
                                    onChange={handleChange}
                                    className={`w-full px-4 py-2 border rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent ${
                                        errors.company
                                            ? "border-red-500"
                                            : "border-gray-300 dark:border-gray-600"
                                    }`}
                                    placeholder="Acme Corp"
                                />
                                {errors.company && (
                                    <p className="text-red-500 text-sm mt-1">
                                        {errors.company}
                                    </p>
                                )}
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    Job Title *
                                </label>
                                <input
                                    type="text"
                                    name="jobTitle"
                                    value={formData.jobTitle}
                                    onChange={handleChange}
                                    className={`w-full px-4 py-2 border rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent ${
                                        errors.jobTitle
                                            ? "border-red-500"
                                            : "border-gray-300 dark:border-gray-600"
                                    }`}
                                    placeholder="Senior Software Engineer"
                                />
                                {errors.jobTitle && (
                                    <p className="text-red-500 text-sm mt-1">
                                        {errors.jobTitle}
                                    </p>
                                )}
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    Employment Type
                                </label>
                                <select
                                    name="employmentType"
                                    value={formData.employmentType}
                                    onChange={handleChange}
                                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                >
                                    <option value="Full-time">Full-time</option>
                                    <option value="Part-time">Part-time</option>
                                    <option value="Contract">Contract</option>
                                    <option value="Freelance">Freelance</option>
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    Location
                                </label>
                                <input
                                    type="text"
                                    name="location"
                                    value={formData.location}
                                    onChange={handleChange}
                                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                    placeholder="Remote, San Francisco, etc."
                                />
                            </div>
                        </div>
                    </div>
                )}

                {/* Job Description Section - Show only if not using template */}
                {!useTemplate && (
                    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
                            Job Description
                        </h2>

                        <div className="space-y-4">
                            <div>
                                <div className="flex items-center justify-between mb-1">
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                                        Full Job Description *
                                    </label>
                                    <span className="text-xs text-gray-500 dark:text-gray-400">
                                        {formData.fullText.length} / 50 min
                                    </span>
                                </div>
                                <textarea
                                    name="fullText"
                                    value={formData.fullText}
                                    onChange={handleChange}
                                    onBlur={parseJobDescription}
                                    rows={12}
                                    className={`w-full px-4 py-2 border rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent font-mono text-sm ${
                                        errors.fullText
                                            ? "border-red-500"
                                            : "border-gray-300 dark:border-gray-600"
                                    }`}
                                    placeholder="Paste the complete job posting here..."
                                />
                                {errors.fullText && (
                                    <p className="text-red-500 text-sm mt-1">
                                        {errors.fullText}
                                    </p>
                                )}
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    Must-Have Skills (comma-separated)
                                </label>
                                <input
                                    type="text"
                                    name="mustHaveSkills"
                                    value={formData.mustHaveSkills}
                                    onChange={handleChange}
                                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                    placeholder="Python, AWS, Docker"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    Nice-to-Have Skills (comma-separated)
                                </label>
                                <input
                                    type="text"
                                    name="niceToHaveSkills"
                                    value={formData.niceToHaveSkills}
                                    onChange={handleChange}
                                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                    placeholder="Kubernetes, Terraform"
                                />
                            </div>
                        </div>
                    </div>
                )}

                {/* Configuration Section - Always shown */}
                <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                    <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
                        Resume Configuration
                    </h2>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                Career Profile
                            </label>
                            <select
                                name="careerProfilePath"
                                value={formData.careerProfilePath}
                                onChange={handleChange}
                                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                            >
                                {profiles.length > 0 ? (
                                    profiles.map((profile) => (
                                        <option
                                            key={profile.filename}
                                            value={profile.filename}
                                        >
                                            {profile.filename}
                                        </option>
                                    ))
                                ) : (
                                    <option value="career_profile.json">
                                        career_profile.json
                                    </option>
                                )}
                            </select>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                Output Backend
                            </label>
                            <select
                                name="outputBackend"
                                value={formData.outputBackend}
                                onChange={handleChange}
                                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                            >
                                {OUTPUT_BACKENDS.map((backend) => (
                                    <option
                                        key={backend.value}
                                        value={backend.value}
                                    >
                                        {backend.label}
                                    </option>
                                ))}
                            </select>
                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                {
                                    OUTPUT_BACKENDS.find(
                                        (b) =>
                                            b.value === formData.outputBackend,
                                    )?.description
                                }
                            </p>
                        </div>

                        {formData.outputBackend === "latex" && (
                            <div>
                                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                    LaTeX Template
                                </label>
                                <select
                                    name="template"
                                    value={formData.template}
                                    onChange={handleChange}
                                    className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                >
                                    {TEMPLATES.map((template) => (
                                        <option
                                            key={template.value}
                                            value={template.value}
                                        >
                                            {template.label}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        )}

                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                Priority (0-10)
                            </label>
                            <input
                                type="range"
                                name="priority"
                                min="0"
                                max="10"
                                value={formData.priority}
                                onChange={handleChange}
                                className="w-full"
                            />
                            <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                                <span>Low</span>
                                <span className="font-medium text-gray-900 dark:text-white">
                                    {formData.priority}
                                </span>
                                <span>High</span>
                            </div>
                        </div>
                    </div>

                    <div className="mt-4">
                        <label className="flex items-center gap-2 cursor-pointer">
                            <input
                                type="checkbox"
                                name="enableUploads"
                                checked={formData.enableUploads}
                                onChange={handleChange}
                                className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                            />
                            <span className="text-sm text-gray-700 dark:text-gray-300">
                                Enable cloud uploads (Nextcloud/MinIO)
                            </span>
                        </label>
                    </div>
                </div>

                {/* Submit Section */}
                {errors.submit && (
                    <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                        <p className="text-red-700 dark:text-red-400 text-sm">
                            {errors.submit}
                        </p>
                    </div>
                )}

                <div className="flex items-center gap-4">
                    <button
                        type="submit"
                        disabled={submitting}
                        className="px-8 py-3 bg-primary-600 hover:bg-primary-700 dark:bg-primary-500 dark:hover:bg-primary-600 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                        {submitting ? (
                            <>
                                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                                <span>Submitting...</span>
                            </>
                        ) : (
                            <>
                                <span>🚀</span>
                                <span>Generate Resume</span>
                            </>
                        )}
                    </button>

                    <button
                        type="button"
                        onClick={() => navigate("/")}
                        className="px-6 py-3 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 font-medium rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                    >
                        Cancel
                    </button>
                </div>
            </form>
        </div>
    );
}

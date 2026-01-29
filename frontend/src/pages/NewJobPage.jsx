import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { apiService } from "../services/api";

// Steps
import JobDetailsStep from "../components/wizard/JobDetailsStep";
import ProfileStep from "../components/wizard/ProfileStep";
import SettingsStep from "../components/wizard/SettingsStep";

const STEPS = [
    { id: 1, title: "Job Details", desc: "Define the target role" },
    { id: 2, title: "Career Profile", desc: "Select your experience" },
    { id: 3, title: "Configuration", desc: "Tune the pipeline" },
];

export default function NewJobPage() {
    const navigate = useNavigate();
    const [currentStep, setCurrentStep] = useState(1);
    const [loading, setLoading] = useState(false);
    const [existingJobs, setExistingJobs] = useState([]);

    // Unified Form State matching FULL schema.json
    const [formData, setFormData] = useState({
        // 1. Job Details
        job_details: {
            source: "",
            platform: "",
            job_title: "",
            company: "",
            company_rating: "",
            location: "",
            location_detail: "",
            employment_type: "Full-time",

            // Compensation
            pay_currency: "USD",
            pay_min_annual: "",
            pay_max_annual: "",
            pay_rate_type: "year",
            pay_display: "",

            // Work Model
            remote_type: "onsite",
            work_model: "onsite",
            work_model_notes: "",

            // URLs & Metadata
            job_post_url: "",
            apply_url: "",
            posting_age: "",

            // Clearance
            security_clearance_required: "",
            security_clearance_preferred: "",
        },

        // 2. Benefits
        benefits: {
            listed_benefits: [], // Array of strings
            benefits_text: "",
            eligibility_notes: "",
            relocation: "",
            sign_on_bonus: "",
        },

        // 3. Job Description
        job_description: {
            headline: "",
            short_summary: "",
            full_text: "",
            required_experience_years_min: 0,
            required_education: "",
            must_have_skills: [], // Array of strings
            nice_to_have_skills: [], // Array of strings
        },

        // Wizard Context
        profile_id: "",

        // Settings
        template: "awesome-cv",
        output_backend: "weasyprint",
        priority: 5,
        advanced_settings: {
            base_model: "gpt-4o",
            strong_model: "gpt-4o",
            temperature: 0.7,
            max_critique_loops: 1,
            min_quality_score: 8.0,
            enable_cover_letter: false,
        },
    });

    // Initial Data Fetch
    useEffect(() => {
        const fetchJobs = async () => {
            try {
                const response = await apiService.listJobs({
                    page: 1,
                    page_size: 100,
                });
                setExistingJobs(response.data.items || []);
            } catch (error) {
                console.error("Failed to load jobs", error);
            }
        };
        fetchJobs();
    }, []);

    const handleNext = () => setCurrentStep((prev) => Math.min(prev + 1, 3));
    const handleBack = () => setCurrentStep((prev) => Math.max(prev - 1, 1));

    const handleDeleteJob = async (id) => {
        if (!window.confirm("Delete this job listing?")) return;
        try {
            await apiService.deleteJob(id);
            setExistingJobs((prev) =>
                prev.filter((j) => j.id !== id && j.job_id !== id),
            );
        } catch (error) {
            console.error(error);
            alert("Failed to delete job");
        }
    };

    const handleSubmit = async () => {
        setLoading(true);
        try {
            // Helper to ensure array fields are arrays
            const ensureArray = (val) => {
                if (Array.isArray(val)) return val;
                if (typeof val === "string")
                    return val
                        .split("\n")
                        .map((s) => s.trim())
                        .filter(Boolean);
                return [];
            };

            const payload = {
                profile_id: formData.profile_id,
                job_data: {
                    job_details: formData.job_details,
                    benefits: {
                        ...formData.benefits,
                        listed_benefits: ensureArray(
                            formData.benefits.listed_benefits,
                        ),
                    },
                    job_description: {
                        ...formData.job_description,
                        must_have_skills: ensureArray(
                            formData.job_description.must_have_skills,
                        ),
                        nice_to_have_skills: ensureArray(
                            formData.job_description.nice_to_have_skills,
                        ),
                    },
                },
                template: formData.template,
                output_backend: formData.output_backend,
                priority: formData.priority,
                advanced_settings: formData.advanced_settings,
            };

            const response = await apiService.submitJob(payload);
            navigate(`/jobs/${response.data.id || response.data.job_id}`);
        } catch (error) {
            console.error(error);
            alert(error.response?.data?.detail || "Failed to submit job");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-5xl mx-auto px-4 py-8">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-6">
                    Create New Resume
                </h1>
                <div className="flex items-center justify-between relative">
                    <div className="absolute left-0 top-1/2 -translate-y-1/2 w-full h-1 bg-gray-200 dark:bg-gray-700 -z-10" />
                    {STEPS.map((step) => {
                        const isCompleted = step.id < currentStep;
                        const isCurrent = step.id === currentStep;
                        return (
                            <div
                                key={step.id}
                                className="flex flex-col items-center bg-gray-50 dark:bg-background px-4"
                            >
                                <div
                                    className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-colors mb-2 ${isCompleted ? "bg-green-500 text-white" : isCurrent ? "bg-primary-600 text-white ring-4 ring-primary-100 dark:ring-primary-900" : "bg-gray-200 dark:bg-gray-700 text-gray-500"}`}
                                >
                                    {isCompleted ? "✓" : step.id}
                                </div>
                                <span
                                    className={`text-sm font-medium ${isCurrent ? "text-primary-600 dark:text-primary-400" : "text-gray-500"}`}
                                >
                                    {step.title}
                                </span>
                            </div>
                        );
                    })}
                </div>
            </div>

            <div className="bg-white dark:bg-background-surface p-8 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
                {currentStep === 1 && (
                    <JobDetailsStep
                        formData={formData}
                        setFormData={setFormData}
                        onNext={handleNext}
                        existingJobs={existingJobs}
                        onDeleteJob={handleDeleteJob}
                    />
                )}
                {currentStep === 2 && (
                    <ProfileStep
                        formData={formData}
                        setFormData={setFormData}
                        onNext={handleNext}
                        onBack={handleBack}
                    />
                )}
                {currentStep === 3 && (
                    <SettingsStep
                        formData={formData}
                        setFormData={setFormData}
                        onSubmit={handleSubmit}
                        onBack={handleBack}
                        loading={loading}
                    />
                )}
            </div>
        </div>
    );
}

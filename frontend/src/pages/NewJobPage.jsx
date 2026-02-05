import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { apiService } from "../services/api";

// Steps
import JobDetailsStep from "../components/wizard/JobDetailsStep";
import ProfileStep from "../components/wizard/ProfileStep";
import SettingsStep from "../components/wizard/SettingsStep";

const STEPS = [
    {
        id: 1,
        title: "Job Details",
        shortTitle: "Job",
        desc: "Define the target role",
    },
    {
        id: 2,
        title: "Career Profile",
        shortTitle: "Profile",
        desc: "Select your experience",
    },
    {
        id: 3,
        title: "Configuration",
        shortTitle: "Config",
        desc: "Tune the pipeline",
    },
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
            required_experience_years_min: "",
            required_education: "",
            must_have_skills: [], // Array of strings
            nice_to_have_skills: [], // Array of strings
        },

        // 4. Career Profile Selection
        profile_id: null,
        career_profile_path: "career_profile.json",

        // 5. Settings
        template: "awesome-cv",
        output_backend: "weasyprint",
        priority: 5,

        // 6. Advanced Settings
        advanced_settings: {
            use_experimental_parser: false,
            enable_cover_letter: false,
            max_tokens: 4096,
            temperature: 0.7,
        },
    });

    useEffect(() => {
        const fetchExistingJobs = async () => {
            try {
                const response = await apiService.listJobs({
                    page: 1,
                    pageSize: 5,
                });
                setExistingJobs(response.data.items || response.data || []);
            } catch (error) {
                console.error("Failed to fetch recent jobs", error);
            }
        };

        fetchExistingJobs();
    }, []);

    const handleNext = () => {
        if (currentStep < STEPS.length) {
            setCurrentStep(currentStep + 1);
            // Scroll to top on mobile
            window.scrollTo({ top: 0, behavior: "smooth" });
        }
    };

    const handleBack = () => {
        if (currentStep > 1) {
            setCurrentStep(currentStep - 1);
            window.scrollTo({ top: 0, behavior: "smooth" });
        }
    };

    const ensureArray = (value) => {
        if (Array.isArray(value)) return value;
        if (typeof value === "string") {
            return value
                .split("\n")
                .map((s) => s.trim())
                .filter(Boolean);
        }
        return [];
    };

    const handleSubmit = async () => {
        setLoading(true);

        try {
            const payload = {
                career_profile_path: formData.career_profile_path,
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
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
            {/* Header */}
            <div className="mb-6 sm:mb-8">
                <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 dark:text-white mb-4 sm:mb-6">
                    Create New Resume
                </h1>

                {/* Progress Steps - Mobile optimized */}
                <div className="relative">
                    {/* Progress Bar Background */}
                    <div className="absolute left-0 right-0 top-5 h-1 bg-slate-200 dark:bg-background-elevated -z-10 hidden sm:block" />

                    {/* Steps */}
                    <div className="flex justify-between">
                        {STEPS.map((step) => {
                            const isCompleted = step.id < currentStep;
                            const isCurrent = step.id === currentStep;
                            return (
                                <div
                                    key={step.id}
                                    className="flex flex-col items-center flex-1 bg-slate-50 dark:bg-background px-2 sm:px-4"
                                >
                                    {/* Circle */}
                                    <div
                                        className={`w-10 h-10 sm:w-12 sm:h-12 rounded-full flex items-center justify-center font-bold text-sm transition-colors mb-2 ${
                                            isCompleted
                                                ? "bg-green-500 text-white"
                                                : isCurrent
                                                  ? "bg-primary-600 text-white ring-4 ring-primary-100 dark:ring-primary-900"
                                                  : "bg-slate-200 dark:bg-background-elevated text-slate-500"
                                        }`}
                                    >
                                        {isCompleted ? "✓" : step.id}
                                    </div>

                                    {/* Title - Responsive */}
                                    <span
                                        className={`text-xs sm:text-sm font-medium text-center ${
                                            isCurrent
                                                ? "text-primary-600 dark:text-primary-400"
                                                : "text-slate-600 dark:text-slate-400"
                                        }`}
                                    >
                                        <span className="hidden sm:inline">
                                            {step.title}
                                        </span>
                                        <span className="sm:hidden">
                                            {step.shortTitle}
                                        </span>
                                    </span>

                                    {/* Description - Hidden on mobile */}
                                    <span className="hidden md:block text-xs text-slate-500 dark:text-slate-500 text-center mt-1">
                                        {step.desc}
                                    </span>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>

            {/* Step Content */}
            <div className="bg-white dark:bg-background-surface rounded-lg border border-slate-200 dark:border-slate-700 p-4 sm:p-6">
                {currentStep === 1 && (
                    <JobDetailsStep
                        formData={formData}
                        setFormData={setFormData}
                        onNext={handleNext}
                        existingJobs={existingJobs}
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
                        onBack={handleBack}
                        onSubmit={handleSubmit}
                        loading={loading}
                    />
                )}
            </div>
        </div>
    );
}

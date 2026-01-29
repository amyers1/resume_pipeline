import { useState } from "react";

export default function JobDetailsStep({
    formData,
    setFormData,
    onNext,
    existingJobs,
    onDeleteJob,
}) {
    const [selectedJobId, setSelectedJobId] = useState("");
    const [openSection, setOpenSection] = useState("core"); // core, compensation, work_model, clearance, benefits, description

    const toggleSection = (section) => {
        setOpenSection(openSection === section ? "" : section);
    };

    // Generic updaters
    const updateDetails = (key, value) => {
        setFormData((prev) => ({
            ...prev,
            job_details: { ...prev.job_details, [key]: value },
        }));
    };
    const updateBenefits = (key, value) => {
        setFormData((prev) => ({
            ...prev,
            benefits: { ...prev.benefits, [key]: value },
        }));
    };
    const updateDesc = (key, value) => {
        setFormData((prev) => ({
            ...prev,
            job_description: { ...prev.job_description, [key]: value },
        }));
    };

    // Helper for array fields (textarea <-> array)
    const handleArrayInput = (updater, key, value) => {
        // Store as string in UI for editing, convert on submit
        updater(key, value.split("\n"));
    };

    const handleJobSelect = (e) => {
        const jobId = e.target.value;
        setSelectedJobId(jobId);

        if (!jobId) {
            // Reset to empty defaults (omitted for brevity, assume parent handles reset or sets defaults)
            return;
        }

        const job = existingJobs.find(
            (j) => j.id === jobId || j.job_id === jobId,
        );
        if (job && job.job_description_json) {
            const jd = job.job_description_json.job_details || {};
            const bene = job.job_description_json.benefits || {};
            const desc = job.job_description_json.job_description || {};

            setFormData((prev) => ({
                ...prev,
                job_details: { ...prev.job_details, ...jd },
                benefits: { ...prev.benefits, ...bene },
                job_description: { ...prev.job_description, ...desc },
            }));
        }
    };

    const isFormValid =
        formData.job_details.company &&
        formData.job_details.job_title &&
        formData.job_description.full_text;

    const InputGroup = ({
        label,
        value,
        onChange,
        type = "text",
        placeholder,
        required,
    }) => (
        <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {label} {required && "*"}
            </label>
            <input
                type={type}
                value={value || ""}
                onChange={(e) => onChange(e.target.value)}
                className="w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-background-surface text-gray-900 dark:text-white shadow-sm focus:border-primary-500 focus:ring-primary-500"
                placeholder={placeholder}
                required={required}
            />
        </div>
    );

    const TextAreaGroup = ({
        label,
        value,
        onChange,
        rows = 3,
        placeholder,
    }) => (
        <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {label}
            </label>
            <textarea
                rows={rows}
                value={Array.isArray(value) ? value.join("\n") : value || ""}
                onChange={(e) => onChange(e.target.value)}
                className="w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-background-surface text-gray-900 dark:text-white shadow-sm focus:border-primary-500 focus:ring-primary-500 font-mono text-sm"
                placeholder={placeholder}
            />
        </div>
    );

    const SectionHeader = ({ id, title }) => (
        <button
            type="button"
            onClick={() => toggleSection(id)}
            className="w-full flex items-center justify-between py-3 px-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-left"
        >
            <span className="font-medium text-gray-900 dark:text-white">
                {title}
            </span>
            <span className="text-gray-500">
                {openSection === id ? "−" : "+"}
            </span>
        </button>
    );

    return (
        <div className="space-y-6">
            {/* Job Selector */}
            <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-100 dark:border-blue-800">
                <label className="block text-sm font-medium text-blue-900 dark:text-blue-100 mb-2">
                    Import data from existing job
                </label>
                <div className="flex gap-2">
                    <select
                        value={selectedJobId}
                        onChange={handleJobSelect}
                        className="flex-1 rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-background-surface text-gray-900 dark:text-white shadow-sm"
                    >
                        <option value="">-- Start Fresh --</option>
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
                            Delete
                        </button>
                    )}
                </div>
            </div>

            {/* 1. CORE INFO */}
            <div className="space-y-4">
                <SectionHeader id="core" title="1. Core Information" />
                {openSection === "core" && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 px-2">
                        <InputGroup
                            label="Company"
                            required
                            value={formData.job_details.company}
                            onChange={(v) => updateDetails("company", v)}
                        />
                        <InputGroup
                            label="Job Title"
                            required
                            value={formData.job_details.job_title}
                            onChange={(v) => updateDetails("job_title", v)}
                        />
                        <InputGroup
                            label="Location"
                            value={formData.job_details.location}
                            onChange={(v) => updateDetails("location", v)}
                        />
                        <InputGroup
                            label="Location Detail (Address)"
                            value={formData.job_details.location_detail}
                            onChange={(v) =>
                                updateDetails("location_detail", v)
                            }
                        />
                        <InputGroup
                            label="Posting URL"
                            value={formData.job_details.job_post_url}
                            onChange={(v) => updateDetails("job_post_url", v)}
                        />
                        <InputGroup
                            label="Apply URL"
                            value={formData.job_details.apply_url}
                            onChange={(v) => updateDetails("apply_url", v)}
                        />
                        <InputGroup
                            label="Source (e.g. Indeed)"
                            value={formData.job_details.source}
                            onChange={(v) => updateDetails("source", v)}
                        />
                        <InputGroup
                            label="Platform ID"
                            value={formData.job_details.platform}
                            onChange={(v) => updateDetails("platform", v)}
                        />
                        <InputGroup
                            label="Company Rating"
                            value={formData.job_details.company_rating}
                            onChange={(v) => updateDetails("company_rating", v)}
                        />
                        <InputGroup
                            label="Posting Age"
                            value={formData.job_details.posting_age}
                            onChange={(v) => updateDetails("posting_age", v)}
                        />
                    </div>
                )}
            </div>

            {/* 2. COMPENSATION */}
            <div className="space-y-4">
                <SectionHeader id="compensation" title="2. Compensation" />
                {openSection === "compensation" && (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 px-2">
                        <InputGroup
                            label="Display Text"
                            value={formData.job_details.pay_display}
                            onChange={(v) => updateDetails("pay_display", v)}
                            placeholder="$120k - $150k"
                        />
                        <InputGroup
                            label="Min Pay"
                            type="number"
                            value={formData.job_details.pay_min_annual}
                            onChange={(v) => updateDetails("pay_min_annual", v)}
                        />
                        <InputGroup
                            label="Max Pay"
                            type="number"
                            value={formData.job_details.pay_max_annual}
                            onChange={(v) => updateDetails("pay_max_annual", v)}
                        />
                        <InputGroup
                            label="Currency"
                            value={formData.job_details.pay_currency}
                            onChange={(v) => updateDetails("pay_currency", v)}
                        />
                        <InputGroup
                            label="Rate Type (year/hour)"
                            value={formData.job_details.pay_rate_type}
                            onChange={(v) => updateDetails("pay_rate_type", v)}
                        />
                    </div>
                )}
            </div>

            {/* 3. WORK MODEL */}
            <div className="space-y-4">
                <SectionHeader id="work_model" title="3. Work Model" />
                {openSection === "work_model" && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 px-2">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                                Remote Type
                            </label>
                            <select
                                value={formData.job_details.remote_type}
                                onChange={(e) =>
                                    updateDetails("remote_type", e.target.value)
                                }
                                className="w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-background-surface text-gray-900 dark:text-white shadow-sm"
                            >
                                <option value="onsite">On-site</option>
                                <option value="hybrid">Hybrid</option>
                                <option value="remote">Remote</option>
                            </select>
                        </div>
                        <InputGroup
                            label="Employment Type"
                            value={formData.job_details.employment_type}
                            onChange={(v) =>
                                updateDetails("employment_type", v)
                            }
                        />
                        <InputGroup
                            label="Work Model Notes"
                            value={formData.job_details.work_model_notes}
                            onChange={(v) =>
                                updateDetails("work_model_notes", v)
                            }
                        />
                    </div>
                )}
            </div>

            {/* 4. CLEARANCE */}
            <div className="space-y-4">
                <SectionHeader id="clearance" title="4. Security Clearance" />
                {openSection === "clearance" && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 px-2">
                        <InputGroup
                            label="Required Clearance"
                            value={
                                formData.job_details.security_clearance_required
                            }
                            onChange={(v) =>
                                updateDetails("security_clearance_required", v)
                            }
                        />
                        <InputGroup
                            label="Preferred Clearance"
                            value={
                                formData.job_details
                                    .security_clearance_preferred
                            }
                            onChange={(v) =>
                                updateDetails("security_clearance_preferred", v)
                            }
                        />
                    </div>
                )}
            </div>

            {/* 5. BENEFITS */}
            <div className="space-y-4">
                <SectionHeader id="benefits" title="5. Benefits" />
                {openSection === "benefits" && (
                    <div className="space-y-4 px-2">
                        <TextAreaGroup
                            label="Listed Benefits (One per line)"
                            value={formData.benefits.listed_benefits}
                            onChange={(v) =>
                                handleArrayInput(
                                    updateBenefits,
                                    "listed_benefits",
                                    v,
                                )
                            }
                            placeholder="Health Insurance&#10;401k"
                        />
                        <InputGroup
                            label="Sign-on Bonus"
                            value={formData.benefits.sign_on_bonus}
                            onChange={(v) => updateBenefits("sign_on_bonus", v)}
                        />
                        <InputGroup
                            label="Relocation"
                            value={formData.benefits.relocation}
                            onChange={(v) => updateBenefits("relocation", v)}
                        />
                        <TextAreaGroup
                            label="Benefits Text (Full Description)"
                            value={formData.benefits.benefits_text}
                            onChange={(v) => updateBenefits("benefits_text", v)}
                        />
                        <TextAreaGroup
                            label="Eligibility Notes"
                            value={formData.benefits.eligibility_notes}
                            onChange={(v) =>
                                updateBenefits("eligibility_notes", v)
                            }
                        />
                    </div>
                )}
            </div>

            {/* 6. DESCRIPTION & SKILLS */}
            <div className="space-y-4">
                <SectionHeader
                    id="description"
                    title="6. Description & Skills"
                />
                {openSection === "description" && (
                    <div className="space-y-4 px-2">
                        <InputGroup
                            label="Headline"
                            value={formData.job_description.headline}
                            onChange={(v) => updateDesc("headline", v)}
                        />
                        <TextAreaGroup
                            label="Short Summary"
                            value={formData.job_description.short_summary}
                            onChange={(v) => updateDesc("short_summary", v)}
                            rows={2}
                        />
                        <TextAreaGroup
                            label="Full Job Description *"
                            value={formData.job_description.full_text}
                            onChange={(v) => updateDesc("full_text", v)}
                            rows={12}
                            required
                        />

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <InputGroup
                                label="Min Experience (Years)"
                                type="number"
                                value={
                                    formData.job_description
                                        .required_experience_years_min
                                }
                                onChange={(v) =>
                                    updateDesc(
                                        "required_experience_years_min",
                                        v,
                                    )
                                }
                            />
                            <InputGroup
                                label="Required Education"
                                value={
                                    formData.job_description.required_education
                                }
                                onChange={(v) =>
                                    updateDesc("required_education", v)
                                }
                            />
                        </div>

                        <TextAreaGroup
                            label="Must Have Skills (One per line)"
                            value={formData.job_description.must_have_skills}
                            onChange={(v) =>
                                handleArrayInput(
                                    updateDesc,
                                    "must_have_skills",
                                    v,
                                )
                            }
                        />
                        <TextAreaGroup
                            label="Nice to Have Skills (One per line)"
                            value={formData.job_description.nice_to_have_skills}
                            onChange={(v) =>
                                handleArrayInput(
                                    updateDesc,
                                    "nice_to_have_skills",
                                    v,
                                )
                            }
                        />
                    </div>
                )}
            </div>

            <div className="flex justify-end pt-4">
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

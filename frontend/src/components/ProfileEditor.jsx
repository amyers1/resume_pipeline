import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { apiService } from "../services/api";
import { useUser } from "../contexts/UserContext";

// FIX: Moved Input components outside of ProfileEditor to prevent re-creation on render
const InputField = ({
    label,
    value,
    onChange,
    type = "text",
    placeholder,
    required = false,
    className = "",
}) => (
    <div className={className}>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {label} {required && "*"}
        </label>
        <input
            type={type}
            value={value || ""}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            required={required}
            className="w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-background-surface text-gray-900 dark:text-white shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
        />
    </div>
);

const TextAreaField = ({
    label,
    value,
    onChange,
    rows = 3,
    placeholder,
    className = "",
}) => (
    <div className={className}>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {label}
        </label>
        <textarea
            value={value || ""}
            onChange={(e) => onChange(e.target.value)}
            rows={rows}
            placeholder={placeholder}
            className="w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-background-surface text-gray-900 dark:text-white shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
        />
    </div>
);

export default function ProfileEditor() {
    const { profileId } = useParams();
    const navigate = useNavigate();
    const { currentUser, loading: userLoading } = useUser();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    // eslint-disable-next-line no-unused-vars
    const [profile, setProfile] = useState(null);
    const [formData, setFormData] = useState({
        basics: {
            name: "",
            label: "",
            email: "",
            phone: "",
            url: "",
            summary: "",
            location: {
                city: "",
                region: "",
                countryCode: "",
            },
        },
        work: [],
        education: [],
        skills: [],
        certifications: [],
        projects: [],
        awards: [],
    });

    useEffect(() => {
        if (currentUser) {
            if (profileId) {
                loadProfile();
            } else {
                setLoading(false);
            }
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [currentUser, profileId]);

    const loadProfile = async () => {
        try {
            setLoading(true);
            const response = await apiService.getProfile(
                currentUser.id,
                profileId,
            );
            setProfile(response.data);

            // Convert database format to form format
            const profileJson = response.data.profile_json || {};
            setFormData(profileJson);
        } catch (error) {
            console.error("Failed to load profile:", error);
            alert("Failed to load profile. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    const handleBasicInfoChange = (field, value) => {
        setFormData((prev) => ({
            ...prev,
            basics: {
                ...prev.basics,
                [field]: value,
            },
        }));
    };

    const handleLocationChange = (field, value) => {
        setFormData((prev) => ({
            ...prev,
            basics: {
                ...prev.basics,
                location: {
                    ...prev.basics.location,
                    [field]: value,
                },
            },
        }));
    };

    const handleSkillChange = (index, value) => {
        setFormData((prev) => {
            const newSkills = [...prev.skills];
            newSkills[index] = { name: value, level: "", keywords: [] };
            return { ...prev, skills: newSkills };
        });
    };

    const addSkill = () => {
        setFormData((prev) => ({
            ...prev,
            skills: [...prev.skills, { name: "", level: "", keywords: [] }],
        }));
    };

    const removeSkill = (index) => {
        setFormData((prev) => ({
            ...prev,
            skills: prev.skills.filter((_, i) => i !== index),
        }));
    };

    const handleWorkChange = (index, field, value) => {
        setFormData((prev) => {
            const newWork = [...prev.work];
            newWork[index] = { ...newWork[index], [field]: value };
            return { ...prev, work: newWork };
        });
    };

    const handleWorkHighlightChange = (
        workIndex,
        highlightIndex,
        field,
        value,
    ) => {
        setFormData((prev) => {
            const newWork = [...prev.work];
            const highlights = [...(newWork[workIndex].highlights || [])];
            // Ensure highlight is an object
            const currentHighlight = highlights[highlightIndex];
            const highlightObj =
                typeof currentHighlight === "string"
                    ? { description: currentHighlight, domain_tags: [] }
                    : { ...currentHighlight };
            highlightObj[field] = value;
            highlights[highlightIndex] = highlightObj;
            newWork[workIndex] = { ...newWork[workIndex], highlights };
            return { ...prev, work: newWork };
        });
    };

    const addWorkExperience = () => {
        setFormData((prev) => ({
            ...prev,
            work: [
                ...prev.work,
                {
                    name: "",
                    position: "",
                    startDate: "",
                    endDate: "",
                    summary: "",
                    highlights: [],
                },
            ],
        }));
    };

    const addWorkHighlight = (workIndex) => {
        setFormData((prev) => {
            const newWork = [...prev.work];
            newWork[workIndex].highlights = [
                ...(newWork[workIndex].highlights || []),
                { description: "", domain_tags: [] },
            ];
            return { ...prev, work: newWork };
        });
    };

    const removeWorkExperience = (index) => {
        setFormData((prev) => ({
            ...prev,
            work: prev.work.filter((_, i) => i !== index),
        }));
    };

    const removeWorkHighlight = (workIndex, highlightIndex) => {
        setFormData((prev) => {
            const newWork = [...prev.work];
            newWork[workIndex].highlights = newWork[
                workIndex
            ].highlights.filter((_, i) => i !== highlightIndex);
            return { ...prev, work: newWork };
        });
    };

    const handleEducationChange = (index, field, value) => {
        setFormData((prev) => {
            const newEducation = [...prev.education];
            newEducation[index] = { ...newEducation[index], [field]: value };
            return { ...prev, education: newEducation };
        });
    };

    const addEducation = () => {
        setFormData((prev) => ({
            ...prev,
            education: [
                ...prev.education,
                {
                    institution: "",
                    area: "",
                    studyType: "",
                    startDate: "",
                    endDate: "",
                    location: "",
                    score: "",
                    courses: [],
                },
            ],
        }));
    };

    const removeEducation = (index) => {
        setFormData((prev) => ({
            ...prev,
            education: prev.education.filter((_, i) => i !== index),
        }));
    };

    const handleCertificationChange = (index, field, value) => {
        setFormData((prev) => {
            const newCerts = [...prev.certifications];
            newCerts[index] = { ...newCerts[index], [field]: value };
            return { ...prev, certifications: newCerts };
        });
    };

    const addCertification = () => {
        setFormData((prev) => ({
            ...prev,
            certifications: [
                ...prev.certifications,
                { name: "", date: "", issuer: "", url: "" },
            ],
        }));
    };

    const removeCertification = (index) => {
        setFormData((prev) => ({
            ...prev,
            certifications: prev.certifications.filter((_, i) => i !== index),
        }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!currentUser) {
            alert("No user found. Please try refreshing the page.");
            return;
        }

        try {
            setSaving(true);

            const payload = {
                name: formData.basics.name || "Career Profile",
                profile_json: formData,
            };

            if (profileId) {
                // Update existing profile
                await apiService.updateProfile(
                    currentUser.id,
                    profileId,
                    payload,
                );
                alert("Profile updated successfully!");
            } else {
                // Create new profile
                await apiService.createProfile(currentUser.id, payload);
                alert("Profile created successfully!");
                navigate("/profiles");
            }
        } catch (error) {
            console.error("Failed to save profile:", error);
            alert("Failed to save profile. Please try again.");
        } finally {
            setSaving(false);
        }
    };

    if (userLoading || loading) {
        return (
            <div className="flex justify-center items-center min-h-screen">
                <div className="w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
        );
    }

    return (
        <div className="max-w-5xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between mb-8">
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                    {profileId ? "Edit Profile" : "Create Profile"}
                </h1>
                <button
                    onClick={() => navigate("/profiles")}
                    className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-background-surface hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                    Back to Profiles
                </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-8">
                {/* Basic Information */}
                <section className="bg-white dark:bg-background-surface shadow rounded-lg p-6">
                    <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4 border-b border-gray-200 dark:border-gray-700 pb-2">
                        Basic Information
                    </h2>
                    <div className="grid grid-cols-1 gap-y-6 gap-x-4 sm:grid-cols-2">
                        <InputField
                            label="Full Name"
                            value={formData.basics.name}
                            onChange={(v) => handleBasicInfoChange("name", v)}
                            required
                        />
                        <InputField
                            label="Professional Title"
                            value={formData.basics.label}
                            onChange={(v) => handleBasicInfoChange("label", v)}
                            placeholder="e.g. Senior Software Engineer"
                        />
                        <InputField
                            label="Email"
                            value={formData.basics.email}
                            onChange={(v) => handleBasicInfoChange("email", v)}
                            type="email"
                        />
                        <InputField
                            label="Phone"
                            value={formData.basics.phone}
                            onChange={(v) => handleBasicInfoChange("phone", v)}
                            type="tel"
                        />
                        <InputField
                            label="Website/Portfolio"
                            value={formData.basics.url}
                            onChange={(v) => handleBasicInfoChange("url", v)}
                            placeholder="https://yourwebsite.com"
                            className="sm:col-span-2"
                        />
                        <TextAreaField
                            label="Professional Summary"
                            value={formData.basics.summary}
                            onChange={(v) =>
                                handleBasicInfoChange("summary", v)
                            }
                            rows={4}
                            placeholder="A brief summary of your professional background and goals..."
                            className="sm:col-span-2"
                        />
                    </div>
                </section>

                {/* Location */}
                <section className="bg-white dark:bg-background-surface shadow rounded-lg p-6">
                    <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4 border-b border-gray-200 dark:border-gray-700 pb-2">
                        Location
                    </h2>
                    <div className="grid grid-cols-1 gap-y-6 gap-x-4 sm:grid-cols-3">
                        <InputField
                            label="City"
                            value={formData.basics.location.city}
                            onChange={(v) => handleLocationChange("city", v)}
                        />
                        <InputField
                            label="State/Region"
                            value={formData.basics.location.region}
                            onChange={(v) => handleLocationChange("region", v)}
                        />
                        <InputField
                            label="Country Code"
                            value={formData.basics.location.countryCode}
                            onChange={(v) =>
                                handleLocationChange("countryCode", v)
                            }
                            placeholder="US"
                        />
                    </div>
                </section>

                {/* Skills */}
                <section className="bg-white dark:bg-background-surface shadow rounded-lg p-6">
                    <div className="flex items-center justify-between mb-4 border-b border-gray-200 dark:border-gray-700 pb-2">
                        <h2 className="text-lg font-medium text-gray-900 dark:text-white">
                            Skills
                        </h2>
                        <button
                            type="button"
                            onClick={addSkill}
                            className="text-sm text-primary-600 dark:text-primary-400 hover:text-primary-700 font-medium"
                        >
                            + Add Skill
                        </button>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                        {formData.skills.map((skill, index) => (
                            <div
                                key={index}
                                className="flex gap-2 items-center"
                            >
                                <input
                                    type="text"
                                    value={skill.name || skill}
                                    onChange={(e) =>
                                        handleSkillChange(index, e.target.value)
                                    }
                                    placeholder="e.g. Python"
                                    className="block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-background-surface text-gray-900 dark:text-white shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                                />
                                <button
                                    type="button"
                                    onClick={() => removeSkill(index)}
                                    className="text-red-600 hover:text-red-800 p-2"
                                    title="Remove Skill"
                                >
                                    &times;
                                </button>
                            </div>
                        ))}
                        {formData.skills.length === 0 && (
                            <p className="text-sm text-gray-500 dark:text-gray-400 col-span-full">
                                No skills added yet.
                            </p>
                        )}
                    </div>
                </section>

                {/* Work Experience */}
                <section className="bg-white dark:bg-background-surface shadow rounded-lg p-6">
                    <div className="flex items-center justify-between mb-6 border-b border-gray-200 dark:border-gray-700 pb-2">
                        <h2 className="text-lg font-medium text-gray-900 dark:text-white">
                            Work Experience
                        </h2>
                        <button
                            type="button"
                            onClick={addWorkExperience}
                            className="px-3 py-1 bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300 rounded text-sm font-medium hover:bg-primary-100 dark:hover:bg-primary-900/50 transition-colors"
                        >
                            + Add Position
                        </button>
                    </div>

                    <div className="space-y-6">
                        {formData.work.map((job, index) => (
                            <div
                                key={index}
                                className="bg-gray-50 dark:bg-gray-700/30 rounded-lg p-4 relative border border-gray-200 dark:border-gray-700"
                            >
                                <button
                                    type="button"
                                    onClick={() => removeWorkExperience(index)}
                                    className="absolute top-4 right-4 text-gray-400 hover:text-red-600 transition-colors"
                                    title="Remove Position"
                                >
                                    <svg
                                        xmlns="http://www.w3.org/2000/svg"
                                        className="h-5 w-5"
                                        viewBox="0 0 20 20"
                                        fill="currentColor"
                                    >
                                        <path
                                            fillRule="evenodd"
                                            d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                                            clipRule="evenodd"
                                        />
                                    </svg>
                                </button>

                                <h3 className="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wider mb-4">
                                    Position {index + 1}
                                </h3>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                                    <InputField
                                        label="Company"
                                        value={job.name}
                                        onChange={(v) =>
                                            handleWorkChange(index, "name", v)
                                        }
                                    />
                                    <InputField
                                        label="Position"
                                        value={job.position}
                                        onChange={(v) =>
                                            handleWorkChange(
                                                index,
                                                "position",
                                                v,
                                            )
                                        }
                                    />
                                    <InputField
                                        label="Start Date"
                                        value={job.startDate}
                                        onChange={(v) =>
                                            handleWorkChange(
                                                index,
                                                "startDate",
                                                v,
                                            )
                                        }
                                        placeholder="YYYY-MM"
                                    />
                                    <InputField
                                        label="End Date"
                                        value={job.endDate}
                                        onChange={(v) =>
                                            handleWorkChange(
                                                index,
                                                "endDate",
                                                v,
                                            )
                                        }
                                        placeholder="YYYY-MM (blank for current)"
                                    />
                                </div>

                                <TextAreaField
                                    label="Summary"
                                    value={job.summary}
                                    onChange={(v) =>
                                        handleWorkChange(index, "summary", v)
                                    }
                                    rows={2}
                                    className="mb-4"
                                />

                                <div className="space-y-3">
                                    <div className="flex items-center justify-between">
                                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                                            Highlights
                                        </label>
                                        <button
                                            type="button"
                                            onClick={() =>
                                                addWorkHighlight(index)
                                            }
                                            className="text-xs text-primary-600 hover:text-primary-700 font-medium"
                                        >
                                            + Add Highlight
                                        </button>
                                    </div>
                                    {(job.highlights || []).map(
                                        (highlight, hIndex) => {
                                            const desc =
                                                typeof highlight === "string"
                                                    ? highlight
                                                    : highlight.description ||
                                                      "";
                                            const tags =
                                                typeof highlight === "string"
                                                    ? []
                                                    : highlight.domain_tags ||
                                                      [];
                                            return (
                                                <div
                                                    key={hIndex}
                                                    className="bg-white dark:bg-background-surface rounded-md p-3 border border-gray-200 dark:border-gray-600"
                                                >
                                                    <div className="flex gap-2 items-start mb-2">
                                                        <textarea
                                                            value={desc}
                                                            onChange={(e) =>
                                                                handleWorkHighlightChange(
                                                                    index,
                                                                    hIndex,
                                                                    "description",
                                                                    e.target
                                                                        .value,
                                                                )
                                                            }
                                                            rows={2}
                                                            className="flex-1 rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-background-surface text-gray-900 dark:text-white shadow-sm focus:border-primary-500 focus:ring-primary-500 text-sm"
                                                            placeholder="Achievement or responsibility..."
                                                        />
                                                        <button
                                                            type="button"
                                                            onClick={() =>
                                                                removeWorkHighlight(
                                                                    index,
                                                                    hIndex,
                                                                )
                                                            }
                                                            className="text-gray-400 hover:text-red-600 mt-2"
                                                        >
                                                            &times;
                                                        </button>
                                                    </div>
                                                    <div>
                                                        <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                                                            Tags
                                                            (comma-separated)
                                                        </label>
                                                        <input
                                                            type="text"
                                                            value={tags.join(
                                                                ", ",
                                                            )}
                                                            onChange={(e) =>
                                                                handleWorkHighlightChange(
                                                                    index,
                                                                    hIndex,
                                                                    "domain_tags",
                                                                    e.target.value
                                                                        .split(
                                                                            ",",
                                                                        )
                                                                        .map(
                                                                            (
                                                                                t,
                                                                            ) =>
                                                                                t.trim(),
                                                                        )
                                                                        .filter(
                                                                            (
                                                                                t,
                                                                            ) =>
                                                                                t,
                                                                        ),
                                                                )
                                                            }
                                                            className="w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-background-surface text-gray-900 dark:text-white shadow-sm focus:border-primary-500 focus:ring-primary-500 text-xs"
                                                            placeholder="e.g. Python, AWS, Leadership"
                                                        />
                                                    </div>
                                                </div>
                                            );
                                        },
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </section>

                {/* Education */}
                <section className="bg-white dark:bg-background-surface shadow rounded-lg p-6">
                    <div className="flex items-center justify-between mb-6 border-b border-gray-200 dark:border-gray-700 pb-2">
                        <h2 className="text-lg font-medium text-gray-900 dark:text-white">
                            Education
                        </h2>
                        <button
                            type="button"
                            onClick={addEducation}
                            className="px-3 py-1 bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300 rounded text-sm font-medium hover:bg-primary-100 dark:hover:bg-primary-900/50 transition-colors"
                        >
                            + Add Education
                        </button>
                    </div>

                    <div className="space-y-6">
                        {formData.education.map((edu, index) => (
                            <div
                                key={index}
                                className="bg-gray-50 dark:bg-gray-700/30 rounded-lg p-4 relative border border-gray-200 dark:border-gray-700"
                            >
                                <button
                                    type="button"
                                    onClick={() => removeEducation(index)}
                                    className="absolute top-4 right-4 text-gray-400 hover:text-red-600 transition-colors"
                                >
                                    <svg
                                        xmlns="http://www.w3.org/2000/svg"
                                        className="h-5 w-5"
                                        viewBox="0 0 20 20"
                                        fill="currentColor"
                                    >
                                        <path
                                            fillRule="evenodd"
                                            d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                                            clipRule="evenodd"
                                        />
                                    </svg>
                                </button>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <InputField
                                        label="Institution"
                                        value={edu.institution}
                                        onChange={(v) =>
                                            handleEducationChange(
                                                index,
                                                "institution",
                                                v,
                                            )
                                        }
                                    />
                                    <InputField
                                        label="Location"
                                        value={edu.location}
                                        onChange={(v) =>
                                            handleEducationChange(
                                                index,
                                                "location",
                                                v,
                                            )
                                        }
                                        placeholder="e.g. Boston, MA"
                                    />
                                    <InputField
                                        label="Degree Type"
                                        value={edu.studyType}
                                        onChange={(v) =>
                                            handleEducationChange(
                                                index,
                                                "studyType",
                                                v,
                                            )
                                        }
                                        placeholder="e.g. Bachelor's, Master's"
                                    />
                                    <InputField
                                        label="Field of Study"
                                        value={edu.area}
                                        onChange={(v) =>
                                            handleEducationChange(
                                                index,
                                                "area",
                                                v,
                                            )
                                        }
                                    />
                                    <InputField
                                        label="End Date"
                                        value={edu.endDate}
                                        onChange={(v) =>
                                            handleEducationChange(
                                                index,
                                                "endDate",
                                                v,
                                            )
                                        }
                                        placeholder="YYYY-MM"
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                </section>

                {/* Certifications */}
                <section className="bg-white dark:bg-background-surface shadow rounded-lg p-6">
                    <div className="flex items-center justify-between mb-6 border-b border-gray-200 dark:border-gray-700 pb-2">
                        <h2 className="text-lg font-medium text-gray-900 dark:text-white">
                            Certifications
                        </h2>
                        <button
                            type="button"
                            onClick={addCertification}
                            className="px-3 py-1 bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300 rounded text-sm font-medium hover:bg-primary-100 dark:hover:bg-primary-900/50 transition-colors"
                        >
                            + Add Certification
                        </button>
                    </div>

                    <div className="space-y-6">
                        {formData.certifications.map((cert, index) => (
                            <div
                                key={index}
                                className="bg-gray-50 dark:bg-gray-700/30 rounded-lg p-4 relative border border-gray-200 dark:border-gray-700"
                            >
                                <button
                                    type="button"
                                    onClick={() => removeCertification(index)}
                                    className="absolute top-4 right-4 text-gray-400 hover:text-red-600 transition-colors"
                                >
                                    <svg
                                        xmlns="http://www.w3.org/2000/svg"
                                        className="h-5 w-5"
                                        viewBox="0 0 20 20"
                                        fill="currentColor"
                                    >
                                        <path
                                            fillRule="evenodd"
                                            d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                                            clipRule="evenodd"
                                        />
                                    </svg>
                                </button>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <InputField
                                        label="Certification Name"
                                        value={cert.name}
                                        onChange={(v) =>
                                            handleCertificationChange(
                                                index,
                                                "name",
                                                v,
                                            )
                                        }
                                    />
                                    <InputField
                                        label="Issuer"
                                        value={cert.issuer}
                                        onChange={(v) =>
                                            handleCertificationChange(
                                                index,
                                                "issuer",
                                                v,
                                            )
                                        }
                                    />
                                    <InputField
                                        label="Date"
                                        value={cert.date}
                                        onChange={(v) =>
                                            handleCertificationChange(
                                                index,
                                                "date",
                                                v,
                                            )
                                        }
                                        placeholder="YYYY-MM"
                                    />
                                    <InputField
                                        label="URL"
                                        value={cert.url}
                                        onChange={(v) =>
                                            handleCertificationChange(
                                                index,
                                                "url",
                                                v,
                                            )
                                        }
                                        type="url"
                                    />
                                </div>
                            </div>
                        ))}
                    </div>
                </section>

                {/* Action Buttons */}
                <div className="flex items-center justify-end gap-4 pt-6 border-t border-gray-200 dark:border-gray-700">
                    <button
                        type="button"
                        onClick={() => navigate("/profiles")}
                        className="px-4 py-2 bg-white dark:bg-background-surface text-gray-700 dark:text-gray-200 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                        disabled={saving}
                    >
                        Cancel
                    </button>
                    <button
                        type="submit"
                        className="px-6 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm transition-colors"
                        disabled={saving}
                    >
                        {saving ? "Saving..." : "Save Profile"}
                    </button>
                </div>
            </form>
        </div>
    );
}

import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { apiService } from "../services/api";
import { useUser } from "../contexts/UserContext";
import "./ProfileEditor.css";

export default function ProfileEditor() {
    const { profileId } = useParams();
    const navigate = useNavigate();
    const { currentUser, loading: userLoading } = useUser();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
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

    const handleWorkHighlightChange = (workIndex, highlightIndex, value) => {
        setFormData((prev) => {
            const newWork = [...prev.work];
            const highlights = [...(newWork[workIndex].highlights || [])];
            highlights[highlightIndex] = value;
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
                "",
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
        return <div className="profile-editor loading">Loading profile...</div>;
    }

    return (
        <div className="profile-editor">
            <div className="profile-editor-header">
                <h1>{profileId ? "Edit Profile" : "Create Profile"}</h1>
                <button
                    onClick={() => navigate("/profiles")}
                    className="btn-secondary"
                >
                    Back to Profiles
                </button>
            </div>

            <form onSubmit={handleSubmit} className="profile-form">
                {/* Basic Information */}
                <section className="form-section">
                    <h2>Basic Information</h2>
                    <div className="form-row">
                        <div className="form-group">
                            <label>Full Name *</label>
                            <input
                                type="text"
                                value={formData.basics.name}
                                onChange={(e) =>
                                    handleBasicInfoChange(
                                        "name",
                                        e.target.value,
                                    )
                                }
                                required
                            />
                        </div>
                        <div className="form-group">
                            <label>Professional Title</label>
                            <input
                                type="text"
                                value={formData.basics.label}
                                onChange={(e) =>
                                    handleBasicInfoChange(
                                        "label",
                                        e.target.value,
                                    )
                                }
                                placeholder="e.g. Senior Software Engineer"
                            />
                        </div>
                    </div>

                    <div className="form-row">
                        <div className="form-group">
                            <label>Email</label>
                            <input
                                type="email"
                                value={formData.basics.email}
                                onChange={(e) =>
                                    handleBasicInfoChange(
                                        "email",
                                        e.target.value,
                                    )
                                }
                            />
                        </div>
                        <div className="form-group">
                            <label>Phone</label>
                            <input
                                type="tel"
                                value={formData.basics.phone}
                                onChange={(e) =>
                                    handleBasicInfoChange(
                                        "phone",
                                        e.target.value,
                                    )
                                }
                            />
                        </div>
                    </div>

                    <div className="form-group">
                        <label>Website/Portfolio</label>
                        <input
                            type="url"
                            value={formData.basics.url}
                            onChange={(e) =>
                                handleBasicInfoChange("url", e.target.value)
                            }
                            placeholder="https://yourwebsite.com"
                        />
                    </div>

                    <div className="form-group">
                        <label>Professional Summary</label>
                        <textarea
                            value={formData.basics.summary}
                            onChange={(e) =>
                                handleBasicInfoChange("summary", e.target.value)
                            }
                            rows={4}
                            placeholder="A brief summary of your professional background and goals..."
                        />
                    </div>
                </section>

                {/* Location */}
                <section className="form-section">
                    <h2>Location</h2>
                    <div className="form-row">
                        <div className="form-group">
                            <label>City</label>
                            <input
                                type="text"
                                value={formData.basics.location.city}
                                onChange={(e) =>
                                    handleLocationChange("city", e.target.value)
                                }
                            />
                        </div>
                        <div className="form-group">
                            <label>State/Region</label>
                            <input
                                type="text"
                                value={formData.basics.location.region}
                                onChange={(e) =>
                                    handleLocationChange(
                                        "region",
                                        e.target.value,
                                    )
                                }
                            />
                        </div>
                        <div className="form-group">
                            <label>Country Code</label>
                            <input
                                type="text"
                                value={formData.basics.location.countryCode}
                                onChange={(e) =>
                                    handleLocationChange(
                                        "countryCode",
                                        e.target.value,
                                    )
                                }
                                placeholder="US"
                                maxLength={2}
                            />
                        </div>
                    </div>
                </section>

                {/* Skills */}
                <section className="form-section">
                    <h2>Skills</h2>
                    {formData.skills.map((skill, index) => (
                        <div key={index} className="list-item">
                            <input
                                type="text"
                                value={skill.name || skill}
                                onChange={(e) =>
                                    handleSkillChange(index, e.target.value)
                                }
                                placeholder="e.g. Python, React, AWS"
                            />
                            <button
                                type="button"
                                onClick={() => removeSkill(index)}
                                className="btn-remove"
                            >
                                Remove
                            </button>
                        </div>
                    ))}
                    <button
                        type="button"
                        onClick={addSkill}
                        className="btn-add"
                    >
                        + Add Skill
                    </button>
                </section>

                {/* Work Experience */}
                <section className="form-section">
                    <h2>Work Experience</h2>
                    {formData.work.map((job, index) => (
                        <div key={index} className="nested-item">
                            <h3>Position {index + 1}</h3>
                            <div className="form-row">
                                <div className="form-group">
                                    <label>Company</label>
                                    <input
                                        type="text"
                                        value={job.name}
                                        onChange={(e) =>
                                            handleWorkChange(
                                                index,
                                                "name",
                                                e.target.value,
                                            )
                                        }
                                    />
                                </div>
                                <div className="form-group">
                                    <label>Position</label>
                                    <input
                                        type="text"
                                        value={job.position}
                                        onChange={(e) =>
                                            handleWorkChange(
                                                index,
                                                "position",
                                                e.target.value,
                                            )
                                        }
                                    />
                                </div>
                            </div>
                            <div className="form-row">
                                <div className="form-group">
                                    <label>Start Date</label>
                                    <input
                                        type="text"
                                        value={job.startDate}
                                        onChange={(e) =>
                                            handleWorkChange(
                                                index,
                                                "startDate",
                                                e.target.value,
                                            )
                                        }
                                        placeholder="YYYY-MM"
                                    />
                                </div>
                                <div className="form-group">
                                    <label>End Date</label>
                                    <input
                                        type="text"
                                        value={job.endDate}
                                        onChange={(e) =>
                                            handleWorkChange(
                                                index,
                                                "endDate",
                                                e.target.value,
                                            )
                                        }
                                        placeholder="YYYY-MM or leave blank for current"
                                    />
                                </div>
                            </div>
                            <div className="form-group">
                                <label>Summary</label>
                                <textarea
                                    value={job.summary}
                                    onChange={(e) =>
                                        handleWorkChange(
                                            index,
                                            "summary",
                                            e.target.value,
                                        )
                                    }
                                    rows={2}
                                />
                            </div>
                            <div className="highlights-section">
                                <label>Highlights/Achievements</label>
                                {(job.highlights || []).map(
                                    (highlight, hIndex) => (
                                        <div
                                            key={hIndex}
                                            className="highlight-item"
                                        >
                                            <textarea
                                                value={
                                                    typeof highlight ===
                                                    "string"
                                                        ? highlight
                                                        : highlight.description
                                                }
                                                onChange={(e) =>
                                                    handleWorkHighlightChange(
                                                        index,
                                                        hIndex,
                                                        e.target.value,
                                                    )
                                                }
                                                rows={2}
                                                placeholder="Describe an achievement or responsibility..."
                                            />
                                            <button
                                                type="button"
                                                onClick={() =>
                                                    removeWorkHighlight(
                                                        index,
                                                        hIndex,
                                                    )
                                                }
                                                className="btn-remove-small"
                                            >
                                                ×
                                            </button>
                                        </div>
                                    ),
                                )}
                                <button
                                    type="button"
                                    onClick={() => addWorkHighlight(index)}
                                    className="btn-add-small"
                                >
                                    + Add Highlight
                                </button>
                            </div>
                            <button
                                type="button"
                                onClick={() => removeWorkExperience(index)}
                                className="btn-remove"
                            >
                                Remove Position
                            </button>
                        </div>
                    ))}
                    <button
                        type="button"
                        onClick={addWorkExperience}
                        className="btn-add"
                    >
                        + Add Work Experience
                    </button>
                </section>

                {/* Education */}
                <section className="form-section">
                    <h2>Education</h2>
                    {formData.education.map((edu, index) => (
                        <div key={index} className="nested-item">
                            <h3>Education {index + 1}</h3>
                            <div className="form-row">
                                <div className="form-group">
                                    <label>Institution</label>
                                    <input
                                        type="text"
                                        value={edu.institution}
                                        onChange={(e) =>
                                            handleEducationChange(
                                                index,
                                                "institution",
                                                e.target.value,
                                            )
                                        }
                                    />
                                </div>
                                <div className="form-group">
                                    <label>Degree Type</label>
                                    <input
                                        type="text"
                                        value={edu.studyType}
                                        onChange={(e) =>
                                            handleEducationChange(
                                                index,
                                                "studyType",
                                                e.target.value,
                                            )
                                        }
                                        placeholder="e.g. Bachelor's, Master's"
                                    />
                                </div>
                            </div>
                            <div className="form-row">
                                <div className="form-group">
                                    <label>Field of Study</label>
                                    <input
                                        type="text"
                                        value={edu.area}
                                        onChange={(e) =>
                                            handleEducationChange(
                                                index,
                                                "area",
                                                e.target.value,
                                            )
                                        }
                                    />
                                </div>
                                <div className="form-group">
                                    <label>End Date</label>
                                    <input
                                        type="text"
                                        value={edu.endDate}
                                        onChange={(e) =>
                                            handleEducationChange(
                                                index,
                                                "endDate",
                                                e.target.value,
                                            )
                                        }
                                        placeholder="YYYY-MM"
                                    />
                                </div>
                            </div>
                            <button
                                type="button"
                                onClick={() => removeEducation(index)}
                                className="btn-remove"
                            >
                                Remove Education
                            </button>
                        </div>
                    ))}
                    <button
                        type="button"
                        onClick={addEducation}
                        className="btn-add"
                    >
                        + Add Education
                    </button>
                </section>

                {/* Certifications */}
                <section className="form-section">
                    <h2>Certifications</h2>
                    {formData.certifications.map((cert, index) => (
                        <div key={index} className="nested-item">
                            <div className="form-row">
                                <div className="form-group">
                                    <label>Certification Name</label>
                                    <input
                                        type="text"
                                        value={cert.name}
                                        onChange={(e) =>
                                            handleCertificationChange(
                                                index,
                                                "name",
                                                e.target.value,
                                            )
                                        }
                                    />
                                </div>
                                <div className="form-group">
                                    <label>Issuer</label>
                                    <input
                                        type="text"
                                        value={cert.issuer}
                                        onChange={(e) =>
                                            handleCertificationChange(
                                                index,
                                                "issuer",
                                                e.target.value,
                                            )
                                        }
                                    />
                                </div>
                            </div>
                            <div className="form-row">
                                <div className="form-group">
                                    <label>Date</label>
                                    <input
                                        type="text"
                                        value={cert.date}
                                        onChange={(e) =>
                                            handleCertificationChange(
                                                index,
                                                "date",
                                                e.target.value,
                                            )
                                        }
                                        placeholder="YYYY-MM"
                                    />
                                </div>
                                <div className="form-group">
                                    <label>URL</label>
                                    <input
                                        type="url"
                                        value={cert.url}
                                        onChange={(e) =>
                                            handleCertificationChange(
                                                index,
                                                "url",
                                                e.target.value,
                                            )
                                        }
                                    />
                                </div>
                            </div>
                            <button
                                type="button"
                                onClick={() => removeCertification(index)}
                                className="btn-remove"
                            >
                                Remove Certification
                            </button>
                        </div>
                    ))}
                    <button
                        type="button"
                        onClick={addCertification}
                        className="btn-add"
                    >
                        + Add Certification
                    </button>
                </section>

                {/* Submit */}
                <div className="form-actions">
                    <button
                        type="button"
                        onClick={() => navigate("/profiles")}
                        className="btn-secondary"
                        disabled={saving}
                    >
                        Cancel
                    </button>
                    <button
                        type="submit"
                        className="btn-primary"
                        disabled={saving}
                    >
                        {saving ? "Saving..." : "Save Profile"}
                    </button>
                </div>
            </form>
        </div>
    );
}

import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { apiService } from "../services/api";
import { useUser } from "../contexts/UserContext";
import "./ProfileView.css";

export default function ProfileView() {
    const { profileId } = useParams();
    const navigate = useNavigate();
    const { currentUser, loading: userLoading } = useUser();
    const [loading, setLoading] = useState(true);
    const [profile, setProfile] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (currentUser && profileId) {
            loadProfile();
        }
    }, [currentUser, profileId]);

    const loadProfile = async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await apiService.getProfile(
                currentUser.id,
                profileId,
            );
            setProfile(response.data);
        } catch (err) {
            console.error("Failed to load profile:", err);
            setError("Failed to load profile. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    if (userLoading || loading) {
        return (
            <div className="profile-view loading">
                <div className="spinner"></div>
                <p>Loading profile...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="profile-view error">
                <p>{error}</p>
                <button onClick={loadProfile} className="btn-primary">
                    Retry
                </button>
            </div>
        );
    }

    const data = profile.profile_json || {};
    const basics = data.basics || {};
    const location = basics.location || {};

    return (
        <div className="profile-view">
            <div className="profile-view-header">
                <h1>{basics.name || "Career Profile"}</h1>
                <div className="header-actions">
                    <button
                        onClick={() => navigate("/profiles")}
                        className="btn-secondary"
                    >
                        Back to List
                    </button>
                    <button
                        onClick={() => navigate(`/profiles/${profileId}/edit`)}
                        className="btn-primary"
                    >
                        Edit Profile
                    </button>
                </div>
            </div>

            <div className="profile-content">
                {/* Basic Information */}
                <section className="profile-section">
                    <h2>Basic Information</h2>
                    <div className="info-grid">
                        {basics.label && (
                            <div className="info-item">
                                <span className="label">Title:</span>
                                <span className="value">{basics.label}</span>
                            </div>
                        )}
                        {basics.email && (
                            <div className="info-item">
                                <span className="label">Email:</span>
                                <span className="value">{basics.email}</span>
                            </div>
                        )}
                        {basics.phone && (
                            <div className="info-item">
                                <span className="label">Phone:</span>
                                <span className="value">{basics.phone}</span>
                            </div>
                        )}
                        {basics.url && (
                            <div className="info-item">
                                <span className="label">Website:</span>
                                <span className="value">
                                    <a
                                        href={basics.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                    >
                                        {basics.url}
                                    </a>
                                </span>
                            </div>
                        )}
                        {(location.city || location.region) && (
                            <div className="info-item">
                                <span className="label">Location:</span>
                                <span className="value">
                                    {[location.city, location.region]
                                        .filter(Boolean)
                                        .join(", ")}
                                </span>
                            </div>
                        )}
                    </div>
                    {basics.summary && (
                        <div className="summary">
                            <h3>Professional Summary</h3>
                            <p>{basics.summary}</p>
                        </div>
                    )}
                </section>

                {/* Skills */}
                {data.skills && data.skills.length > 0 && (
                    <section className="profile-section">
                        <h2>Skills</h2>
                        <div className="skills-list">
                            {data.skills.map((skill, index) => (
                                <span key={index} className="skill-tag">
                                    {typeof skill === "string"
                                        ? skill
                                        : skill.name}
                                </span>
                            ))}
                        </div>
                    </section>
                )}

                {/* Work Experience */}
                {data.work && data.work.length > 0 && (
                    <section className="profile-section">
                        <h2>Work Experience</h2>
                        {data.work.map((job, index) => (
                            <div key={index} className="experience-item">
                                <div className="experience-header">
                                    <div>
                                        <h3>{job.position}</h3>
                                        <h4>{job.name}</h4>
                                    </div>
                                    <div className="date-range">
                                        {job.startDate} -{" "}
                                        {job.endDate || "Present"}
                                    </div>
                                </div>
                                {job.summary && (
                                    <p className="summary">{job.summary}</p>
                                )}
                                {job.highlights &&
                                    job.highlights.length > 0 && (
                                        <ul className="highlights">
                                            {job.highlights.map(
                                                (highlight, hIndex) => (
                                                    <li key={hIndex}>
                                                        {typeof highlight ===
                                                        "string"
                                                            ? highlight
                                                            : highlight.description}
                                                    </li>
                                                ),
                                            )}
                                        </ul>
                                    )}
                            </div>
                        ))}
                    </section>
                )}

                {/* Education */}
                {data.education && data.education.length > 0 && (
                    <section className="profile-section">
                        <h2>Education</h2>
                        {data.education.map((edu, index) => (
                            <div key={index} className="education-item">
                                <div className="education-header">
                                    <div>
                                        <h3>
                                            {edu.studyType} in {edu.area}
                                        </h3>
                                        <h4>{edu.institution}</h4>
                                    </div>
                                    <div className="date-range">
                                        {edu.endDate}
                                    </div>
                                </div>
                                {edu.score && (
                                    <p className="score">Score: {edu.score}</p>
                                )}
                            </div>
                        ))}
                    </section>
                )}

                {/* Certifications */}
                {data.certifications && data.certifications.length > 0 && (
                    <section className="profile-section">
                        <h2>Certifications</h2>
                        {data.certifications.map((cert, index) => (
                            <div key={index} className="certification-item">
                                <div className="cert-header">
                                    <h3>{cert.name}</h3>
                                    <span className="cert-date">
                                        {cert.date}
                                    </span>
                                </div>
                                {cert.issuer && (
                                    <p className="cert-issuer">
                                        Issued by: {cert.issuer}
                                    </p>
                                )}
                                {cert.url && (
                                    <a
                                        href={cert.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="cert-link"
                                    >
                                        View Certification
                                    </a>
                                )}
                            </div>
                        ))}
                    </section>
                )}

                {/* Projects */}
                {data.projects && data.projects.length > 0 && (
                    <section className="profile-section">
                        <h2>Projects</h2>
                        {data.projects.map((project, index) => (
                            <div key={index} className="project-item">
                                <h3>{project.name}</h3>
                                {project.description && (
                                    <p className="project-desc">
                                        {project.description}
                                    </p>
                                )}
                                {project.keywords &&
                                    project.keywords.length > 0 && (
                                        <div className="project-keywords">
                                            {project.keywords.map(
                                                (keyword, kIndex) => (
                                                    <span
                                                        key={kIndex}
                                                        className="keyword-tag"
                                                    >
                                                        {keyword}
                                                    </span>
                                                ),
                                            )}
                                        </div>
                                    )}
                                {project.url && (
                                    <a
                                        href={project.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="project-link"
                                    >
                                        View Project
                                    </a>
                                )}
                            </div>
                        ))}
                    </section>
                )}
            </div>
        </div>
    );
}

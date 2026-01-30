import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { apiService } from "../services/api";
import { useUser } from "../contexts/UserContext";

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
            <div className="flex items-center justify-center py-12">
                <div className="w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="text-center py-12">
                    <p className="text-red-600 dark:text-red-400 mb-4">
                        {error}
                    </p>
                    <button
                        onClick={loadProfile}
                        className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
                    >
                        Retry
                    </button>
                </div>
            </div>
        );
    }

    if (!profile) {
        return (
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="text-center py-12">
                    <p className="text-slate-600 dark:text-slate-400 mb-4">
                        Profile not found
                    </p>
                    <button
                        onClick={() => navigate("/profiles")}
                        className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
                    >
                        Back to Profiles
                    </button>
                </div>
            </div>
        );
    }

    const data = profile.profile_json || {};
    const basics = data.basics || {};
    const location = basics.location || {};

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {/* Header */}
            <div className="flex items-center justify-between mb-8 pb-4 border-b-2 border-slate-200 dark:border-slate-700">
                <div className="flex items-center gap-4">
                    <button
                        onClick={() => navigate("/profiles")}
                        className="px-4 py-2 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                    >
                        ← Back
                    </button>
                    <h1 className="text-3xl font-bold text-slate-900 dark:text-white">
                        {profile.name || basics.name || "Untitled Profile"}
                    </h1>
                </div>
                <button
                    onClick={() => navigate(`/profiles/${profileId}/edit`)}
                    className="px-6 py-2 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors"
                >
                    Edit Profile
                </button>
            </div>

            {/* Content */}
            <div className="bg-white dark:bg-background-surface rounded-lg shadow">
                {/* Basic Information */}
                <section className="p-8 border-b border-slate-200 dark:border-slate-700">
                    <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-6">
                        Basic Information
                    </h2>
                    <div className="grid gap-4 md:grid-cols-2">
                        {basics.name && (
                            <div>
                                <p className="text-sm text-slate-500 dark:text-slate-400">
                                    Name
                                </p>
                                <p className="text-slate-900 dark:text-white font-medium">
                                    {basics.name}
                                </p>
                            </div>
                        )}
                        {basics.label && (
                            <div>
                                <p className="text-sm text-slate-500 dark:text-slate-400">
                                    Title
                                </p>
                                <p className="text-slate-900 dark:text-white font-medium">
                                    {basics.label}
                                </p>
                            </div>
                        )}
                        {basics.email && (
                            <div>
                                <p className="text-sm text-slate-500 dark:text-slate-400">
                                    Email
                                </p>
                                <p className="text-slate-900 dark:text-white font-medium">
                                    {basics.email}
                                </p>
                            </div>
                        )}
                        {basics.phone && (
                            <div>
                                <p className="text-sm text-slate-500 dark:text-slate-400">
                                    Phone
                                </p>
                                <p className="text-slate-900 dark:text-white font-medium">
                                    {basics.phone}
                                </p>
                            </div>
                        )}
                        {basics.url && (
                            <div>
                                <p className="text-sm text-slate-500 dark:text-slate-400">
                                    Website
                                </p>
                                <a
                                    href={basics.url}
                                    className="text-primary-600 dark:text-primary-400 hover:underline font-medium"
                                >
                                    {basics.url}
                                </a>
                            </div>
                        )}
                        {(location.city || location.region) && (
                            <div>
                                <p className="text-sm text-slate-500 dark:text-slate-400">
                                    Location
                                </p>
                                <p className="text-slate-900 dark:text-white font-medium">
                                    {[
                                        location.city,
                                        location.region,
                                        location.countryCode,
                                    ]
                                        .filter(Boolean)
                                        .join(", ")}
                                </p>
                            </div>
                        )}
                    </div>
                    {basics.summary && (
                        <div className="mt-6">
                            <p className="text-sm text-slate-500 dark:text-slate-400 mb-2">
                                Summary
                            </p>
                            <p className="text-slate-900 dark:text-white leading-relaxed">
                                {basics.summary}
                            </p>
                        </div>
                    )}
                </section>

                {/* Skills */}
                {Array.isArray(data.skills) && data.skills.length > 0 && (
                    <section className="p-8 border-b border-slate-200 dark:border-slate-700">
                        <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-6">
                            Skills
                        </h2>
                        <div className="flex flex-wrap gap-2">
                            {data.skills.map((skill, index) => (
                                <span
                                    key={index}
                                    className="px-4 py-2 bg-primary-600 text-white text-sm font-medium rounded-full"
                                >
                                    {typeof skill === "string"
                                        ? skill
                                        : skill.name}
                                </span>
                            ))}
                        </div>
                    </section>
                )}

                {/* Work Experience */}
                {Array.isArray(data.work) && data.work.length > 0 && (
                    <section className="p-8 border-b border-slate-200 dark:border-slate-700">
                        <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-6">
                            Work Experience
                        </h2>
                        <div className="space-y-6">
                            {data.work.map((job, index) => (
                                <div
                                    key={index}
                                    className="p-6 bg-slate-50 dark:bg-background rounded-lg border border-slate-200 dark:border-slate-700"
                                >
                                    <div className="mb-4">
                                        <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                                            {job.position}
                                        </h3>
                                        <p className="text-primary-600 dark:text-primary-400 font-medium">
                                            {job.name}
                                        </p>
                                        <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                                            {job.startDate && (
                                                <>
                                                    {job.startDate}{" "}
                                                    {job.endDate
                                                        ? `- ${job.endDate}`
                                                        : "- Present"}
                                                </>
                                            )}
                                        </p>
                                    </div>
                                    {job.summary && (
                                        <p className="text-slate-700 dark:text-slate-300 mb-3">
                                            {job.summary}
                                        </p>
                                    )}
                                    {Array.isArray(job.highlights) &&
                                        job.highlights.length > 0 && (
                                            <div>
                                                <p className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                                                    Key Achievements:
                                                </p>
                                                <ul className="space-y-2">
                                                    {job.highlights.map(
                                                        (highlight, idx) => (
                                                            <li
                                                                key={idx}
                                                                className="flex gap-2"
                                                            >
                                                                <span className="text-primary-600 dark:text-primary-400 mt-1">
                                                                    •
                                                                </span>
                                                                <span className="text-slate-700 dark:text-slate-300">
                                                                    {typeof highlight ===
                                                                    "string"
                                                                        ? highlight
                                                                        : highlight.description}
                                                                </span>
                                                            </li>
                                                        ),
                                                    )}
                                                </ul>
                                            </div>
                                        )}
                                </div>
                            ))}
                        </div>
                    </section>
                )}

                {/* Education */}
                {Array.isArray(data.education) && data.education.length > 0 && (
                    <section className="p-8 border-b border-slate-200 dark:border-slate-700">
                        <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-6">
                            Education
                        </h2>
                        <div className="space-y-4">
                            {data.education.map((edu, index) => (
                                <div
                                    key={index}
                                    className="p-6 bg-slate-50 dark:bg-background rounded-lg border border-slate-200 dark:border-slate-700"
                                >
                                    <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                                        {edu.institution}
                                    </h3>
                                    <p className="text-primary-600 dark:text-primary-400 font-medium">
                                        {edu.studyType}{" "}
                                        {edu.area && `in ${edu.area}`}
                                    </p>
                                    {edu.endDate && (
                                        <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                                            Graduated: {edu.endDate}
                                        </p>
                                    )}
                                    {edu.score && (
                                        <p className="text-sm text-slate-600 dark:text-slate-400">
                                            GPA: {edu.score}
                                        </p>
                                    )}
                                </div>
                            ))}
                        </div>
                    </section>
                )}

                {/* Certifications */}
                {Array.isArray(data.certifications) &&
                    data.certifications.length > 0 && (
                        <section className="p-8 border-b border-slate-200 dark:border-slate-700">
                            <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-6">
                                Certifications
                            </h2>
                            <div className="space-y-4">
                                {data.certifications.map((cert, index) => (
                                    <div
                                        key={index}
                                        className="flex items-start gap-4 p-4 bg-slate-50 dark:bg-background rounded-lg border border-slate-200 dark:border-slate-700"
                                    >
                                        <span className="text-2xl">🏆</span>
                                        <div className="flex-1">
                                            <h3 className="font-semibold text-slate-900 dark:text-white">
                                                {typeof cert === "string"
                                                    ? cert
                                                    : cert.name}
                                            </h3>
                                            {typeof cert === "object" && (
                                                <>
                                                    {cert.issuer && (
                                                        <p className="text-primary-600 dark:text-primary-400">
                                                            {cert.issuer}
                                                        </p>
                                                    )}
                                                    {cert.date && (
                                                        <p className="text-sm text-slate-600 dark:text-slate-400">
                                                            {cert.date}
                                                        </p>
                                                    )}
                                                </>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </section>
                    )}

                {/* Projects */}
                {Array.isArray(data.projects) && data.projects.length > 0 && (
                    <section className="p-8">
                        <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-6">
                            Projects
                        </h2>
                        <div className="space-y-4">
                            {data.projects.map((project, index) => (
                                <div
                                    key={index}
                                    className="p-6 bg-slate-50 dark:bg-background rounded-lg border border-slate-200 dark:border-slate-700"
                                >
                                    <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
                                        {project.name}
                                    </h3>
                                    {project.description && (
                                        <p className="text-slate-700 dark:text-slate-300 mt-2">
                                            {project.description}
                                        </p>
                                    )}
                                    {project.url && (
                                        <a
                                            href={project.url}
                                            className="text-primary-600 dark:text-primary-400 hover:underline text-sm mt-2 inline-block"
                                        >
                                            View Project →
                                        </a>
                                    )}
                                </div>
                            ))}
                        </div>
                    </section>
                )}
            </div>
        </div>
    );
}

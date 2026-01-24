import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { apiService } from "../services/api";
import { useUser } from "../contexts/UserContext";

export default function ProfilesList() {
    const navigate = useNavigate();
    const { currentUser, loading: userLoading } = useUser();
    const [profiles, setProfiles] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (currentUser) {
            loadProfiles();
        }
    }, [currentUser]);

    const loadProfiles = async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await apiService.listUserProfiles(currentUser.id);
            setProfiles(response.data);
        } catch (err) {
            console.error("Failed to load profiles:", err);
            setError("Failed to load profiles. Please try again.");
        } finally {
            setLoading(false);
        }
    };

    const handleEdit = (profileId) => {
        navigate(`/profiles/${profileId}/edit`);
    };

    const handleView = (profileId) => {
        navigate(`/profiles/${profileId}`);
    };

    const handleCreateNew = () => {
        navigate("/profiles/new");
    };

    if (userLoading || loading) {
        return (
            <div className="flex flex-col items-center justify-center py-12">
                <div className="w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
                <p className="mt-4 text-gray-600 dark:text-gray-400">
                    Loading profiles...
                </p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center py-12">
                <p className="text-red-600 dark:text-red-400 mb-4">{error}</p>
                <button
                    onClick={loadProfiles}
                    className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
                >
                    Retry
                </button>
            </div>
        );
    }

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="flex items-center justify-between mb-8 pb-4 border-b-2 border-gray-200 dark:border-gray-700">
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                    Career Profiles
                </h1>
                <button
                    onClick={handleCreateNew}
                    className="px-6 py-2 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors"
                >
                    + Create New Profile
                </button>
            </div>

            {profiles.length === 0 ? (
                <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg shadow">
                    <div className="text-6xl mb-4">📄</div>
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                        No profiles yet
                    </h3>
                    <p className="text-gray-600 dark:text-gray-400 mb-6">
                        Create your first career profile to get started.
                    </p>
                    <button
                        onClick={handleCreateNew}
                        className="px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors"
                    >
                        Create Profile
                    </button>
                </div>
            ) : (
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                    {profiles.map((profile) => {
                        if (!profile || !profile.id) return null;

                        const profileJson = profile.profile_json || {};
                        const basics = profileJson.basics || {};
                        const name =
                            profile.name || basics.name || "Untitled Profile";
                        const updatedDate =
                            profile.updated_at || profile.created_at;

                        return (
                            <div
                                key={profile.id}
                                className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow hover:shadow-lg transition-shadow border border-gray-200 dark:border-gray-700"
                            >
                                <div className="mb-4 pb-4 border-b border-gray-200 dark:border-gray-700">
                                    <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                                        {name}
                                    </h3>
                                    <span className="text-sm text-gray-500 dark:text-gray-400">
                                        Updated:{" "}
                                        {updatedDate
                                            ? new Date(
                                                  updatedDate,
                                              ).toLocaleDateString()
                                            : "N/A"}
                                    </span>
                                </div>

                                <div className="space-y-2 mb-4">
                                    {basics.email && (
                                        <p className="text-sm text-gray-700 dark:text-gray-300">
                                            <strong className="text-gray-900 dark:text-white">
                                                Email:
                                            </strong>{" "}
                                            {basics.email}
                                        </p>
                                    )}
                                    {basics.phone && (
                                        <p className="text-sm text-gray-700 dark:text-gray-300">
                                            <strong className="text-gray-900 dark:text-white">
                                                Phone:
                                            </strong>{" "}
                                            {basics.phone}
                                        </p>
                                    )}
                                    {basics.label && (
                                        <p className="text-sm text-gray-700 dark:text-gray-300">
                                            <strong className="text-gray-900 dark:text-white">
                                                Title:
                                            </strong>{" "}
                                            {basics.label}
                                        </p>
                                    )}

                                    <div className="flex flex-wrap gap-2 mt-4 pt-4 border-t border-gray-100 dark:border-gray-700">
                                        <span className="text-xs px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full">
                                            {Array.isArray(profileJson.work)
                                                ? profileJson.work.length
                                                : 0}{" "}
                                            Positions
                                        </span>
                                        <span className="text-xs px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full">
                                            {Array.isArray(
                                                profileJson.education,
                                            )
                                                ? profileJson.education.length
                                                : 0}{" "}
                                            Education
                                        </span>
                                        <span className="text-xs px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full">
                                            {Array.isArray(profileJson.skills)
                                                ? profileJson.skills.length
                                                : 0}{" "}
                                            Skills
                                        </span>
                                    </div>
                                </div>

                                <div className="flex gap-3 mt-4">
                                    <button
                                        onClick={() => handleView(profile.id)}
                                        className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                                    >
                                        View
                                    </button>
                                    <button
                                        onClick={() => handleEdit(profile.id)}
                                        className="flex-1 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
                                    >
                                        Edit
                                    </button>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}

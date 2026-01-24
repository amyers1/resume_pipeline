import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { apiService } from "../services/api";
import { useUser } from "../contexts/UserContext";
import "./ProfilesList.css";

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
            <div className="profiles-list loading">
                <div className="spinner"></div>
                <p>Loading profiles...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="profiles-list error">
                <p>{error}</p>
                <button onClick={loadProfiles} className="btn-primary">
                    Retry
                </button>
            </div>
        );
    }

    return (
        <div className="profiles-list">
            <div className="profiles-header">
                <h1>Career Profiles</h1>
                <button onClick={handleCreateNew} className="btn-primary">
                    + Create New Profile
                </button>
            </div>

            {profiles.length === 0 ? (
                <div className="empty-state">
                    <p>
                        No profiles found. Create your first profile to get
                        started.
                    </p>
                    <button onClick={handleCreateNew} className="btn-primary">
                        Create Profile
                    </button>
                </div>
            ) : (
                <div className="profiles-grid">
                    {profiles.map((profile) => (
                        <div key={profile.id} className="profile-card">
                            <div className="profile-card-header">
                                <h3>{profile.name}</h3>
                                <span className="profile-date">
                                    Updated:{" "}
                                    {new Date(
                                        profile.updated_at ||
                                            profile.created_at,
                                    ).toLocaleDateString()}
                                </span>
                            </div>

                            <div className="profile-card-body">
                                {profile.profile_json?.basics?.email && (
                                    <p className="profile-info">
                                        <strong>Email:</strong>{" "}
                                        {profile.profile_json.basics.email}
                                    </p>
                                )}
                                {profile.profile_json?.basics?.phone && (
                                    <p className="profile-info">
                                        <strong>Phone:</strong>{" "}
                                        {profile.profile_json.basics.phone}
                                    </p>
                                )}
                                {profile.profile_json?.basics?.label && (
                                    <p className="profile-info">
                                        <strong>Title:</strong>{" "}
                                        {profile.profile_json.basics.label}
                                    </p>
                                )}

                                <div className="profile-stats">
                                    <span className="stat-item">
                                        {profile.profile_json?.work?.length ||
                                            0}{" "}
                                        Work Experiences
                                    </span>
                                    <span className="stat-item">
                                        {profile.profile_json?.education
                                            ?.length || 0}{" "}
                                        Education
                                    </span>
                                    <span className="stat-item">
                                        {profile.profile_json?.skills?.length ||
                                            0}{" "}
                                        Skills
                                    </span>
                                </div>
                            </div>

                            <div className="profile-card-actions">
                                <button
                                    onClick={() => handleView(profile.id)}
                                    className="btn-secondary"
                                >
                                    View
                                </button>
                                <button
                                    onClick={() => handleEdit(profile.id)}
                                    className="btn-primary"
                                >
                                    Edit
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

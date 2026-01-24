import { useState, useEffect, useRef } from "react";
import { apiService } from "../../services/api";
import { useUser } from "../../contexts/UserContext";

export default function ProfileStep({ formData, setFormData, onNext, onBack }) {
    const { currentUser, loading: userLoading } = useUser();
    const [profiles, setProfiles] = useState([]);
    const [profilePreview, setProfilePreview] = useState("");
    const [uploading, setUploading] = useState(false);
    const fileInputRef = useRef(null);

    // 1. Fetch Profiles for current user
    const loadProfiles = async () => {
        if (!currentUser) return;

        try {
            const response = await apiService.listUserProfiles(currentUser.id);
            setProfiles(response.data);
        } catch (error) {
            console.error("Failed to load profiles", error);
        }
    };

    useEffect(() => {
        if (currentUser) {
            loadProfiles();
        }
    }, [currentUser]);

    // 2. Update Preview
    useEffect(() => {
        if (formData.profile_id) {
            const profile = profiles.find((p) => p.id === formData.profile_id);
            if (profile) {
                const dataToShow = profile.profile_json || profile;
                setProfilePreview(JSON.stringify(dataToShow, null, 2));
            }
        } else {
            setProfilePreview("");
        }
    }, [formData.profile_id, profiles]);

    // 3. Handle File Import
    const handleFileUpload = async (event) => {
        const file = event.target.files[0];
        if (!file || !currentUser) return;

        setUploading(true);
        const reader = new FileReader();

        reader.onload = async (e) => {
            try {
                const jsonContent = JSON.parse(e.target.result);

                const payload = {
                    name: jsonContent.basics?.name || "Imported Profile",
                    profile_json: jsonContent,
                };

                await apiService.createProfile(currentUser.id, payload);
                await loadProfiles();
                alert("Profile imported successfully!");
            } catch (error) {
                console.error("Import failed:", error);
                alert("Failed to import profile: " + error.message);
            } finally {
                setUploading(false);
                if (fileInputRef.current) fileInputRef.current.value = "";
            }
        };

        reader.readAsText(file);
    };

    const handleManageProfiles = () => {
        window.open("/profiles", "_blank");
    };

    if (userLoading) {
        return (
            <div className="flex items-center justify-center py-12">
                <div className="w-12 h-12 border-4 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
                <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
                    <div className="flex-1">
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Select Career Profile *
                        </label>
                        <select
                            value={formData.profile_id}
                            onChange={(e) =>
                                setFormData((prev) => ({
                                    ...prev,
                                    profile_id: e.target.value,
                                }))
                            }
                            className="w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                        >
                            <option value="">-- Select Profile --</option>
                            {profiles.map((p) => (
                                <option key={p.id} value={p.id}>
                                    {p.name || "Untitled Profile"} (
                                    {new Date(
                                        p.created_at,
                                    ).toLocaleDateString()}
                                    )
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className="flex gap-2">
                        <button
                            type="button"
                            onClick={handleManageProfiles}
                            className="px-4 py-2 bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 text-sm font-medium rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors flex items-center gap-2 border border-blue-200 dark:border-blue-800"
                        >
                            ⚙️ Manage
                        </button>

                        <input
                            type="file"
                            accept=".json"
                            className="hidden"
                            ref={fileInputRef}
                            onChange={handleFileUpload}
                        />
                        <button
                            type="button"
                            onClick={() => fileInputRef.current?.click()}
                            disabled={uploading}
                            className="px-4 py-2 bg-gray-50 text-gray-700 dark:bg-gray-700 dark:text-gray-300 text-sm font-medium rounded-lg hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors flex items-center gap-2 border border-gray-200 dark:border-gray-600 disabled:opacity-50"
                        >
                            {uploading ? "Importing..." : "📂 Import JSON"}
                        </button>
                    </div>
                </div>

                <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                    Choose a profile from the database to use as the base for
                    this resume.
                </p>
            </div>

            {profilePreview && (
                <div className="mt-6">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Profile Preview
                    </label>
                    <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 max-h-80 overflow-y-auto shadow-inner">
                        <pre className="text-xs text-gray-600 dark:text-gray-400 font-mono whitespace-pre-wrap">
                            {profilePreview}
                        </pre>
                    </div>
                </div>
            )}

            <div className="flex justify-between pt-6 border-t border-gray-200 dark:border-gray-700 mt-8">
                <button
                    onClick={onBack}
                    className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors font-medium text-sm"
                >
                    ← Back
                </button>
                <button
                    onClick={onNext}
                    disabled={!formData.profile_id}
                    className="px-6 py-2 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm shadow-sm"
                >
                    Next: Pipeline Settings →
                </button>
            </div>
        </div>
    );
}

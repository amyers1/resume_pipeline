import { useState, useEffect, useRef } from "react";
import { apiService } from "../../services/api";

export default function ProfileStep({ formData, setFormData, onNext, onBack }) {
    const [profiles, setProfiles] = useState([]);
    const [profilePreview, setProfilePreview] = useState("");
    const [uploading, setUploading] = useState(false);
    const fileInputRef = useRef(null);

    // 1. Fetch Profiles
    const loadProfiles = async () => {
        try {
            const response = await apiService.listProfiles();
            setProfiles(response.data);
        } catch (error) {
            console.error("Failed to load profiles", error);
        }
    };

    useEffect(() => {
        loadProfiles();
    }, []);

    // 2. Update Preview
    useEffect(() => {
        if (formData.profile_id) {
            const profile = profiles.find((p) => p.id === formData.profile_id);
            if (profile) {
                // FIXED: Use the nested profile_json if available, or fall back to the object
                const dataToShow = profile.profile_json || profile;
                setProfilePreview(JSON.stringify(dataToShow, null, 2));
            }
        } else {
            setProfilePreview("");
        }
    }, [formData.profile_id, profiles]);

    // 3. Handle File Import (Client-side JSON Read)
    const handleFileUpload = async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        setUploading(true);
        const reader = new FileReader();

        reader.onload = async (e) => {
            try {
                // Parse JSON in browser
                const jsonContent = JSON.parse(e.target.result);

                // Get a user ID (Using the first user found, or a default)
                // In a real app, this comes from Auth Context.
                // For now, we fetch users and pick the first one.
                const usersRes = await apiService.listUsers();
                const userId = usersRes.data[0]?.id;

                if (!userId)
                    throw new Error("No user found to attach profile to.");

                // Send as JSON payload
                const payload = {
                    name: jsonContent.basics?.name || "Imported Profile",
                    profile_json: jsonContent,
                };

                await apiService.createProfile(userId, payload);

                // Refresh list and select the new one
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

    return (
        <div className="space-y-6">
            <div className="flex items-end justify-between gap-4">
                <div className="flex-1">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Select Career Profile
                    </label>
                    <select
                        value={formData.profile_id}
                        onChange={(e) =>
                            setFormData((prev) => ({
                                ...prev,
                                profile_id: e.target.value,
                            }))
                        }
                        className="w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm focus:border-primary-500 focus:ring-primary-500"
                    >
                        <option value="">-- Select Profile --</option>
                        {profiles.map((p) => (
                            <option key={p.id} value={p.id}>
                                {p.name || "Untitled Profile"} (
                                {new Date(p.created_at).toLocaleDateString()})
                            </option>
                        ))}
                    </select>
                </div>

                {/* Import Button */}
                <div>
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
                        className="px-4 py-2 bg-gray-600 text-white text-sm font-medium rounded-lg hover:bg-gray-700 transition-colors flex items-center gap-2"
                    >
                        {uploading ? "Importing..." : "📂 Import JSON"}
                    </button>
                </div>
            </div>

            <p className="text-sm text-gray-500 -mt-4">
                Choose a profile from the database or import a standard{" "}
                <code>career_profile.json</code>.
            </p>

            {/* Preview Area */}
            {profilePreview && (
                <div className="mt-4">
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Profile Preview
                    </label>
                    <div className="p-4 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 max-h-60 overflow-y-auto">
                        <pre className="text-xs text-gray-600 dark:text-gray-400 font-mono whitespace-pre-wrap">
                            {profilePreview}
                        </pre>
                    </div>
                </div>
            )}

            <div className="flex justify-between pt-4">
                <button
                    onClick={onBack}
                    className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                    ← Back
                </button>
                <button
                    onClick={onNext}
                    disabled={!formData.profile_id}
                    className="px-6 py-2 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                    Next: Pipeline Settings →
                </button>
            </div>
        </div>
    );
}

import { useState, useEffect } from "react";
import { apiService } from "../../services/api";

export default function ProfileStep({ formData, setFormData, onNext, onBack }) {
    const [profiles, setProfiles] = useState([]);
    const [profilePreview, setProfilePreview] = useState("");

    useEffect(() => {
        const loadProfiles = async () => {
            try {
                const response = await apiService.listProfiles();
                setProfiles(response.data);
            } catch (error) {
                console.error("Failed to load profiles", error);
            }
        };
        loadProfiles();
    }, []);

    // Update preview when selection changes
    useEffect(() => {
        if (formData.profile_id) {
            const profile = profiles.find((p) => p.id === formData.profile_id);
            if (profile) {
                // In a real app, you might want to fetch the full JSON details here
                // For now, we assume we might need a separate endpoint or the list returns enough
                setProfilePreview(JSON.stringify(profile, null, 2));
            }
        }
    }, [formData.profile_id, profiles]);

    const isFormValid = !!formData.profile_id;

    return (
        <div className="space-y-6">
            <div>
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
                            {p.name || "Untitled Profile"}
                        </option>
                    ))}
                </select>
                <p className="mt-1 text-sm text-gray-500">
                    Choose the experience and skills source for this resume.
                </p>
            </div>

            {/* Optional: Profile Preview Area */}
            {profilePreview && (
                <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        Profile Preview (Read-Only)
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
                    disabled={!isFormValid}
                    className="px-6 py-2 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                    Next: Pipeline Settings →
                </button>
            </div>
        </div>
    );
}

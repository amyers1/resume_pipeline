import { TEMPLATES, OUTPUT_BACKENDS } from "../../utils/constants";

export default function SettingsStep({
    formData,
    setFormData,
    onSubmit,
    onBack,
    loading,
}) {
    const updateAdvanced = (key, value) => {
        setFormData((prev) => ({
            ...prev,
            advanced_settings: {
                ...prev.advanced_settings,
                [key]: value,
            },
        }));
    };

    // Define Model Options
    const BASE_MODELS = [
        { value: "gpt-5-mini", label: "GPT-5 Mini (OpenAI)" },
        { value: "gpt-4o-mini", label: "GPT-4o Mini (OpenAI)" },
        {
            value: "gemini-3.0-flash-preview",
            label: "Gemini 3.0 Flash Preview (Google)",
        },
        { value: "gemini-2.5-flash", label: "Gemini 2.5 Flash (Google)" },
        {
            value: "gemini-2.5-flash-lite",
            label: "Gemini 2.5 Flash-Lite (Google)",
        },
    ];

    const STRONG_MODELS = [
        ...BASE_MODELS, // Include base models as options for strong model too
        { value: "gpt-5", label: "GPT-5 (OpenAI)" },
        { value: "gpt-4o", label: "GPT-4o (OpenAI)" },
        { value: "gemini-2.5-pro", label: "Gemini 2.5 Pro (Google)" },
    ];

    return (
        <div className="space-y-8">
            {/* 1. Basic Output Settings */}
            <section className="space-y-4">
                <h3 className="text-lg font-medium text-slate-900 dark:text-white border-b border-slate-200 dark:border-slate-700 pb-2">
                    Output Configuration
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                            Resume Template
                        </label>
                        <select
                            value={formData.template}
                            onChange={(e) =>
                                setFormData((prev) => ({
                                    ...prev,
                                    template: e.target.value,
                                }))
                            }
                            className="w-full rounded-md border-slate-300 dark:border-slate-600 bg-white dark:bg-background-surface text-slate-900 dark:text-white shadow-sm focus:border-primary-500 focus:ring-primary-500"
                        >
                            {TEMPLATES.map((t) => (
                                <option key={t.value} value={t.value}>
                                    {t.label}
                                </option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                            Output Format
                        </label>
                        <select
                            value={formData.output_backend}
                            onChange={(e) =>
                                setFormData((prev) => ({
                                    ...prev,
                                    output_backend: e.target.value,
                                }))
                            }
                            className="w-full rounded-md border-slate-300 dark:border-slate-600 bg-white dark:bg-background-surface text-slate-900 dark:text-white shadow-sm focus:border-primary-500 focus:ring-primary-500"
                        >
                            {OUTPUT_BACKENDS.map((b) => (
                                <option key={b.value} value={b.value}>
                                    {b.label}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>
            </section>

            {/* 2. Advanced Pipeline Settings */}
            <section className="space-y-4">
                <h3 className="text-lg font-medium text-slate-900 dark:text-white border-b border-slate-200 dark:border-slate-700 pb-2">
                    AI Pipeline Controls
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Model Selection */}
                    <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                            Base Model (Analysis & Fast Tasks)
                        </label>
                        <select
                            value={formData.advanced_settings.base_model}
                            onChange={(e) =>
                                updateAdvanced("base_model", e.target.value)
                            }
                            className="w-full rounded-md border-slate-300 dark:border-slate-600 bg-white dark:bg-background-surface text-slate-900 dark:text-white shadow-sm focus:border-primary-500 focus:ring-primary-500"
                        >
                            {BASE_MODELS.map((m) => (
                                <option key={m.value} value={m.value}>
                                    {m.label}
                                </option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                            Strong Model (Reasoning & Drafting)
                        </label>
                        <select
                            value={formData.advanced_settings.strong_model}
                            onChange={(e) =>
                                updateAdvanced("strong_model", e.target.value)
                            }
                            className="w-full rounded-md border-slate-300 dark:border-slate-600 bg-white dark:bg-background-surface text-slate-900 dark:text-white shadow-sm focus:border-primary-500 focus:ring-primary-500"
                        >
                            {STRONG_MODELS.map((m) => (
                                <option key={m.value} value={m.value}>
                                    {m.label}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Numeric Controls */}
                    <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                            Max Critique Loops (0-3)
                        </label>
                        <input
                            type="number"
                            min="0"
                            max="3"
                            value={
                                formData.advanced_settings.max_critique_loops
                            }
                            onChange={(e) =>
                                updateAdvanced(
                                    "max_critique_loops",
                                    parseInt(e.target.value),
                                )
                            }
                            className="w-full rounded-md border-slate-300 dark:border-slate-600 bg-white dark:bg-background-surface text-slate-900 dark:text-white shadow-sm focus:border-primary-500 focus:ring-primary-500"
                        />
                        <p className="text-xs text-slate-500 mt-1">
                            More loops = higher quality, slower generation.
                        </p>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                            Creativity (Temperature)
                        </label>
                        <div className="flex items-center gap-4">
                            <input
                                type="range"
                                min="0"
                                max="1"
                                step="0.1"
                                value={formData.advanced_settings.temperature}
                                onChange={(e) =>
                                    updateAdvanced(
                                        "temperature",
                                        parseFloat(e.target.value),
                                    )
                                }
                                className="flex-1 h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer dark:bg-background-elevated"
                            />
                            <span className="text-sm font-mono text-slate-900 dark:text-white w-10">
                                {formData.advanced_settings.temperature}
                            </span>
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-2 pt-2">
                    <input
                        type="checkbox"
                        id="cover_letter"
                        checked={formData.advanced_settings.enable_cover_letter}
                        onChange={(e) =>
                            updateAdvanced(
                                "enable_cover_letter",
                                e.target.checked,
                            )
                        }
                        className="rounded border-slate-300 text-primary-600 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                    />
                    <label
                        htmlFor="cover_letter"
                        className="text-sm text-slate-700 dark:text-slate-300"
                    >
                        Generate Cover Letter (Experimental)
                    </label>
                </div>
            </section>

            <div className="flex justify-between pt-6 border-t border-slate-200 dark:border-slate-700">
                <button
                    onClick={onBack}
                    className="px-4 py-2 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                >
                    ← Back
                </button>
                <button
                    onClick={onSubmit}
                    disabled={loading}
                    className="px-8 py-2 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                >
                    {loading ? (
                        <>
                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                            <span>Submitting...</span>
                        </>
                    ) : (
                        <>
                            <span>🚀</span>
                            <span>Generate Resume</span>
                        </>
                    )}
                </button>
            </div>
        </div>
    );
}

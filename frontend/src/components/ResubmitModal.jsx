import { useState, useEffect } from "react";
import {
    TEMPLATES,
    OUTPUT_BACKENDS,
    BASE_MODEL_OPTIONS,
    STRONG_MODEL_OPTIONS,
} from "../utils/constants";

// Collapsible advanced section
const AdvancedSettings = ({ config, setConfig }) => {
    const [isOpen, setIsOpen] = useState(false);

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        const val =
            type === "checkbox"
                ? checked
                : type === "range" || name === "max_critique_loops"
                  ? parseFloat(value)
                  : value;
        setConfig((prev) => ({
            ...prev,
            advanced_settings: { ...prev.advanced_settings, [name]: val },
        }));
    };

    return (
        <div className="mt-4 border-t border-slate-200 dark:border-slate-700 pt-4">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full flex items-center justify-between text-sm font-medium text-slate-600 dark:text-slate-400"
            >
                <span>Advanced Settings</span>
                <span>{isOpen ? "−" : "+"}</span>
            </button>
            {isOpen && (
                <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    {/* Model Selectors */}
                    <div className="col-span-1">
                        <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1">
                            Base Model (Analysis & Fast Tasks)
                        </label>
                        <select
                            name="base_model"
                            value={config.advanced_settings.base_model}
                            onChange={handleChange}
                            className="w-full rounded-md border-slate-300 dark:border-slate-600 bg-white dark:bg-background-surface text-slate-900 dark:text-white shadow-sm focus:border-primary-500 focus:ring-primary-500"
                        >
                            {BASE_MODEL_OPTIONS.map((m) => (
                                <option key={m.value} value={m.value}>
                                    {m.label}
                                </option>
                            ))}
                        </select>
                    </div>
                    <div className="col-span-1">
                        <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1">
                            Strong Model (Reasoning & Drafting)
                        </label>
                        <select
                            name="strong_model"
                            value={config.advanced_settings.strong_model}
                            onChange={handleChange}
                            className="w-full rounded-md border-slate-300 dark:border-slate-600 bg-white dark:bg-background-surface text-slate-900 dark:text-white shadow-sm focus:border-primary-500 focus:ring-primary-500"
                        >
                            {STRONG_MODEL_OPTIONS.map((m) => (
                                <option key={m.value} value={m.value}>
                                    {m.label}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Sliders */}
                    <div className="col-span-1">
                        <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1">
                            Creativity (Temperature)
                        </label>
                        <div className="flex items-center gap-4">
                            <input
                                type="range"
                                min="0"
                                max="1"
                                step="0.1"
                                name="temperature"
                                value={config.advanced_settings.temperature}
                                onChange={handleChange}
                                className="flex-1 h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer dark:bg-background-elevated"
                            />
                            <span className="text-sm font-mono text-slate-900 dark:text-white w-10">
                                {config.advanced_settings.temperature}
                            </span>
                        </div>
                    </div>
                    <div className="col-span-2">
                        <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1">
                            Min Quality Score:{" "}
                            {config.advanced_settings.min_quality_score?.toFixed(
                                1,
                            )}
                        </label>
                        <input
                            type="range"
                            name="min_quality_score"
                            min="6.0"
                            max="9.5"
                            step="0.1"
                            value={config.advanced_settings.min_quality_score}
                            onChange={handleChange}
                            className="w-full"
                        />
                    </div>
                    <div className="col-span-1">
                        <label className="block font-medium text-slate-700 dark:text-slate-300 mb-1">
                            Max Critique Loops (0-3)
                        </label>
                        <input
                            type="number"
                            min="0"
                            max="3"
                            value={config.advanced_settings.max_critique_loops}
                            onChange={handleChange}
                            name="max_critique_loops"
                            className="w-full rounded-md border-slate-300 dark:border-slate-600 bg-white dark:bg-background-surface text-slate-900 dark:text-white shadow-sm focus:border-primary-500 focus:ring-primary-500"
                        />
                        <p className="text-xs text-slate-500 mt-1">
                            More loops = higher quality, slower generation.
                        </p>
                    </div>

                    {/* Cover Letter Checkbox */}
                    <div className="col-span-2 flex items-center gap-2">
                        <input
                            type="checkbox"
                            name="enable_cover_letter"
                            id="enable_cover_letter"
                            checked={
                                config.advanced_settings.enable_cover_letter
                            }
                            onChange={handleChange}
                            className="rounded border-slate-300 text-primary-600 shadow-sm focus:border-primary-500 focus:ring-primary-500"
                        />
                        <label
                            htmlFor="enable_cover_letter"
                            className="text-sm text-slate-700 dark:text-slate-300"
                        >
                            Generate Cover Letter (Experimental)
                        </label>
                    </div>
                </div>
            )}
        </div>
    );
};

export default function ResubmitModal({
    job,
    onSubmit,
    onClose,
    isSubmitting,
}) {
    const [config, setConfig] = useState({
        template: job.template || "awesome-cv",
        output_backend: job.output_backend || "weasyprint",
        priority: Math.min((job.priority || 5) + 1, 10),
        advanced_settings: {
            base_model: "gpt-5-mini",
            strong_model: "gpt-5",
            temperature: 0.7,
            max_critique_loops: 1,
            min_quality_score: 8.0,
            enable_cover_letter: false,
            ...job.advanced_settings,
        },
    });

    // Update template when backend changes to avoid mismatches
    useEffect(() => {
        if (config.output_backend === "latex") {
            const currentTemplate = TEMPLATES.find(
                (t) => t.value === config.template,
            );
            if (currentTemplate?.backend !== "latex") {
                setConfig((prev) => ({ ...prev, template: "awesome-cv" }));
            }
        } else {
            setConfig((prev) => ({ ...prev, template: "resume.html.j2" }));
        }
    }, [config.output_backend]);

    const handleSubmit = () => {
        onSubmit(config);
    };

    const isLatex = config.output_backend === "latex";

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white dark:bg-background-surface rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-2xl font-bold text-slate-900 dark:text-white">
                        Regenerate Resume
                    </h2>
                    <button
                        onClick={onClose}
                        className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 text-2xl"
                    >
                        ×
                    </button>
                </div>

                <div className="space-y-4">
                    {/* Backend Selector */}
                    <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                            Output Backend
                        </label>
                        <select
                            value={config.output_backend}
                            onChange={(e) =>
                                setConfig({
                                    ...config,
                                    output_backend: e.target.value,
                                })
                            }
                            className="w-full form-select"
                        >
                            {OUTPUT_BACKENDS.map((backend) => (
                                <option
                                    key={backend.value}
                                    value={backend.value}
                                >
                                    {backend.label}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Template Selector */}
                    {isLatex && (
                        <div>
                            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                                LaTeX Template
                            </label>
                            <select
                                value={config.template}
                                onChange={(e) =>
                                    setConfig({
                                        ...config,
                                        template: e.target.value,
                                    })
                                }
                                className="w-full form-select"
                            >
                                {TEMPLATES.filter(
                                    (t) => t.backend === "latex",
                                ).map((template) => (
                                    <option
                                        key={template.value}
                                        value={template.value}
                                    >
                                        {template.label}
                                    </option>
                                ))}
                            </select>
                        </div>
                    )}

                    {/* Priority Slider */}
                    <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                            Priority: {config.priority}
                        </label>
                        <input
                            type="range"
                            min="0"
                            max="10"
                            value={config.priority}
                            onChange={(e) =>
                                setConfig({
                                    ...config,
                                    priority: parseInt(e.target.value),
                                })
                            }
                            className="w-full"
                        />
                    </div>
                </div>

                <AdvancedSettings config={config} setConfig={setConfig} />

                <div className="flex items-center gap-3 mt-8">
                    <button
                        onClick={handleSubmit}
                        disabled={isSubmitting}
                        className="flex-1 px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50"
                    >
                        {isSubmitting ? "Generating..." : "🚀 Generate Resume"}
                    </button>
                    <button
                        onClick={onClose}
                        className="flex-1 px-6 py-3 border border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 font-medium rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700"
                    >
                        Cancel
                    </button>
                </div>
            </div>
        </div>
    );
}

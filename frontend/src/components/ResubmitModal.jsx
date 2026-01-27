import { useState, useEffect } from "react";
import { TEMPLATES, OUTPUT_BACKENDS } from "../utils/constants";

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
            ...job.advanced_settings,
            enable_uploads: true,
        },
    });

    // Update template when backend changes to avoid mismatches
    useEffect(() => {
        if (config.output_backend === "latex") {
            // If current template is not a latex template, switch to a default
            const currentTemplate = TEMPLATES.find(
                (t) => t.value === config.template,
            );
            if (currentTemplate?.backend !== "latex") {
                setConfig((prev) => ({ ...prev, template: "awesome-cv" }));
            }
        } else {
            // If backend is not latex (e.g., weasyprint), ensure html template is selected
            setConfig((prev) => ({ ...prev, template: "resume.html.j2" }));
        }
    }, [config.output_backend]);

    const handleSubmit = () => {
        onSubmit(config);
    };

    const isLatex = config.output_backend === "latex";

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                        Regenerate Resume
                    </h2>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-2xl"
                    >
                        ×
                    </button>
                </div>

                {/* ... Info Box ... */}

                <div className="space-y-4">
                    {/* Backend Selector */}
                    <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Output Backend
                        </label>
                        <select
                            value={config.output_backend} // Updated variable name
                            onChange={(e) =>
                                setConfig({
                                    ...config,
                                    output_backend: e.target.value,
                                })
                            }
                            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
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
                    {config.output_backend === "latex" && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
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
                                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
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
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                            Priority (0-10)
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
                        <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                            <span>Low</span>
                            <span className="font-medium text-gray-900 dark:text-white text-base">
                                {config.priority}
                            </span>
                            <span>High</span>
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-3 mt-8">
                    <button
                        onClick={handleSubmit}
                        className="flex-1 px-6 py-3 bg-primary-600 hover:bg-primary-700 dark:bg-primary-500 dark:hover:bg-primary-600 text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
                    >
                        <span>🚀</span>
                        <span>Generate Resume</span>
                    </button>
                    <button
                        onClick={onClose}
                        className="flex-1 px-6 py-3 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 font-medium rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                    >
                        Cancel
                    </button>
                </div>
            </div>
        </div>
    );
}

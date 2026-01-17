import { useState } from 'react';
import { TEMPLATES, OUTPUT_BACKENDS } from '../utils/constants';

export default function ResubmitModal({ job, onSubmit, onClose }) {
  const [config, setConfig] = useState({
    careerProfilePath: job.career_profile_path || 'career_profile.json',
    template: job.template || 'awesome-cv',
    outputBackend: job.output_backend || 'weasyprint',
    priority: Math.min((job.priority || 5) + 1, 10), // Increase priority by 1
    enableUploads: true,
  });

  const handleSubmit = () => {
    onSubmit(config);
  };

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

        <div className="mb-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <h3 className="font-semibold text-blue-900 dark:text-blue-200 mb-1">
            Job Details
          </h3>
          <p className="text-sm text-blue-700 dark:text-blue-300">
            <strong>{job.company}</strong> - {job.job_title}
          </p>
          <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">
            This will create a new resume generation job with the same job description
            but updated configuration options.
          </p>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Career Profile
            </label>
            <input
              type="text"
              value={config.careerProfilePath}
              onChange={(e) =>
                setConfig({ ...config, careerProfilePath: e.target.value })
              }
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Output Backend
            </label>
            <select
              value={config.outputBackend}
              onChange={(e) =>
                setConfig({ ...config, outputBackend: e.target.value })
              }
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              {OUTPUT_BACKENDS.map((backend) => (
                <option key={backend.value} value={backend.value}>
                  {backend.label}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {
                OUTPUT_BACKENDS.find((b) => b.value === config.outputBackend)
                  ?.description
              }
            </p>
          </div>

          {config.outputBackend === 'latex' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                LaTeX Template
              </label>
              <select
                value={config.template}
                onChange={(e) => setConfig({ ...config, template: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              >
                {TEMPLATES.map((template) => (
                  <option key={template.value} value={template.value}>
                    {template.label}
                  </option>
                ))}
              </select>
            </div>
          )}

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
                setConfig({ ...config, priority: parseInt(e.target.value) })
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
            {config.priority > (job.priority || 5) && (
              <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                ✓ Priority increased for faster processing
              </p>
            )}
          </div>

          <div>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={config.enableUploads}
                onChange={(e) =>
                  setConfig({ ...config, enableUploads: e.target.checked })
                }
                className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Enable cloud uploads (Nextcloud/MinIO)
              </span>
            </label>
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

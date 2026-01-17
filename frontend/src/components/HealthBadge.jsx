import { useState } from 'react';
import { useApp } from '../contexts/AppContext';
import { HEALTH_COLORS } from '../utils/constants';
import { formatDate } from '../utils/helpers';

export default function HealthBadge() {
  const { state } = useApp();
  const [showDetails, setShowDetails] = useState(false);
  const { status, checks, version, lastChecked } = state.health;

  const getStatusDot = () => {
    const colors = {
      healthy: 'bg-green-500',
      degraded: 'bg-yellow-500',
      unhealthy: 'bg-red-500',
      unknown: 'bg-gray-500',
    };
    return colors[status] || colors.unknown;
  };

  const getStatusText = () => {
    return status.charAt(0).toUpperCase() + status.slice(1);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setShowDetails(!showDetails)}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
          HEALTH_COLORS[status] || 'bg-gray-100 text-gray-600'
        } hover:opacity-80`}
      >
        <span className={`w-2 h-2 rounded-full ${getStatusDot()} animate-pulse`}></span>
        <span>{getStatusText()}</span>
      </button>

      {showDetails && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setShowDetails(false)}
          ></div>

          {/* Modal */}
          <div className="absolute right-0 top-full mt-2 w-80 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 z-50 p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                System Health
              </h3>
              <button
                onClick={() => setShowDetails(false)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Status</span>
                <span className={`text-sm font-medium px-2 py-1 rounded ${HEALTH_COLORS[status]}`}>
                  {getStatusText()}
                </span>
              </div>

              {version && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Version</span>
                  <span className="text-sm text-gray-900 dark:text-gray-100">{version}</span>
                </div>
              )}

              {lastChecked && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Last Checked</span>
                  <span className="text-sm text-gray-900 dark:text-gray-100">
                    {formatDate(lastChecked.toISOString())}
                  </span>
                </div>
              )}

              <div className="border-t border-gray-200 dark:border-gray-700 pt-3">
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Component Status
                </h4>
                <div className="space-y-2">
                  {Object.entries(checks).map(([key, value]) => (
                    <div key={key} className="flex items-center justify-between">
                      <span className="text-sm text-gray-600 dark:text-gray-400 capitalize">
                        {key.replace(/_/g, ' ')}
                      </span>
                      <span className="text-sm">
                        {value ? '✅' : '❌'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

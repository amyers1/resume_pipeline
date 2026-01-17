import { PIPELINE_STAGES } from '../utils/constants';
import { formatDuration } from '../utils/helpers';

export default function StageTimeline({ currentStage, status, startedAt }) {
  const stages = Object.keys(PIPELINE_STAGES);
  const currentIndex = stages.indexOf(currentStage);

  const getStageStatus = (index) => {
    if (status === 'failed') {
      return index <= currentIndex ? 'failed' : 'pending';
    }
    if (status === 'completed') {
      return 'completed';
    }
    if (index < currentIndex) return 'completed';
    if (index === currentIndex) return 'active';
    return 'pending';
  };

  const getIcon = (stageStatus) => {
    switch (stageStatus) {
      case 'completed':
        return (
          <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center text-white">
            ✓
          </div>
        );
      case 'active':
        return (
          <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
          </div>
        );
      case 'failed':
        return (
          <div className="w-8 h-8 bg-red-500 rounded-full flex items-center justify-center text-white">
            ✕
          </div>
        );
      default:
        return (
          <div className="w-8 h-8 bg-gray-300 dark:bg-gray-600 rounded-full flex items-center justify-center">
            <div className="w-3 h-3 bg-gray-100 dark:bg-gray-800 rounded-full"></div>
          </div>
        );
    }
  };

  return (
    <div className="space-y-4">
      {stages.map((stage, index) => {
        const stageInfo = PIPELINE_STAGES[stage];
        const stageStatus = getStageStatus(index);
        const isLast = index === stages.length - 1;

        return (
          <div key={stage} className="relative">
            <div className="flex items-start gap-4">
              {/* Icon */}
              <div className="relative flex-shrink-0">
                {getIcon(stageStatus)}
                {/* Connecting line */}
                {!isLast && (
                  <div
                    className={`absolute left-1/2 top-8 w-0.5 h-8 -translate-x-1/2 ${
                      stageStatus === 'completed'
                        ? 'bg-green-500'
                        : stageStatus === 'active'
                        ? 'bg-blue-500'
                        : stageStatus === 'failed'
                        ? 'bg-red-500'
                        : 'bg-gray-300 dark:bg-gray-600'
                    }`}
                  ></div>
                )}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0 pb-8">
                <div className="flex items-start justify-between">
                  <div>
                    <p
                      className={`text-sm font-medium ${
                        stageStatus === 'active'
                          ? 'text-gray-900 dark:text-white'
                          : 'text-gray-600 dark:text-gray-400'
                      }`}
                    >
                      {stageInfo.label}
                    </p>
                    {stageStatus === 'active' && (
                      <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                        In progress...
                      </p>
                    )}
                  </div>
                  {stageStatus === 'completed' && (
                    <span className="text-xs text-gray-500 dark:text-gray-500">
                      Complete
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

import { PIPELINE_STAGES } from "../utils/constants";

export default function ProgressBar({
    percent,
    stage,
    message,
    animated = true,
}) {
    const getProgressColor = () => {
        if (percent === 100) return "bg-green-500";
        if (percent >= 70) return "bg-orange-500";
        if (percent >= 25) return "bg-purple-500";
        return "bg-blue-500";
    };

    const stageInfo = PIPELINE_STAGES[stage] || {
        label: "Processing",
        color: "#3b82f6",
    };

    return (
        <div className="w-full space-y-2">
            {/* Stage name */}
            <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                    {stageInfo.label}
                </span>
                <span className="text-sm font-semibold text-slate-900 dark:text-white">
                    {percent}%
                </span>
            </div>

            {/* Progress bar */}
            <div className="w-full h-3 bg-slate-200 dark:bg-background-elevated rounded-full overflow-hidden">
                <div
                    className={`h-full ${getProgressColor()} transition-all duration-500 ease-out ${
                        animated ? "animate-pulse-slow" : ""
                    }`}
                    style={{ width: `${percent}%` }}
                ></div>
            </div>

            {/* Current message */}
            {message && (
                <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                    {message}
                </p>
            )}
        </div>
    );
}

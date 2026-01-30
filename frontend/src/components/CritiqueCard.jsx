import PropTypes from "prop-types";

/**
 * Progress bar component for displaying percentage metrics
 */
const MetricBar = ({ label, value, colorClass = "bg-primary-500" }) => {
    const percentage = Math.round((value || 0) * 100);
    return (
        <div className="mb-3">
            <div className="flex justify-between text-sm mb-1">
                <span className="text-slate-600 dark:text-slate-400">
                    {label}
                </span>
                <span className="font-medium text-slate-900 dark:text-white">
                    {percentage}%
                </span>
            </div>
            <div className="w-full bg-slate-200 dark:bg-background-elevated rounded-full h-2">
                <div
                    className={`${colorClass} h-2 rounded-full transition-all duration-300`}
                    style={{ width: `${percentage}%` }}
                />
            </div>
        </div>
    );
};

MetricBar.propTypes = {
    label: PropTypes.string.isRequired,
    value: PropTypes.number,
    colorClass: PropTypes.string,
};

/**
 * Status indicator for boolean metrics
 */
const StatusIndicator = ({ label, ok }) => (
    <div className="flex items-center gap-2">
        <span
            className={`flex items-center justify-center w-5 h-5 rounded-full text-xs font-bold ${
                ok
                    ? "bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400"
                    : "bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400"
            }`}
        >
            {ok ? "✓" : "✗"}
        </span>
        <span className="text-sm text-slate-600 dark:text-slate-400">
            {label}
        </span>
    </div>
);

StatusIndicator.propTypes = {
    label: PropTypes.string.isRequired,
    ok: PropTypes.bool,
};

/**
 * CritiqueCard - Displays overall score and key metrics from resume critique
 */
export default function CritiqueCard({ critique, status, fallbackScore }) {
    // Handle loading/pending states
    if (!critique && status !== "completed") {
        return (
            <div className="bg-white dark:bg-background-surface rounded-lg border border-slate-200 dark:border-slate-700 p-6">
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
                    Critique Score
                </h3>
                <div className="text-center py-4">
                    <div className="text-4xl font-bold text-slate-400 dark:text-slate-500 mb-2">
                        -- / 10
                    </div>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                        {status === "processing"
                            ? "Generating critique..."
                            : status === "queued"
                              ? "Waiting in queue..."
                              : "No critique available"}
                    </p>
                </div>
            </div>
        );
    }

    // Handle completed jobs without detailed critique (backwards compatibility)
    if (!critique && status === "completed") {
        const displayScore =
            fallbackScore !== null && fallbackScore !== undefined
                ? Number(fallbackScore).toFixed(1)
                : null;
        const scoreColor =
            displayScore >= 8
                ? "text-green-600 dark:text-green-400"
                : displayScore >= 6
                  ? "text-yellow-600 dark:text-yellow-400"
                  : "text-red-600 dark:text-red-400";

        return (
            <div className="bg-white dark:bg-background-surface rounded-lg border border-slate-200 dark:border-slate-700 p-6">
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
                    Critique Score
                </h3>
                <div className="text-center py-4">
                    <div
                        className={`text-4xl font-bold ${displayScore ? scoreColor : "text-slate-400 dark:text-slate-500"} mb-2`}
                    >
                        {displayScore || "--"} / 10
                    </div>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                        {displayScore
                            ? "AI-generated quality score"
                            : "No score available"}
                    </p>
                </div>
            </div>
        );
    }

    // Calculate score display (convert from 0-1 to 0-10)
    const score = critique?.score ? (critique.score * 10).toFixed(1) : null;
    const scoreColor =
        score >= 8
            ? "text-green-600 dark:text-green-400"
            : score >= 6
              ? "text-yellow-600 dark:text-yellow-400"
              : "text-red-600 dark:text-red-400";

    // Determine bar colors based on values
    const keywordColor =
        (critique?.jd_keyword_coverage || 0) >= 0.7
            ? "bg-green-500"
            : (critique?.jd_keyword_coverage || 0) >= 0.5
              ? "bg-yellow-500"
              : "bg-red-500";

    const domainColor =
        (critique?.domain_match_coverage || 0) >= 0.6
            ? "bg-green-500"
            : (critique?.domain_match_coverage || 0) >= 0.4
              ? "bg-yellow-500"
              : "bg-red-500";

    return (
        <div className="bg-white dark:bg-background-surface rounded-lg border border-slate-200 dark:border-slate-700 p-6">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
                Critique Score
            </h3>

            {/* Main Score */}
            <div className="text-center mb-6">
                <div className={`text-4xl font-bold ${scoreColor} mb-1`}>
                    {score || "--"} / 10
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                    AI-generated quality score
                </p>
            </div>

            {/* Metric Bars */}
            <div className="space-y-1 mb-4">
                <MetricBar
                    label="Keyword Coverage"
                    value={critique?.jd_keyword_coverage}
                    colorClass={keywordColor}
                />
                <MetricBar
                    label="Domain Match"
                    value={critique?.domain_match_coverage}
                    colorClass={domainColor}
                />
            </div>

            {/* Status Indicators */}
            <div className="flex justify-between pt-4 border-t border-slate-200 dark:border-slate-700">
                <StatusIndicator label="ATS Safe" ok={critique?.ats_ok} />
                <StatusIndicator label="Length OK" ok={critique?.length_ok} />
            </div>
        </div>
    );
}

CritiqueCard.propTypes = {
    critique: PropTypes.shape({
        score: PropTypes.number,
        ats_ok: PropTypes.bool,
        length_ok: PropTypes.bool,
        jd_keyword_coverage: PropTypes.number,
        domain_match_coverage: PropTypes.number,
    }),
    status: PropTypes.string,
    fallbackScore: PropTypes.number,
};

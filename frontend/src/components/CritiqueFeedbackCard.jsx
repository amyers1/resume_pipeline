import { useState } from "react";
import PropTypes from "prop-types";

/**
 * Feedback section component for strengths/weaknesses/suggestions
 */
const FeedbackSection = ({ title, items, icon, colorClass }) => {
    if (!items?.length) return null;

    return (
        <div className="mb-4 last:mb-0">
            <h4
                className={`text-sm font-medium ${colorClass} mb-2 flex items-center gap-1.5`}
            >
                {icon}
                {title}
            </h4>
            <ul className="space-y-1.5">
                {items.map((item, index) => (
                    <li
                        key={index}
                        className="text-sm text-gray-700 dark:text-gray-300 pl-4 relative before:content-[''] before:absolute before:left-0 before:top-2 before:w-1.5 before:h-1.5 before:rounded-full before:bg-current before:opacity-40"
                    >
                        {item}
                    </li>
                ))}
            </ul>
        </div>
    );
};

FeedbackSection.propTypes = {
    title: PropTypes.string.isRequired,
    items: PropTypes.arrayOf(PropTypes.string),
    icon: PropTypes.node,
    colorClass: PropTypes.string,
};

/**
 * CritiqueFeedbackCard - Collapsible card showing strengths, weaknesses, and suggestions
 */
export default function CritiqueFeedbackCard({ critique }) {
    const [isExpanded, setIsExpanded] = useState(false);

    // Don't render if no feedback available
    const hasContent =
        critique?.strengths?.length ||
        critique?.weaknesses?.length ||
        critique?.suggestions?.length;

    if (!hasContent) {
        return null;
    }

    return (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
            {/* Header - Always visible */}
            <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
            >
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Critique Feedback
                </h3>
                <svg
                    className={`w-5 h-5 text-gray-500 transition-transform duration-200 ${
                        isExpanded ? "rotate-180" : ""
                    }`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 9l-7 7-7-7"
                    />
                </svg>
            </button>

            {/* Expandable Content */}
            <div
                className={`transition-all duration-200 ease-in-out ${
                    isExpanded
                        ? "max-h-[800px] opacity-100"
                        : "max-h-0 opacity-0 overflow-hidden"
                }`}
            >
                <div className="px-6 pb-4 border-t border-gray-200 dark:border-gray-700 pt-4">
                    {/* Strengths */}
                    <FeedbackSection
                        title="Strengths"
                        items={critique?.strengths}
                        colorClass="text-green-600 dark:text-green-400"
                        icon={
                            <svg
                                className="w-4 h-4"
                                fill="currentColor"
                                viewBox="0 0 20 20"
                            >
                                <path
                                    fillRule="evenodd"
                                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                                    clipRule="evenodd"
                                />
                            </svg>
                        }
                    />

                    {/* Weaknesses */}
                    <FeedbackSection
                        title="Areas to Improve"
                        items={critique?.weaknesses}
                        colorClass="text-yellow-600 dark:text-yellow-400"
                        icon={
                            <svg
                                className="w-4 h-4"
                                fill="currentColor"
                                viewBox="0 0 20 20"
                            >
                                <path
                                    fillRule="evenodd"
                                    d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                                    clipRule="evenodd"
                                />
                            </svg>
                        }
                    />

                    {/* Suggestions */}
                    <FeedbackSection
                        title="Suggestions"
                        items={critique?.suggestions}
                        colorClass="text-blue-600 dark:text-blue-400"
                        icon={
                            <svg
                                className="w-4 h-4"
                                fill="currentColor"
                                viewBox="0 0 20 20"
                            >
                                <path
                                    fillRule="evenodd"
                                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                                    clipRule="evenodd"
                                />
                            </svg>
                        }
                    />
                </div>
            </div>

            {/* Preview when collapsed */}
            {!isExpanded && (
                <div className="px-6 pb-4 text-sm text-gray-500 dark:text-gray-400">
                    {critique?.strengths?.length > 0 && (
                        <span className="text-green-600 dark:text-green-400">
                            {critique.strengths.length} strengths
                        </span>
                    )}
                    {critique?.weaknesses?.length > 0 && (
                        <>
                            {critique?.strengths?.length > 0 && " · "}
                            <span className="text-yellow-600 dark:text-yellow-400">
                                {critique.weaknesses.length} improvements
                            </span>
                        </>
                    )}
                    {critique?.suggestions?.length > 0 && (
                        <>
                            {(critique?.strengths?.length > 0 ||
                                critique?.weaknesses?.length > 0) &&
                                " · "}
                            <span className="text-blue-600 dark:text-blue-400">
                                {critique.suggestions.length} suggestions
                            </span>
                        </>
                    )}
                </div>
            )}
        </div>
    );
}

CritiqueFeedbackCard.propTypes = {
    critique: PropTypes.shape({
        strengths: PropTypes.arrayOf(PropTypes.string),
        weaknesses: PropTypes.arrayOf(PropTypes.string),
        suggestions: PropTypes.arrayOf(PropTypes.string),
    }),
};

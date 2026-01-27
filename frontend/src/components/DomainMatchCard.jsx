import PropTypes from "prop-types";

/**
 * Domain tag pill component
 */
const DomainTag = ({ name, matched = false, required = false }) => {
    let baseClasses =
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium mr-1.5 mb-1.5";

    if (required && matched) {
        // Required and matched - green
        baseClasses +=
            " bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400";
    } else if (required && !matched) {
        // Required but not matched - red/muted
        baseClasses +=
            " bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400";
    } else if (matched) {
        // User has this domain (extra coverage)
        baseClasses +=
            " bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400";
    } else {
        // Not matched
        baseClasses +=
            " bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400";
    }

    return (
        <span className={baseClasses}>
            {matched && required && (
                <svg
                    className="w-3 h-3 mr-1"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                >
                    <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                    />
                </svg>
            )}
            {!matched && required && (
                <svg
                    className="w-3 h-3 mr-1"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                >
                    <path
                        fillRule="evenodd"
                        d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                        clipRule="evenodd"
                    />
                </svg>
            )}
            {name.replace(/_/g, " ")}
        </span>
    );
};

DomainTag.propTypes = {
    name: PropTypes.string.isRequired,
    matched: PropTypes.bool,
    required: PropTypes.bool,
};

/**
 * DomainMatchCard - Shows domain alignment between JD requirements and user profile
 */
export default function DomainMatchCard({ jdRequirements, critique }) {
    // If no JD requirements, don't render
    if (!jdRequirements?.domain_focus?.length) {
        return null;
    }

    const requiredDomains = jdRequirements.domain_focus || [];
    const coverage = critique?.domain_match_coverage || 0;
    const matchedCount = Math.round(coverage * requiredDomains.length);

    // Determine which domains are matched (approximation based on coverage)
    // In a real implementation, you'd have actual matched domains from backend
    const matchedDomains = new Set(requiredDomains.slice(0, matchedCount));

    return (
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Domain Alignment
                </h3>
                <span
                    className={`text-sm font-medium px-2 py-1 rounded ${
                        coverage >= 0.6
                            ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
                            : coverage >= 0.4
                              ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400"
                              : "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400"
                    }`}
                >
                    {Math.round(coverage * 100)}% Match
                </span>
            </div>

            {/* Required Domains */}
            <div className="mb-4">
                <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                    Required Domains ({requiredDomains.length})
                </p>
                <div className="flex flex-wrap">
                    {requiredDomains.map((domain) => (
                        <DomainTag
                            key={domain}
                            name={domain}
                            required={true}
                            matched={matchedDomains.has(domain)}
                        />
                    ))}
                </div>
            </div>

            {/* Skills Summary */}
            {(jdRequirements.must_have_skills?.length > 0 ||
                jdRequirements.nice_to_have_skills?.length > 0) && (
                <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                    <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                        Key Skills
                    </p>

                    {jdRequirements.must_have_skills?.length > 0 && (
                        <div className="mb-2">
                            <span className="text-xs text-gray-500 dark:text-gray-400">
                                Must-have:{" "}
                            </span>
                            <span className="text-sm text-gray-700 dark:text-gray-300">
                                {jdRequirements.must_have_skills
                                    .slice(0, 5)
                                    .join(", ")}
                                {jdRequirements.must_have_skills.length > 5 &&
                                    ` +${jdRequirements.must_have_skills.length - 5} more`}
                            </span>
                        </div>
                    )}

                    {jdRequirements.nice_to_have_skills?.length > 0 && (
                        <div>
                            <span className="text-xs text-gray-500 dark:text-gray-400">
                                Nice-to-have:{" "}
                            </span>
                            <span className="text-sm text-gray-700 dark:text-gray-300">
                                {jdRequirements.nice_to_have_skills
                                    .slice(0, 5)
                                    .join(", ")}
                                {jdRequirements.nice_to_have_skills.length > 5 &&
                                    ` +${jdRequirements.nice_to_have_skills.length - 5} more`}
                            </span>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

DomainMatchCard.propTypes = {
    jdRequirements: PropTypes.shape({
        domain_focus: PropTypes.arrayOf(PropTypes.string),
        must_have_skills: PropTypes.arrayOf(PropTypes.string),
        nice_to_have_skills: PropTypes.arrayOf(PropTypes.string),
    }),
    critique: PropTypes.shape({
        domain_match_coverage: PropTypes.number,
    }),
};

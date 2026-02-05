export default function LayoutToggle({ layout, onLayoutChange }) {
    const layouts = [
        {
            id: "split",
            label: "Split View",
            icon: (
                <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <rect x="3" y="3" width="7" height="18" rx="1" strokeWidth="2" />
                    <rect x="14" y="3" width="7" height="18" rx="1" strokeWidth="2" />
                </svg>
            ),
        },
        {
            id: "editor",
            label: "Editor Only",
            icon: (
                <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"
                    />
                </svg>
            ),
        },
        {
            id: "preview",
            label: "Preview Only",
            icon: (
                <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                    />
                </svg>
            ),
        },
    ];

    return (
        <div className="flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-800 rounded-lg">
            {layouts.map((l) => (
                <button
                    key={l.id}
                    onClick={() => onLayoutChange(l.id)}
                    title={l.label}
                    className={`
                        p-2 rounded-md transition-colors
                        ${
                            layout === l.id
                                ? "bg-white dark:bg-slate-700 text-primary-600 dark:text-primary-400 shadow-sm"
                                : "text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
                        }
                    `}
                >
                    {l.icon}
                </button>
            ))}
        </div>
    );
}

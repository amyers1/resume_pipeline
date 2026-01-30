import { Link } from "react-router-dom";
import { useApp } from "../contexts/AppContext";
import HealthBadge from "./HealthBadge";

export default function Header() {
    const { state, dispatch, actionTypes } = useApp();

    const toggleTheme = () => {
        dispatch({ type: actionTypes.TOGGLE_THEME });
    };

    return (
        <header className="bg-white dark:bg-background-surface border-b border-slate-200 dark:border-slate-700 sticky top-0 z-30">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between h-16">
                    {/* Logo and Navigation */}
                    <div className="flex items-center gap-8">
                        <Link to="/" className="flex items-center gap-2">
                            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
                                <span className="text-white font-bold text-lg">
                                    <svg
                                        width="40"
                                        height="40"
                                        viewBox="0 0 40 40"
                                        fill="none"
                                        xmlns="http://www.w3.org/2000/svg"
                                    >
                                        <path
                                            d="M8 20H32"
                                            stroke="#334155"
                                            stroke-width="2"
                                            stroke-linecap="round"
                                        />

                                        <circle
                                            cx="8"
                                            cy="20"
                                            r="4"
                                            class="fill-slate-400 dark:fill-slate-500"
                                        />

                                        <circle
                                            cx="20"
                                            cy="20"
                                            r="6"
                                            class="fill-primary-500 animate-pulse"
                                        />
                                        <circle
                                            cx="20"
                                            cy="20"
                                            r="10"
                                            stroke="#06b6d4"
                                            stroke-width="1.5"
                                            class="opacity-30"
                                        />

                                        <circle
                                            cx="32"
                                            cy="20"
                                            r="4"
                                            class="fill-slate-400 dark:fill-slate-500"
                                        />
                                    </svg>
                                </span>
                            </div>
                            <span className="text-xl font-bold text-slate-900 dark:text-white">
                                Resume Pipeline
                            </span>
                        </Link>

                        <nav className="hidden md:flex items-center gap-6">
                            <Link
                                to="/"
                                className="text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition-colors"
                            >
                                Dashboard
                            </Link>
                            <Link
                                to="/profiles"
                                className="text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition-colors"
                            >
                                Profiles
                            </Link>
                            <Link
                                to="/new-job"
                                className="text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition-colors"
                            >
                                New Resume
                            </Link>
                        </nav>
                    </div>

                    {/* Right side actions */}
                    <div className="flex items-center gap-4">
                        <HealthBadge />

                        <button
                            onClick={toggleTheme}
                            className="p-2 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                            aria-label="Toggle theme"
                        >
                            {state.ui.theme === "light" ? "🌙" : "☀️"}
                        </button>
                    </div>
                </div>
            </div>
        </header>
    );
}

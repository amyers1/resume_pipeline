import { Link } from "react-router-dom";
import { useApp } from "../contexts/AppContext";
import HealthBadge from "./HealthBadge";

export default function Header() {
    const { state, dispatch, actionTypes } = useApp();

    const toggleTheme = () => {
        dispatch({ type: actionTypes.TOGGLE_THEME });
    };

    return (
        <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-30">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between h-16">
                    {/* Logo and Navigation */}
                    <div className="flex items-center gap-8">
                        <Link to="/" className="flex items-center gap-2">
                            <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
                                <span className="text-white font-bold text-lg">
                                    R
                                </span>
                            </div>
                            <span className="text-xl font-bold text-gray-900 dark:text-white">
                                Resume Pipeline
                            </span>
                        </Link>

                        <nav className="hidden md:flex items-center gap-6">
                            <Link
                                to="/"
                                className="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors"
                            >
                                Dashboard
                            </Link>
                            <Link
                                to="/profiles"
                                className="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors"
                            >
                                Profiles
                            </Link>
                            <Link
                                to="/new-job"
                                className="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors"
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
                            className="p-2 rounded-lg text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
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

import { Link } from "react-router-dom";
import { useApp } from "../contexts/AppContext";
import HealthBadge from "./HealthBadge";

export default function Header() {
    const { state, dispatch, actionTypes } = useApp();

    const toggleTheme = () => {
        dispatch({ type: actionTypes.TOGGLE_THEME });
    };

    return (
        // Updated: Glassmorphism Header
        <header className="bg-white/80 dark:bg-background/80 backdrop-blur-md border-b border-zinc-200 dark:border-zinc-800 sticky top-0 z-30">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between h-16">
                    {/* Logo and Navigation */}
                    <div className="flex items-center gap-8">
                        <Link to="/" className="flex items-center gap-2 group">
                            {/* NEW LOGO: Standalone SVG (No wrapping box) */}
                            <svg
                                width="40"
                                height="40"
                                viewBox="0 0 40 40"
                                fill="none"
                                xmlns="http://www.w3.org/2000/svg"
                                className="transition-transform group-hover:scale-105"
                            >
                                {/* Connecting Line - Adapts to Zinc Theme */}
                                <path
                                    d="M8 20H32"
                                    stroke="currentColor"
                                    strokeWidth="2"
                                    strokeLinecap="round"
                                    className="text-zinc-300 dark:text-zinc-600"
                                />

                                {/* Left Node (Input) */}
                                <circle
                                    cx="8"
                                    cy="20"
                                    r="4"
                                    className="fill-zinc-400 dark:fill-zinc-500"
                                />

                                {/* Center Node (Processing - Electric Cyan) */}
                                <circle
                                    cx="20"
                                    cy="20"
                                    r="6"
                                    className="fill-primary-500 animate-pulse"
                                />
                                <circle
                                    cx="20"
                                    cy="20"
                                    r="10"
                                    stroke="currentColor"
                                    strokeWidth="1.5"
                                    className="text-primary-500 opacity-30"
                                />

                                {/* Right Node (Output) */}
                                <circle
                                    cx="32"
                                    cy="20"
                                    r="4"
                                    className="fill-zinc-400 dark:fill-zinc-500"
                                />
                            </svg>

                            <span className="text-xl font-bold text-zinc-900 dark:text-white tracking-tight">
                                Resume Pipeline
                            </span>
                        </Link>

                        <nav className="hidden md:flex items-center gap-6">
                            <Link
                                to="/"
                                className="text-sm font-medium text-zinc-600 dark:text-zinc-400 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
                            >
                                Dashboard
                            </Link>
                            <Link
                                to="/profiles"
                                className="text-sm font-medium text-zinc-600 dark:text-zinc-400 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
                            >
                                Profiles
                            </Link>
                            <Link
                                to="/new-job"
                                className="text-sm font-medium text-zinc-600 dark:text-zinc-400 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
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
                            className="p-2 rounded-lg text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors focus:ring-2 focus:ring-primary-500"
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

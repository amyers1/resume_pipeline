import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useApp } from "../contexts/AppContext";
import HealthBadge from "./HealthBadge";

export default function Header() {
    const { state, dispatch, actionTypes } = useApp();
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const location = useLocation();

    const toggleTheme = () => {
        dispatch({ type: actionTypes.TOGGLE_THEME });
    };

    const closeMobileMenu = () => {
        setMobileMenuOpen(false);
    };

    const isActivePath = (path) => {
        return location.pathname === path;
    };

    return (
        <header className="bg-white/80 dark:bg-background/80 backdrop-blur-md border-b border-zinc-200 dark:border-zinc-800 sticky top-0 z-30">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between h-16">
                    {/* Logo */}
                    <div className="flex items-center gap-2 sm:gap-8">
                        <Link
                            to="/"
                            className="flex items-center gap-2 group"
                            onClick={closeMobileMenu}
                        >
                            <svg
                                width="36"
                                height="36"
                                viewBox="0 0 40 40"
                                fill="none"
                                xmlns="http://www.w3.org/2000/svg"
                                className="transition-transform group-hover:scale-105"
                            >
                                <path
                                    d="M8 20H32"
                                    stroke="currentColor"
                                    strokeWidth="2"
                                    strokeLinecap="round"
                                    className="text-zinc-300 dark:text-zinc-600"
                                />
                                <circle
                                    cx="8"
                                    cy="20"
                                    r="3"
                                    fill="currentColor"
                                    className="text-primary-500"
                                />
                                <circle
                                    cx="32"
                                    cy="20"
                                    r="3"
                                    fill="currentColor"
                                    className="text-primary-500"
                                />
                            </svg>
                            <span className="hidden sm:block text-lg font-semibold text-zinc-900 dark:text-white">
                                Resume Pipeline
                            </span>
                        </Link>

                        {/* Desktop Navigation */}
                        <nav className="hidden md:flex items-center gap-6">
                            <Link
                                to="/"
                                className={`text-sm font-medium transition-colors ${
                                    isActivePath("/")
                                        ? "text-primary-600 dark:text-primary-400"
                                        : "text-zinc-600 dark:text-zinc-400 hover:text-primary-600 dark:hover:text-primary-400"
                                }`}
                            >
                                Dashboard
                            </Link>
                            <Link
                                to="/profiles"
                                className={`text-sm font-medium transition-colors ${
                                    isActivePath("/profiles")
                                        ? "text-primary-600 dark:text-primary-400"
                                        : "text-zinc-600 dark:text-zinc-400 hover:text-primary-600 dark:hover:text-primary-400"
                                }`}
                            >
                                Profiles
                            </Link>
                            <Link
                                to="/new-job"
                                className={`text-sm font-medium transition-colors ${
                                    isActivePath("/new-job")
                                        ? "text-primary-600 dark:text-primary-400"
                                        : "text-zinc-600 dark:text-zinc-400 hover:text-primary-600 dark:hover:text-primary-400"
                                }`}
                            >
                                New Resume
                            </Link>
                        </nav>
                    </div>

                    {/* Right side actions */}
                    <div className="flex items-center gap-2 sm:gap-4">
                        {/* Desktop: Show HealthBadge */}
                        <div className="hidden sm:block">
                            <HealthBadge />
                        </div>

                        <button
                            onClick={toggleTheme}
                            className="p-2 rounded-lg text-zinc-500 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors focus:ring-2 focus:ring-primary-500"
                            aria-label="Toggle theme"
                        >
                            {state.ui.theme === "light" ? "🌙" : "☀️"}
                        </button>

                        {/* Mobile Menu Button */}
                        <button
                            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                            className="md:hidden p-2 rounded-lg text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors focus:ring-2 focus:ring-primary-500"
                            aria-label="Toggle mobile menu"
                        >
                            {mobileMenuOpen ? (
                                <svg
                                    className="w-6 h-6"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2}
                                        d="M6 18L18 6M6 6l12 12"
                                    />
                                </svg>
                            ) : (
                                <svg
                                    className="w-6 h-6"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                >
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={2}
                                        d="M4 6h16M4 12h16M4 18h16"
                                    />
                                </svg>
                            )}
                        </button>
                    </div>
                </div>
            </div>

            {/* Mobile Menu */}
            {mobileMenuOpen && (
                <>
                    {/* Backdrop */}
                    <div
                        className="fixed inset-0 bg-black/50 z-40 md:hidden"
                        onClick={closeMobileMenu}
                    />

                    {/* Menu Panel */}
                    <div className="fixed top-16 left-0 right-0 bg-white dark:bg-background-surface border-b border-zinc-200 dark:border-zinc-800 shadow-lg z-40 md:hidden">
                        <nav className="px-4 py-6 space-y-4">
                            <Link
                                to="/"
                                onClick={closeMobileMenu}
                                className={`block px-4 py-3 rounded-lg text-base font-medium transition-colors ${
                                    isActivePath("/")
                                        ? "bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400"
                                        : "text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                                }`}
                            >
                                📊 Dashboard
                            </Link>
                            <Link
                                to="/profiles"
                                onClick={closeMobileMenu}
                                className={`block px-4 py-3 rounded-lg text-base font-medium transition-colors ${
                                    isActivePath("/profiles")
                                        ? "bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400"
                                        : "text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                                }`}
                            >
                                👤 Profiles
                            </Link>
                            <Link
                                to="/new-job"
                                onClick={closeMobileMenu}
                                className={`block px-4 py-3 rounded-lg text-base font-medium transition-colors ${
                                    isActivePath("/new-job")
                                        ? "bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400"
                                        : "text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800"
                                }`}
                            >
                                ✨ New Resume
                            </Link>

                            {/* Mobile: Show Health Status */}
                            <div className="pt-4 border-t border-zinc-200 dark:border-zinc-700">
                                <div className="px-4 py-2">
                                    <HealthBadge />
                                </div>
                            </div>
                        </nav>
                    </div>
                </>
            )}
        </header>
    );
}

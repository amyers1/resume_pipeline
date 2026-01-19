import { useState, useEffect, useRef } from "react";
import { apiService } from "../services/api";
import { HEALTH_COLORS } from "../utils/constants";

export default function HealthBadge() {
    const [health, setHealth] = useState({ status: "unknown" });
    const [isOpen, setIsOpen] = useState(false);
    const [lastChecked, setLastChecked] = useState(null);
    const dropdownRef = useRef(null);

    const checkHealth = async () => {
        try {
            const response = await apiService.checkHealth();
            setHealth(response.data);
            setLastChecked(new Date());
        } catch (error) {
            setHealth({ status: "unhealthy", error: error.message });
        }
    };

    useEffect(() => {
        checkHealth();
        // Poll every 30 seconds
        const interval = setInterval(checkHealth, 30000);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (
                dropdownRef.current &&
                !dropdownRef.current.contains(event.target)
            ) {
                setIsOpen(false);
            }
        };

        document.addEventListener("mousedown", handleClickOutside);
        return () =>
            document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const statusColor = HEALTH_COLORS[health.status] || HEALTH_COLORS.unhealthy;

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${statusColor}`}
            >
                <div className="w-2 h-2 rounded-full bg-current animate-pulse" />
                <span className="capitalize">{health.status}</span>
            </button>

            {isOpen && (
                <div className="absolute right-0 mt-2 w-64 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-2 z-50">
                    <div className="px-4 py-2 border-b border-gray-100 dark:border-gray-700">
                        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                            System Status
                        </h3>
                        <p className="text-xs text-gray-500 mt-1">
                            Last checked:{" "}
                            {lastChecked
                                ? lastChecked.toLocaleTimeString()
                                : "Never"}
                        </p>
                    </div>

                    <div className="px-4 py-2">
                        {/* Safe rendering check to prevent crash */}
                        {health.details ? (
                            <div className="space-y-2">
                                {Object.entries(health.details).map(
                                    ([key, value]) => (
                                        <div
                                            key={key}
                                            className="flex justify-between text-sm"
                                        >
                                            <span className="text-gray-600 dark:text-gray-400 capitalize">
                                                {key.replace("_", " ")}
                                            </span>
                                            <span className="text-gray-900 dark:text-white font-medium">
                                                {value}
                                            </span>
                                        </div>
                                    ),
                                )}
                            </div>
                        ) : (
                            <p className="text-sm text-gray-600 dark:text-gray-400">
                                System is operational.
                            </p>
                        )}

                        {health.error && (
                            <p className="text-xs text-red-500 mt-2 pt-2 border-t border-gray-100 dark:border-gray-700">
                                Error: {health.error}
                            </p>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

import { useEffect, useRef } from "react";
import { formatDate } from "../utils/helpers";

export default function LiveLog({ events = [] }) {
    const logEndRef = useRef(null);

    // Auto-scroll to bottom when new events arrive
    useEffect(() => {
        logEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [events]);

    const getEventIcon = (event) => {
        if (event.status === "job_completed") return "✅";
        if (event.status === "job_failed") return "❌";
        if (event.status === "job_started") return "🚀";
        return "⏳";
    };

    const getEventColor = (event) => {
        if (event.status === "job_completed")
            return "text-green-600 dark:text-green-400";
        if (event.status === "job_failed")
            return "text-red-600 dark:text-red-400";
        if (event.status === "job_started")
            return "text-blue-600 dark:text-blue-400";
        return "text-slate-600 dark:text-slate-400";
    };

    const copyLog = () => {
        const logText = events
            .map((event) => {
                const time = new Date(
                    event.timestamp || Date.now(),
                ).toLocaleTimeString();
                return `${time}  ${event.message || event.stage || ""}`;
            })
            .join("\n");

        navigator.clipboard.writeText(logText);
        alert("Log copied to clipboard!");
    };

    if (events.length === 0) {
        return (
            <div className="text-center py-8 text-slate-500 dark:text-slate-400">
                Waiting for updates...
            </div>
        );
    }

    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-slate-700 dark:text-slate-300">
                    Activity Log
                </h3>
                <button
                    onClick={copyLog}
                    className="text-xs text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300"
                >
                    Copy Log
                </button>
            </div>

            <div className="bg-background rounded-lg p-4 max-h-96 overflow-y-auto font-mono text-sm">
                <div className="space-y-2">
                    {events.map((event, index) => (
                        <div key={index} className="flex items-start gap-3">
                            <span className="text-slate-500 flex-shrink-0 text-xs">
                                {new Date(
                                    event.timestamp || Date.now(),
                                ).toLocaleTimeString()}
                            </span>
                            <span className="flex-shrink-0">
                                {getEventIcon(event)}
                            </span>
                            <span className={`flex-1 ${getEventColor(event)}`}>
                                {event.message ||
                                    event.stage ||
                                    "Processing..."}
                                {event.progress_percent !== undefined && (
                                    <span className="ml-2 text-slate-400">
                                        ({event.progress_percent}%)
                                    </span>
                                )}
                            </span>
                        </div>
                    ))}
                    <div ref={logEndRef} />
                </div>
            </div>
        </div>
    );
}

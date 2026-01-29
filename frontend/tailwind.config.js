/** @type {import('tailwindcss').Config} */
export default {
    content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
    darkMode: "class",
    theme: {
        extend: {
            // 1. The Font Stack
            fontFamily: {
                sans: ["Inter", "system-ui", "sans-serif"],
                mono: ["JetBrains Mono", "monospace"],
            },
            // 2. The Color System
            colors: {
                // "The Architect" Dark Mode Base (Deep Slate)
                // Use these for page backgrounds instead of gray-900
                background: {
                    DEFAULT: "#0f172a", // Slate 900 (Main App Background)
                    surface: "#1e293b", // Slate 800 (Cards/Headers)
                    elevated: "#334155", // Slate 700 (Modals/Popovers)
                },
                // "Electric Cyan" (Replaces your old Blue Primary)
                primary: {
                    50: "#ecfeff",
                    100: "#cffafe",
                    200: "#a5f3fc",
                    300: "#67e8f9",
                    400: "#22d3ee",
                    500: "#06b6d4", // <--- Your new Brand Color
                    600: "#0891b2",
                    700: "#0e7490",
                    800: "#155e75",
                    900: "#164e63",
                    950: "#083344",
                },
                // "Warning Amber" (For alerts/warnings)
                secondary: {
                    500: "#f59e0b",
                },
            },
            // 3. Custom Animations
            animation: {
                "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
            },
        },
    },
    plugins: [],
};

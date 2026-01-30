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
                // "True Dark" Base (Zinc-based)
                background: {
                    DEFAULT: "#09090b", // Almost black (Main App Background)
                    surface: "#18181b", // Zinc 900 (Cards/Headers)
                    elevated: "#27272a", // Zinc 800 (Modals/Popovers)
                },
                // "Electric Cyan" (Kept the same, but now pops against black)
                primary: {
                    50: "#ecfeff",
                    100: "#cffafe",
                    200: "#a5f3fc",
                    300: "#67e8f9",
                    400: "#22d3ee",
                    500: "#06b6d4",
                    600: "#0891b2",
                    700: "#0e7490",
                    800: "#155e75",
                    900: "#164e63",
                    950: "#083344",
                },
                // Status Colors (Aligned with the tech vibe)
                secondary: { 500: "#f59e0b" }, // Amber
                success: { 500: "#10b981" }, // Emerald (Better than standard Green)
                danger: { 500: "#ef4444" }, // Red
            },
            // 3. Custom Animations
            animation: {
                "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
            },
        },
    },
    plugins: [],
};

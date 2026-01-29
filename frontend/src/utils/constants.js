// API Configuration
export const API_CONFIG = {
    baseURL: import.meta.env.VITE_API_URL || "/api",
    timeout: 30000,
    headers: {
        "Content-Type": "application/json",
    },
};

// Error codes from backend
export const ERROR_CODES = {
    VALIDATION_ERROR: "validation_error",
    JOB_NOT_FOUND: "job_not_found",
    FILE_NOT_FOUND: "file_not_found",
    QUEUE_ERROR: "queue_error",
    INTERNAL_ERROR: "internal_error",
    CONFLICT: "conflict",
};

// Pipeline stages with labels and weights
export const PIPELINE_STAGES = {
    analyzing_jd: {
        label: "Analyzing Job Description",
        weight: 15,
        color: "#3b82f6",
    },
    matching_achievements: {
        label: "Matching Experience",
        weight: 20,
        color: "#8b5cf6",
    },
    generating_draft: {
        label: "Generating Draft",
        weight: 25,
        color: "#ec4899",
    },
    critiquing: { label: "AI Review", weight: 15, color: "#f59e0b" },
    refining: { label: "Refining Content", weight: 10, color: "#10b981" },
    generating_output: { label: "Creating PDF", weight: 10, color: "#f59e0b" },
    post_processing: { label: "Uploading Files", weight: 5, color: "#10b981" },
    completed: { label: "Complete", weight: 100, color: "#059669" },
};

// Job status colors
export const STATUS_COLORS = {
    completed:
        "text-green-600 bg-green-100 dark:bg-green-900/30 dark:text-green-400",
    processing:
        "text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30 dark:text-yellow-400",
    failed: "text-red-600 bg-red-100 dark:bg-red-900/30 dark:text-red-400",
    queued: "text-gray-600 bg-gray-100 dark:bg-background-surface dark:text-gray-400",
};

// Health status colors
export const HEALTH_COLORS = {
    healthy: "text-green-600 bg-green-100 dark:bg-green-900/30",
    degraded: "text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30",
    unhealthy: "text-red-600 bg-red-100 dark:bg-red-900/30",
};

// Templates
export const TEMPLATES = [
    { value: "modern-deedy", label: "Modern Deedy", backend: "latex" },
    { value: "awesome-cv", label: "Awesome CV", backend: "latex" },
    { value: "resume.html.j2", label: "Standard HTML", backend: "weasyprint" },
];

// Output backends
export const OUTPUT_BACKENDS = [
    {
        value: "weasyprint",
        label: "WeasyPrint (Fast)",
        description: "CSS-based PDF generation",
    },
    {
        value: "latex",
        label: "LaTeX (Professional)",
        description: "Academic-quality typesetting",
    },
];

// File type icons
export const FILE_ICONS = {
    pdf: "📄",
    json: "📋",
    tex: "📝",
    txt: "📃",
};

// Model Options
export const MODEL_OPTIONS = [
    { value: "gpt-5", label: "GPT-5 (OpenAI)" },
    { value: "gpt-5-mini", label: "GPT-5 Mini (OpenAI)" },
    { value: "gpt-5-nano", label: "GPT-5 Nano (OpenAI)" },
    { value: "gpt-4o", label: "GPT-4o (OpenAI)" },
    { value: "gpt-4o-mini", label: "GPT-4o Mini (OpenAI)" },
    { value: "gpt-4-turbo", label: "GPT-4 Turbo (OpenAI)" },
    { value: "gpt-4", label: "GPT-4 (OpenAI)" },
    { value: "gpt-3.5-turbo", label: "GPT-3.5 Turbo (OpenAI)" },
    { value: "gemini-2.5-pro", label: "Gemini 2.5 Pro (Google)" },
    { value: "gemini-2.5-flash", label: "Gemini 2.5 Flash (Google)" },
    { value: "gemini-2.5-flash-lite", label: "Gemini 2.5 Flash-Lite (Google)" },
    {
        value: "gemini-3.0-flash-preview",
        label: "Gemini 3.0 Flash Preview (Google)",
    },
];

// Base Model Options (for analysis & fast tasks)
export const BASE_MODEL_OPTIONS = [
    { value: "gpt-5-mini", label: "GPT-5 Mini (OpenAI)" },
    { value: "gpt-4o-mini", label: "GPT-4o Mini (OpenAI)" },
    {
        value: "gemini-3.0-flash-preview",
        label: "Gemini 3.0 Flash Preview (Google)",
    },
    { value: "gemini-2.5-flash", label: "Gemini 2.5 Flash (Google)" },
    { value: "gemini-2.5-flash-lite", label: "Gemini 2.5 Flash-Lite (Google)" },
];

// Strong Model Options (for reasoning & drafting)
export const STRONG_MODEL_OPTIONS = [
    ...BASE_MODEL_OPTIONS,
    { value: "gpt-5", label: "GPT-5 (OpenAI)" },
    { value: "gpt-4o", label: "GPT-4o (OpenAI)" },
    { value: "gpt-4", label: "GPT-4 (OpenAI)" },
    { value: "gemini-2.5-pro", label: "Gemini 2.5 Pro (Google)" },
];

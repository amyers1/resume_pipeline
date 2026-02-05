import { useState, useEffect, useRef } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

// Configure PDF.js worker - use unpkg CDN to avoid auth proxy issues
pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

export default function PdfViewer({ pdfUrl, isCompiling }) {
    const [numPages, setNumPages] = useState(null);
    const [pageNumber, setPageNumber] = useState(1);
    const [scale, setScale] = useState(1.0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [fitMode, setFitMode] = useState("width"); // width, page, custom
    const containerRef = useRef(null);
    const [containerWidth, setContainerWidth] = useState(null);

    useEffect(() => {
        if (pdfUrl) {
            setLoading(true);
            setError(null);
        }
    }, [pdfUrl]);

    // Track container size for fit-to-width
    useEffect(() => {
        const updateWidth = () => {
            if (containerRef.current) {
                setContainerWidth(containerRef.current.clientWidth - 32); // Account for padding
            }
        };
        updateWidth();
        window.addEventListener("resize", updateWidth);
        return () => window.removeEventListener("resize", updateWidth);
    }, []);

    const onDocumentLoadSuccess = ({ numPages }) => {
        setNumPages(numPages);
        setPageNumber(1);
        setLoading(false);
    };

    const onDocumentLoadError = (error) => {
        console.error("PDF load error:", error);
        setError("Failed to load PDF");
        setLoading(false);
    };

    const changePage = (offset) => {
        setPageNumber((prevPageNumber) => {
            const newPage = prevPageNumber + offset;
            return Math.max(1, Math.min(newPage, numPages || 1));
        });
    };

    const goToPage = (page) => {
        const pageNum = parseInt(page, 10);
        if (pageNum >= 1 && pageNum <= numPages) {
            setPageNumber(pageNum);
        }
    };

    const previousPage = () => changePage(-1);
    const nextPage = () => changePage(1);

    const zoomIn = () => {
        setFitMode("custom");
        setScale((s) => Math.min(s + 0.2, 3.0));
    };

    const zoomOut = () => {
        setFitMode("custom");
        setScale((s) => Math.max(s - 0.2, 0.3));
    };

    const resetZoom = () => {
        setFitMode("width");
        setScale(1.0);
    };

    const fitToWidth = () => {
        setFitMode("width");
    };

    const fitToPage = () => {
        setFitMode("page");
        setScale(0.8); // Approximate fit for most pages
    };

    const handlePrint = () => {
        if (pdfUrl) {
            window.open(pdfUrl, "_blank");
        }
    };

    if (isCompiling) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4" />
                    <p className="text-slate-600 dark:text-slate-400">
                        Compiling LaTeX...
                    </p>
                </div>
            </div>
        );
    }

    if (!pdfUrl) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="text-center text-slate-500 dark:text-slate-400">
                    <svg
                        className="w-16 h-16 mx-auto mb-4 opacity-50"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                        />
                    </svg>
                    <p>Compile to generate PDF preview</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="text-center text-red-600 dark:text-red-400">
                    <svg
                        className="w-16 h-16 mx-auto mb-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                        />
                    </svg>
                    <p>{error}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full">
            {/* Controls */}
            <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 bg-white dark:bg-background-surface border-b border-slate-200 dark:border-slate-700">
                {/* Page Navigation */}
                <div className="flex items-center gap-1">
                    <button
                        onClick={previousPage}
                        disabled={pageNumber <= 1}
                        className="p-1.5 sm:p-2 rounded hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Previous page"
                    >
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
                                d="M15 19l-7-7 7-7"
                            />
                        </svg>
                    </button>
                    <div className="flex items-center gap-1 text-sm text-slate-600 dark:text-slate-400">
                        <input
                            type="number"
                            min="1"
                            max={numPages || 1}
                            value={pageNumber}
                            onChange={(e) => goToPage(e.target.value)}
                            className="w-12 px-1.5 py-1 text-center border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm"
                        />
                        <span>/</span>
                        <span>{numPages || "?"}</span>
                    </div>
                    <button
                        onClick={nextPage}
                        disabled={pageNumber >= numPages}
                        className="p-1.5 sm:p-2 rounded hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Next page"
                    >
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
                                d="M9 5l7 7-7 7"
                            />
                        </svg>
                    </button>
                </div>

                {/* Zoom Controls */}
                <div className="flex items-center gap-1">
                    <button
                        onClick={zoomOut}
                        className="p-1.5 sm:p-2 rounded hover:bg-slate-100 dark:hover:bg-slate-700"
                        title="Zoom out"
                    >
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
                                d="M20 12H4"
                            />
                        </svg>
                    </button>
                    <span className="text-sm text-slate-600 dark:text-slate-400 min-w-[3rem] text-center">
                        {fitMode === "width"
                            ? "Fit"
                            : `${Math.round(scale * 100)}%`}
                    </span>
                    <button
                        onClick={zoomIn}
                        className="p-1.5 sm:p-2 rounded hover:bg-slate-100 dark:hover:bg-slate-700"
                        title="Zoom in"
                    >
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
                                d="M12 4v16m8-8H4"
                            />
                        </svg>
                    </button>

                    {/* Fit buttons - hidden on very small screens */}
                    <div className="hidden sm:flex items-center gap-1 ml-1 border-l border-slate-200 dark:border-slate-600 pl-2">
                        <button
                            onClick={fitToWidth}
                            className={`px-2 py-1 text-xs rounded transition-colors ${
                                fitMode === "width"
                                    ? "bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300"
                                    : "hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-400"
                            }`}
                            title="Fit to width"
                        >
                            Width
                        </button>
                        <button
                            onClick={resetZoom}
                            className="px-2 py-1 text-xs rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-400"
                            title="Reset zoom"
                        >
                            100%
                        </button>
                    </div>
                </div>

                {/* Action buttons */}
                <div className="flex items-center gap-1">
                    <button
                        onClick={handlePrint}
                        className="p-1.5 sm:p-2 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-400"
                        title="Open in new tab / Print"
                    >
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
                                d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"
                            />
                        </svg>
                    </button>
                    <a
                        href={pdfUrl}
                        download="resume.pdf"
                        className="p-1.5 sm:p-2 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-400"
                        title="Download PDF"
                    >
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
                                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                            />
                        </svg>
                    </a>
                </div>
            </div>

            {/* PDF Document */}
            <div
                ref={containerRef}
                className="flex-1 overflow-auto min-h-0 bg-slate-200 dark:bg-slate-900"
            >
                <div className="flex justify-center p-4">
                    {loading && (
                        <div className="text-center text-slate-600 dark:text-slate-400">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto mb-2" />
                            Loading PDF...
                        </div>
                    )}
                    <Document
                        file={pdfUrl}
                        onLoadSuccess={onDocumentLoadSuccess}
                        onLoadError={onDocumentLoadError}
                        loading=""
                        className="shadow-xl"
                    >
                        <Page
                            pageNumber={pageNumber}
                            scale={fitMode === "custom" ? scale : undefined}
                            width={
                                fitMode === "width" && containerWidth
                                    ? containerWidth
                                    : undefined
                            }
                            renderTextLayer={true}
                            renderAnnotationLayer={true}
                            className="bg-white"
                        />
                    </Document>
                </div>
            </div>

            {/* Page indicator - mobile friendly */}
            {numPages > 1 && (
                <div className="flex justify-center py-2 bg-white dark:bg-background-surface border-t border-slate-200 dark:border-slate-700 sm:hidden">
                    <div className="flex items-center gap-2">
                        {Array.from(
                            { length: Math.min(numPages, 5) },
                            (_, i) => {
                                const pageNum = i + 1;
                                return (
                                    <button
                                        key={pageNum}
                                        onClick={() => setPageNumber(pageNum)}
                                        className={`w-8 h-8 rounded-full text-sm font-medium transition-colors ${
                                            pageNumber === pageNum
                                                ? "bg-primary-600 text-white"
                                                : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400"
                                        }`}
                                    >
                                        {pageNum}
                                    </button>
                                );
                            },
                        )}
                        {numPages > 5 && (
                            <span className="text-slate-400 dark:text-slate-500">
                                ...
                            </span>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

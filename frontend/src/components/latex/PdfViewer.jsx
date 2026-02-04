import { useState, useEffect } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/esm/Page/AnnotationLayer.css";
import "react-pdf/dist/esm/Page/TextLayer.css";

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

export default function PdfViewer({ pdfUrl, isCompiling }) {
    const [numPages, setNumPages] = useState(null);
    const [pageNumber, setPageNumber] = useState(1);
    const [scale, setScale] = useState(1.0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (pdfUrl) {
            setLoading(true);
            setError(null);
        }
    }, [pdfUrl]);

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
        setPageNumber((prevPageNumber) => prevPageNumber + offset);
    };

    const previousPage = () => changePage(-1);
    const nextPage = () => changePage(1);

    const zoomIn = () => setScale((s) => Math.min(s + 0.2, 2.0));
    const zoomOut = () => setScale((s) => Math.max(s - 0.2, 0.5));
    const resetZoom = () => setScale(1.0);

    if (isCompiling) {
        return (
            <div className="flex items-center justify-center h-full">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
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
            <div className="flex items-center justify-between px-4 py-2 bg-white dark:bg-background-surface border-b border-slate-200 dark:border-slate-700">
                <div className="flex items-center gap-2">
                    <button
                        onClick={previousPage}
                        disabled={pageNumber <= 1}
                        className="p-2 rounded hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Previous page"
                    >
                        ←
                    </button>
                    <span className="text-sm text-slate-600 dark:text-slate-400">
                        Page {pageNumber} of {numPages || "?"}
                    </span>
                    <button
                        onClick={nextPage}
                        disabled={pageNumber >= numPages}
                        className="p-2 rounded hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Next page"
                    >
                        →
                    </button>
                </div>

                <div className="flex items-center gap-2">
                    <button
                        onClick={zoomOut}
                        className="p-2 rounded hover:bg-slate-100 dark:hover:bg-slate-700"
                        title="Zoom out"
                    >
                        −
                    </button>
                    <span className="text-sm text-slate-600 dark:text-slate-400 min-w-[4rem] text-center">
                        {Math.round(scale * 100)}%
                    </span>
                    <button
                        onClick={zoomIn}
                        className="p-2 rounded hover:bg-slate-100 dark:hover:bg-slate-700"
                        title="Zoom in"
                    >
                        +
                    </button>
                    <button
                        onClick={resetZoom}
                        className="px-3 py-1 text-sm rounded hover:bg-slate-100 dark:hover:bg-slate-700"
                        title="Reset zoom"
                    >
                        Reset
                    </button>
                </div>
            </div>

            {/* PDF Document */}
            <div className="flex-1 overflow-auto flex items-center justify-center p-4">
                {loading && (
                    <div className="text-center text-slate-600 dark:text-slate-400">
                        Loading PDF...
                    </div>
                )}
                <Document
                    file={pdfUrl}
                    onLoadSuccess={onDocumentLoadSuccess}
                    onLoadError={onDocumentLoadError}
                    loading=""
                >
                    <Page
                        pageNumber={pageNumber}
                        scale={scale}
                        renderTextLayer={true}
                        renderAnnotationLayer={true}
                    />
                </Document>
            </div>
        </div>
    );
}

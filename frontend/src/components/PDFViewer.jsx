import React, { useState, useEffect, useRef, useCallback } from 'react';
import * as pdfjsLib from 'pdfjs-dist';

// Configure PDF.js worker
pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.js',
  import.meta.url
).toString();

/**
 * PDFViewer — Renderiza páginas de PDF usando PDF.js en canvas.
 *
 * Props:
 *   pdfUrl       — URL del PDF (endpoint /download o /static/books/...)
 *   currentPage  — Página actual (1-indexed)
 *   totalPages   — Total de páginas (desde API, NO del PDF)
 *   onPageChange — callback(pageNumber) cuando cambia la página renderizada
 *   zoom         — nivel de zoom (1.0 = 100%)
 *   onZoomChange — callback(newZoom) cuando cambia el zoom
 *   onDocumentLoaded — callback(pdfDocument) cuando el PDF se carga completamente
 *   onError          — callback(error) si falla la carga del PDF
 */
export default function PDFViewer({
  pdfUrl,
  currentPage = 1,
  totalPages: totalPagesProp = null,
  onPageChange,
  zoom = 1.0,
  onZoomChange,
  onDocumentLoaded,
  onError,
}) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const pdfDocRef = useRef(null);
  const renderingRef = useRef(false);
  const pageCacheRef = useRef(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [containerWidth, setContainerWidth] = useState(0);
  const currentPageRef = useRef(currentPage);

  // Keep ref in sync
  useEffect(() => {
    currentPageRef.current = currentPage;
  }, [currentPage]);

  // Load PDF document
  useEffect(() => {
    if (!pdfUrl) return;

    let cancelled = false;

    const loadPdf = async () => {
      try {
        setLoading(true);
        setError(null);

        const loadingTask = pdfjsLib.getDocument({
          url: pdfUrl,
          // Use range requests for large PDFs
          rangeChunkSize: 65536,
          disableAutoFetch: false,
          disableStream: false,
        });

        const pdfDoc = await loadingTask.promise;

        if (cancelled) return;

        pdfDocRef.current = pdfDoc;
        pageCacheRef.current.clear();

        if (onDocumentLoaded) onDocumentLoaded(pdfDoc);

        setLoading(false);
      } catch (err) {
        if (cancelled) return;
        console.error('Error loading PDF:', err);
        setError(err.message || 'Error loading PDF');
        setLoading(false);
        if (onError) onError(err);
      }
    };

    loadPdf();

    return () => {
      cancelled = true;
      if (pdfDocRef.current) {
        pdfDocRef.current.destroy();
        pdfDocRef.current = null;
      }
    };
  }, [pdfUrl]);

  // Observe container resize
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const w = entry.contentRect.width;
        if (w > 0 && Math.abs(w - containerWidth) > 1) {
          setContainerWidth(w);
        }
      }
    });

    observer.observe(container);
    setContainerWidth(container.clientWidth);

    return () => observer.disconnect();
  }, []);

  // Render a page on canvas
  const renderPage = useCallback(async (pageNumber) => {
    const pdfDoc = pdfDocRef.current;
    const canvas = canvasRef.current;
    if (!pdfDoc || !canvas || renderingRef.current) return;

    if (pageNumber < 1 || pageNumber > pdfDoc.numPages) return;

    renderingRef.current = true;

    try {
      // Get or cache the page
      let pageData = pageCacheRef.current.get(pageNumber);
      if (!pageData) {
        const page = await pdfDoc.getPage(pageNumber);
        const unscaledViewport = page.getViewport({ scale: 1 });
        pageData = { page, originalWidth: unscaledViewport.width, originalHeight: unscaledViewport.height };
        // Limit cache to 20 pages (simple FIFO)
        if (pageCacheRef.current.size > 20) {
          const keys = Array.from(pageCacheRef.current.keys());
          if (keys.length > 0) {
            pageCacheRef.current.delete(keys[0]);
          }
        }
        pageCacheRef.current.set(pageNumber, pageData);
      }

      const { page, originalWidth, originalHeight } = pageData;

      // Calculate scale to fit container width
      const maxWidth = containerWidth - 40; // padding
      const baseScale = maxWidth / originalWidth;
      const finalScale = baseScale * zoom;

      const viewport = page.getViewport({ scale: finalScale });

      const canvasEl = canvasRef.current;
      const ctx = canvasEl.getContext('2d');

      // Set canvas size
      canvasEl.width = viewport.width;
      canvasEl.height = viewport.height;
      canvasEl.style.width = viewport.width + 'px';
      canvasEl.style.height = viewport.height + 'px';

      // Clear and render
      ctx.clearRect(0, 0, canvasEl.width, canvasEl.height);
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, canvasEl.width, canvasEl.height);

      await page.render({
        canvasContext: ctx,
        viewport: viewport,
      }).promise;

      renderingRef.current = false;
    } catch (err) {
      console.error('Error rendering page:', err);
      renderingRef.current = false;
    }
  }, [containerWidth, zoom]);

  // Render when page or zoom changes
  useEffect(() => {
    if (!loading && !error && pdfDocRef.current) {
      renderPage(currentPage);
    }
  }, [currentPage, loading, error, renderPage]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

      if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        e.preventDefault();
        if (currentPageRef.current > 1 && onPageChange) {
          onPageChange(currentPageRef.current - 1);
        }
      } else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        e.preventDefault();
        if (onPageChange && currentPageRef.current < (totalPagesProp || pdfDocRef.current?.numPages || 0)) {
          onPageChange(currentPageRef.current + 1);
        }
      } else if (e.key === '+' || e.key === '=') {
        e.preventDefault();
        if (onZoomChange) onZoomChange(Math.min(zoom + 0.1, 3.0));
      } else if (e.key === '-') {
        e.preventDefault();
        if (onZoomChange) onZoomChange(Math.max(zoom - 0.1, 0.5));
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onPageChange, onZoomChange, zoom, totalPagesProp]);

  if (loading) {
    return (
      <div ref={containerRef} className="flex items-center justify-center h-full min-h-[300px] sm:min-h-[400px]">
        <div className="text-center text-[#A0A0A0]">
          <div className="animate-spin w-8 h-8 border-4 border-[#D92B2B] border-t-transparent rounded-full mx-auto mb-4"></div>
          Cargando PDF...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div ref={containerRef} className="flex items-center justify-center h-full min-h-[300px] sm:min-h-[400px]">
        <div className="text-center text-red-400">
          <p className="mb-2">Error al cargar el PDF</p>
          <p className="text-sm text-[#A0A0A0]">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* PDF canvas area */}
      <div
        ref={containerRef}
        className="flex-1 flex items-center justify-center overflow-hidden bg-[#1a1a1a] rounded-lg"
        style={{ minHeight: '300px' }}
      >
        <canvas
          ref={canvasRef}
          className="shadow-2xl max-w-full"
        />
      </div>

      {/* Zoom controls */}
      <div className="flex items-center justify-center gap-2 sm:gap-3 mt-2 sm:mt-3 py-1.5 sm:py-2">
        <button
          onClick={() => onZoomChange && onZoomChange(Math.max(zoom - 0.1, 0.5))}
          className="w-9 h-9 sm:w-8 sm:h-8 flex items-center justify-center rounded bg-white/5 border border-white/10 text-[#A0A0A0] hover:text-white hover:bg-white/10 transition-colors text-sm font-bold"
          title="Zoom menos"
        >
          -
        </button>
        <span className="text-xs text-[#A0A0A0] font-mono min-w-[44px] sm:min-w-[48px] text-center">
          {Math.round(zoom * 100)}%
        </span>
        <button
          onClick={() => onZoomChange && onZoomChange(Math.min(zoom + 0.1, 3.0))}
          className="w-9 h-9 sm:w-8 sm:h-8 flex items-center justify-center rounded bg-white/5 border border-white/10 text-[#A0A0A0] hover:text-white hover:bg-white/10 transition-colors text-sm font-bold"
          title="Zoom mas"
        >
          +
        </button>
      </div>
    </div>
  );
}

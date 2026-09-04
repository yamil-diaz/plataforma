import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import * as pdfjsLib from 'pdfjs-dist';

// Configure PDF.js worker (same as PDFViewer)
pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.js',
  import.meta.url
).toString();

const THUMBNAIL_WIDTH = 120;
const THUMBNAIL_SCALE = 0.2; // Low scale for thumbnails
const BATCH_SIZE = 8; // Render this many thumbnails per batch

/**
 * ThumbnailSidebar — Panel lateral con miniaturas de todas las páginas del PDF.
 *
 * Props:
 *   pdfDocument  — PDF.js document instance (pre-loaded)
 *   pdfUrl       — URL del PDF (fallback if pdfDocument not provided)
 *   totalPages   — Total de páginas
 *   currentPage  — Página actual (1-indexed)
 *   onPageSelect — callback(pageNumber) al hacer clic en una miniatura
 *   visible      — si el sidebar está visible
 */
export default function ThumbnailSidebar({
  pdfDocument,
  pdfUrl,
  totalPages,
  currentPage,
  onPageSelect,
  onClose,
  visible = true,
}) {
  const scrollRef = useRef(null);
  const [renderedPages, setRenderedPages] = useState(new Set());
  const [loadedDoc, setLoadedDoc] = useState(null);
  const loadingDocRef = useRef(false);

  // Load PDF independently if no document provided
  useEffect(() => {
    if (pdfDocument) {
      setLoadedDoc(pdfDocument);
      return;
    }
    if (!pdfUrl || loadedDoc || loadingDocRef.current) return;

    let cancelled = false;
    loadingDocRef.current = true;

    const load = async () => {
      try {
        const doc = await pdfjsLib.getDocument(pdfUrl).promise;
        if (!cancelled) setLoadedDoc(doc);
      } catch (err) {
        console.error('ThumbnailSidebar: error loading PDF:', err);
      } finally {
        loadingDocRef.current = false;
      }
    };

    load();
    return () => { cancelled = true; };
  }, [pdfDocument, pdfUrl]);

  // Reset rendered pages when document changes
  useEffect(() => {
    setRenderedPages(new Set());
  }, [loadedDoc]);

  // Scroll active thumbnail into view
  useEffect(() => {
    if (!visible) return;
    const container = scrollRef.current;
    const activeEl = container?.querySelector('[data-active="true"]');
    if (activeEl && container) {
      const containerRect = container.getBoundingClientRect();
      const elRect = activeEl.getBoundingClientRect();
      if (elRect.top < containerRect.top || elRect.bottom > containerRect.bottom) {
        activeEl.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }
    }
  }, [currentPage, visible]);

  // Render a single thumbnail on a canvas
  const renderThumbnail = useCallback(async (pageNum, canvas) => {
    if (!loadedDoc || !canvas) return;
    if (pageNum < 1 || pageNum > loadedDoc.numPages) return;

    try {
      const page = await loadedDoc.getPage(pageNum);
      const viewport = page.getViewport({ scale: THUMBNAIL_SCALE });

      const canvasEl = canvas;
      canvasEl.width = viewport.width;
      canvasEl.height = viewport.height;

      const ctx = canvasEl.getContext('2d');
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, canvasEl.width, canvasEl.height);

      await page.render({
        canvasContext: ctx,
        viewport: viewport,
      }).promise;

      setRenderedPages((prev) => new Set([...prev, pageNum]));
    } catch (err) {
      console.error(`Error rendering thumbnail for page ${pageNum}:`, err);
    }
  }, [loadedDoc]);

  // Lazy render: observe which thumbnails are visible
  useEffect(() => {
    if (!loadedDoc || !visible) return;

    const container = scrollRef.current;
    if (!container) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const pageNum = parseInt(entry.target.dataset.page, 10);
            const canvas = entry.target.querySelector('canvas');
            if (canvas && !renderedPages.has(pageNum)) {
              renderThumbnail(pageNum, canvas);
            }
          }
        });
      },
      {
        root: container,
        rootMargin: '200px', // Pre-render 200px outside viewport
      }
    );

    // Observe all thumbnail containers
    const items = container.querySelectorAll('[data-page]');
    items.forEach((item) => observer.observe(item));

    return () => observer.disconnect();
  }, [loadedDoc, visible, totalPages, renderThumbnail]);

  // Pages to display
  const pages = useMemo(() => {
    const arr = [];
    for (let i = 1; i <= (totalPages || 0); i++) arr.push(i);
    return arr;
  }, [totalPages]);

  if (!visible) return null;

  return (
    <>
      {/* Sidebar */}
      <div className="
        w-[140px] sm:w-[150px] md:w-[160px] shrink-0 bg-[#0f0f0f] border-r border-white/10 flex flex-col h-full
        max-md:fixed max-md:top-0 max-md:left-0 max-md:bottom-0 max-md:z-40 max-md:shadow-2xl max-md:w-[180px]
      ">
        {/* Header */}
        <div className="px-3 py-3 border-b border-white/10">
          <span className="text-xs font-semibold text-[#A0A0A0] tracking-wider uppercase">
            Paginas
          </span>
        </div>

        {/* Thumbnail list */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto px-2 py-2 space-y-2"
          style={{ scrollBehavior: 'smooth' }}
        >
          {pages.map((num) => {
            const isActive = num === currentPage;
            return (
              <div
                key={num}
                data-page={num}
                data-active={isActive}
                onClick={() => {
                  if (onPageSelect) onPageSelect(num);
                  // Auto-close sidebar on mobile after selection
                  if (onClose && window.innerWidth < 768) onClose();
                }}
                className={`relative cursor-pointer rounded-md overflow-hidden transition-all duration-150 ${
                  isActive
                    ? 'ring-2 ring-[#D92B2B] ring-offset-1 ring-offset-[#0f0f0f]'
                    : 'ring-1 ring-white/5 hover:ring-white/20'
                }`}
              >
                {/* Canvas placeholder */}
                <canvas
                  className="w-full block bg-white"
                  style={{ aspectRatio: '0.707' }} // A4 ratio
                />

                {/* Page number badge */}
                <div
                  className={`absolute bottom-0 left-0 right-0 text-center py-0.5 text-[10px] font-medium ${
                    isActive
                      ? 'bg-[#D92B2B] text-white'
                      : 'bg-black/60 text-[#A0A0A0]'
                  }`}
                >
                  {num}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}

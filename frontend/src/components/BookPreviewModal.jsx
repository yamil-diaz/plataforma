import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { X, ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Eye } from 'lucide-react';
import * as pdfjsLib from 'pdfjs-dist';

pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.js',
  import.meta.url
).toString();

const THUMBNAIL_SCALE = 0.2;

export default function BookPreviewModal({ pdfUrl, bookTitle, onClose }) {
  const [pdfDoc, setPdfDoc] = useState(null);
  const [totalPages, setTotalPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [zoom, setZoom] = useState(1.0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [renderedThumbs, setRenderedThumbs] = useState(new Set());
  const [renderError, setRenderError] = useState(null);

  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const renderingRef = useRef(false);
  const renderRequestRef = useRef(0);
  const pageCacheRef = useRef(new Map());
  const thumbScrollRef = useRef(null);
  const containerWidthRef = useRef(0);
  const containerHeightRef = useRef(0);
  const [containerWidth, setContainerWidth] = useState(0);
  const currentPageRef = useRef(currentPage);

  useEffect(() => { currentPageRef.current = currentPage; }, [currentPage]);

  // Load PDF
  useEffect(() => {
    if (!pdfUrl) return;
    let cancelled = false;
    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        const doc = await pdfjsLib.getDocument({
          url: pdfUrl,
          rangeChunkSize: 65536,
          disableAutoFetch: false,
          disableStream: false,
        }).promise;
        if (cancelled) return;
        setPdfDoc(doc);
        setTotalPages(doc.numPages);
        setLoading(false);
      } catch (err) {
        if (cancelled) return;
        setError(err.message || 'Error al cargar el PDF');
        setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; if (pdfDoc) pdfDoc.destroy(); };
  }, [pdfUrl]);

  // Container resize — uses ref for stable width tracking
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const updateDimensions = () => {
      const w = container.clientWidth;
      const h = container.clientHeight;
      if (w > 0) {
        containerWidthRef.current = w;
        setContainerWidth(w);
      }
      if (h > 0) {
        containerHeightRef.current = h;
      }
    };

    // Initial measurement
    updateDimensions();

    const obs = new ResizeObserver(() => {
      updateDimensions();
    });
    obs.observe(container);
    return () => obs.disconnect();
  }, [loading, pdfDoc]);

  // Render page — core fix: request ID, guard on containerWidth, error display
  const renderPage = useCallback(async (pageNum) => {
    const cw = containerWidthRef.current;
    if (!pdfDoc || !canvasRef.current || cw <= 0) return;
    if (pageNum < 1 || pageNum > pdfDoc.numPages) return;

    // Cancel any previous in-flight render
    const requestId = ++renderRequestRef.current;
    renderingRef.current = true;
    setRenderError(null);

    try {
      let pageData = pageCacheRef.current.get(pageNum);
      if (!pageData) {
        const page = await pdfDoc.getPage(pageNum);
        // Check if this render was superseded while awaiting page
        if (requestId !== renderRequestRef.current) return;
        const unscaled = page.getViewport({ scale: 1 });
        pageData = { page, w: unscaled.width, h: unscaled.height };
        if (pageCacheRef.current.size > 15) {
          const keys = Array.from(pageCacheRef.current.keys());
          if (keys.length > 0) pageCacheRef.current.delete(keys[0]);
        }
        pageCacheRef.current.set(pageNum, pageData);
      }

      const { page, w, h } = pageData;
      const maxW = cw - 32;
      const ch = containerHeightRef.current;
      const maxH = ch > 0 ? ch - 80 : 0;
      if (maxW <= 0) return;
      const scaleW = maxW / w;
      const scaleH = maxH > 0 ? maxH / h : Infinity;
      const scale = Math.min(scaleW, scaleH) * zoom;
      const vp = page.getViewport({ scale });

      // Check again before painting
      if (requestId !== renderRequestRef.current) return;

      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      canvas.width = vp.width;
      canvas.height = vp.height;
      canvas.style.width = vp.width + 'px';
      canvas.style.height = vp.height + 'px';
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      await page.render({ canvasContext: ctx, viewport: vp }).promise;

      // Final check — only mark done if still the latest request
      if (requestId === renderRequestRef.current) {
        renderingRef.current = false;
      }
    } catch (err) {
      console.error('Preview render error:', err);
      if (requestId === renderRequestRef.current) {
        renderingRef.current = false;
        setRenderError(err.message || 'Error al renderizar la página');
        // Paint error on canvas so it's not blank
        const canvas = canvasRef.current;
        if (canvas) {
          const ctx = canvas.getContext('2d');
          canvas.width = Math.max(cw - 32, 200);
          canvas.height = 200;
          canvas.style.width = canvas.width + 'px';
          canvas.style.height = '200px';
          ctx.fillStyle = '#1a1a1a';
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          ctx.fillStyle = '#ef4444';
          ctx.font = '14px sans-serif';
          ctx.textAlign = 'center';
          ctx.fillText('Error al renderizar', canvas.width / 2, 90);
          ctx.fillStyle = '#a0a0a0';
          ctx.font = '12px sans-serif';
          ctx.fillText(err.message || 'Error desconocido', canvas.width / 2, 115);
        }
      }
    }
  }, [pdfDoc, zoom]);

  // Re-render when containerWidth transitions from 0 to a real value
  useEffect(() => {
    if (containerWidth > 0 && pdfDoc && !loading) {
      renderPage(currentPage);
    }
  }, [containerWidth, pdfDoc, loading, renderPage, currentPage]);

  // Thumbnail rendering
  const renderThumb = useCallback(async (pageNum, canvas) => {
    if (!pdfDoc || !canvas) return;
    try {
      const page = await pdfDoc.getPage(pageNum);
      const vp = page.getViewport({ scale: THUMBNAIL_SCALE });
      canvas.width = vp.width;
      canvas.height = vp.height;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      await page.render({ canvasContext: ctx, viewport: vp }).promise;
      setRenderedThumbs((prev) => new Set([...prev, pageNum]));
    } catch (err) {
      console.error(`Thumb error page ${pageNum}:`, err);
    }
  }, [pdfDoc]);

  // Lazy thumbnails
  useEffect(() => {
    if (!pdfDoc || !sidebarOpen) return;
    const container = thumbScrollRef.current;
    if (!container) return;
    const obs = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const p = parseInt(entry.target.dataset.page, 10);
          const c = entry.target.querySelector('canvas');
          if (c && !renderedThumbs.has(p)) renderThumb(p, c);
        }
      });
    }, { root: container, rootMargin: '200px' });
    container.querySelectorAll('[data-page]').forEach((el) => obs.observe(el));
    return () => obs.disconnect();
  }, [pdfDoc, sidebarOpen, totalPages, renderThumb]);

  // Scroll active thumb into view
  useEffect(() => {
    if (!sidebarOpen) return;
    const container = thumbScrollRef.current;
    const active = container?.querySelector('[data-active="true"]');
    if (active && container) {
      const cr = container.getBoundingClientRect();
      const ar = active.getBoundingClientRect();
      if (ar.top < cr.top || ar.bottom > cr.bottom) {
        active.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }
    }
  }, [currentPage, sidebarOpen]);

  // Navigation
  const goPrev = () => { if (currentPage > 1) setCurrentPage(currentPage - 1); };
  const goNext = () => { if (currentPage < totalPages) setCurrentPage(currentPage + 1); };
  const zoomIn = () => setZoom((z) => Math.min(z + 0.1, 3.0));
  const zoomOut = () => setZoom((z) => Math.max(z - 0.1, 0.5));

  // Keyboard
  useEffect(() => {
    const handleKey = (e) => {
      if (e.key === 'Escape') { onClose(); return; }
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
      if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { e.preventDefault(); goPrev(); }
      else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') { e.preventDefault(); goNext(); }
      else if (e.key === '+' || e.key === '=') { e.preventDefault(); zoomIn(); }
      else if (e.key === '-') { e.preventDefault(); zoomOut(); }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  });

  // Prevent body scroll when modal is open
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
  }, []);

  const pages = useMemo(() => {
    const arr = [];
    for (let i = 1; i <= totalPages; i++) arr.push(i);
    return arr;
  }, [totalPages]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div
        className="relative bg-[#121212] border border-white/10 rounded-xl shadow-2xl flex flex-col w-[95vw] h-[90vh] max-w-[1200px]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 shrink-0">
          <div className="flex items-center gap-2 text-white font-semibold text-sm sm:text-base truncate">
            <Eye className="w-4 h-4 text-[#D4AF37] shrink-0" />
            <span className="truncate">Vista previa{bookTitle ? `: ${bookTitle}` : ''}</span>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded hover:bg-white/10 text-[#A0A0A0] hover:text-white transition-colors shrink-0"
            aria-label="Cerrar vista previa"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center text-[#A0A0A0]">
              <div className="animate-spin w-8 h-8 border-4 border-[#D4AF37] border-t-transparent rounded-full mx-auto mb-4"></div>
              Cargando vista previa...
            </div>
          </div>
        ) : error ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center text-red-400">
              <p className="mb-2">Error al cargar el PDF</p>
              <p className="text-sm text-[#A0A0A0]">{error}</p>
            </div>
          </div>
        ) : (
          <div className="flex flex-1 min-h-0">
            {/* Sidebar thumbnails */}
            {sidebarOpen && (
              <div className="
                w-[120px] sm:w-[130px] md:w-[140px] shrink-0 bg-[#0f0f0f] border-r border-white/10 flex flex-col
                max-md:fixed max-md:top-0 max-md:left-0 max-md:bottom-0 max-md:z-50 max-md:w-[160px] max-md:shadow-2xl
              ">
                <div className="px-3 py-2 border-b border-white/10">
                  <span className="text-[10px] font-semibold text-[#A0A0A0] tracking-wider uppercase">Paginas</span>
                </div>
                <div
                  ref={thumbScrollRef}
                  className="flex-1 overflow-y-auto px-1.5 py-2 space-y-1.5"
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
                          setCurrentPage(num);
                          if (window.innerWidth < 768) setSidebarOpen(false);
                        }}
                        className={`relative cursor-pointer rounded overflow-hidden transition-all duration-150 ${
                          isActive
                            ? 'ring-2 ring-[#D4AF37] ring-offset-1 ring-offset-[#0f0f0f]'
                            : 'ring-1 ring-white/5 hover:ring-white/20'
                        }`}
                      >
                        <canvas className="w-full block bg-white" style={{ aspectRatio: '0.707' }} />
                        <div className={`absolute bottom-0 left-0 right-0 text-center py-0.5 text-[9px] font-medium ${
                          isActive ? 'bg-[#D4AF37] text-black' : 'bg-black/60 text-[#A0A0A0]'
                        }`}>{num}</div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Main viewer area */}
            <div className="flex-1 flex flex-col min-w-0">
              {/* Viewer toolbar */}
              <div className="flex items-center justify-between gap-2 px-3 py-2 border-b border-white/10 bg-[#0f0f0f] shrink-0">
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => setSidebarOpen((p) => !p)}
                    className="w-8 h-8 flex items-center justify-center rounded bg-white/5 border border-white/10 text-[#A0A0A0] hover:text-white hover:bg-white/10 transition-colors"
                    title={sidebarOpen ? 'Ocultar miniaturas' : 'Mostrar miniaturas'}
                  >
                    {sidebarOpen ? (
                      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="9" y1="3" x2="9" y2="21"/></svg>
                    ) : (
                      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/></svg>
                    )}
                  </button>
                  <button
                    onClick={goPrev}
                    disabled={currentPage <= 1}
                    className="w-8 h-8 flex items-center justify-center rounded bg-white/5 border border-white/10 text-[#A0A0A0] hover:text-white hover:bg-white/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <span className="text-xs text-[#A0A0A0] font-mono min-w-[80px] text-center">
                    Pag {currentPage} de {totalPages}
                  </span>
                  <button
                    onClick={goNext}
                    disabled={currentPage >= totalPages}
                    className="w-8 h-8 flex items-center justify-center rounded bg-white/5 border border-white/10 text-[#A0A0A0] hover:text-white hover:bg-white/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={zoomOut}
                    disabled={zoom <= 0.5}
                    className="w-8 h-8 flex items-center justify-center rounded bg-white/5 border border-white/10 text-[#A0A0A0] hover:text-white hover:bg-white/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    <ZoomOut className="w-4 h-4" />
                  </button>
                  <span className="text-xs text-[#A0A0A0] font-mono min-w-[40px] text-center">
                    {Math.round(zoom * 100)}%
                  </span>
                  <button
                    onClick={zoomIn}
                    disabled={zoom >= 3.0}
                    className="w-8 h-8 flex items-center justify-center rounded bg-white/5 border border-white/10 text-[#A0A0A0] hover:text-white hover:bg-white/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    <ZoomIn className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Canvas area */}
              <div
                ref={containerRef}
                className="flex-1 flex items-center justify-center overflow-hidden bg-[#1a1a1a]"
                style={{ minHeight: 0 }}
              >
                <canvas ref={canvasRef} className="shadow-2xl max-w-full" />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

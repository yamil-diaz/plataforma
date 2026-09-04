import React, { useState, useEffect, useRef } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react';

/**
 * ReaderToolbar — Barra de herramientas del lector PDF.
 *
 * Props:
 *   currentPage      — Página actual (1-indexed)
 *   totalPages       — Total de páginas
 *   onPageChange     — callback(pageNumber) al cambiar de página
 *   zoom             — Nivel de zoom (1.0 = 100%)
 *   onZoomChange     — callback(newZoom) al cambiar zoom
 *   sidebarVisible   — Si el sidebar de miniaturas está visible
 *   onToggleSidebar  — callback() para mostrar/ocultar sidebar
 */
export default function ReaderToolbar({
  currentPage = 1,
  totalPages = 0,
  onPageChange,
  zoom = 1.0,
  onZoomChange,
  sidebarVisible = false,
  onToggleSidebar,
}) {
  const [inputValue, setInputValue] = useState(String(currentPage));
  const [isEditing, setIsEditing] = useState(false);
  const inputRef = useRef(null);

  // Sync input when currentPage changes externally
  useEffect(() => {
    if (!isEditing) {
      setInputValue(String(currentPage));
    }
  }, [currentPage, isEditing]);

  const handleInputChange = (e) => {
    const val = e.target.value.replace(/[^0-9]/g, '');
    setInputValue(val);
  };

  const handleInputFocus = () => {
    setIsEditing(true);
    // Select all on focus
    if (inputRef.current) inputRef.current.select();
  };

  const handleInputBlur = () => {
    setIsEditing(false);
    // Reset to current page if invalid
    setInputValue(String(currentPage));
  };

  const handleInputKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      submitPageInput();
    } else if (e.key === 'Escape') {
      setIsEditing(false);
      setInputValue(String(currentPage));
      inputRef.current?.blur();
    }
  };

  const submitPageInput = () => {
    const num = parseInt(inputValue, 10);
    if (!isNaN(num) && num >= 1 && num <= totalPages && num !== currentPage) {
      if (onPageChange) onPageChange(num);
    } else {
      // Reset to current page
      setInputValue(String(currentPage));
    }
    setIsEditing(false);
    inputRef.current?.blur();
  };

  const goPrev = () => {
    if (currentPage > 1 && onPageChange) onPageChange(currentPage - 1);
  };

  const goNext = () => {
    if (currentPage < totalPages && onPageChange) onPageChange(currentPage + 1);
  };

  const zoomIn = () => {
    if (onZoomChange) onZoomChange(Math.min(zoom + 0.1, 3.0));
  };

  const zoomOut = () => {
    if (onZoomChange) onZoomChange(Math.max(zoom - 0.1, 0.5));
  };

  const isFirst = currentPage <= 1;
  const isLast = currentPage >= totalPages;

  return (
    <div className="flex items-center justify-between gap-1.5 sm:gap-2 px-2 sm:px-4 py-1.5 sm:py-2 bg-[#121212] border-t border-white/10 overflow-hidden">
      {/* Left: Sidebar toggle + Navigation */}
      <div className="flex items-center gap-1 sm:gap-2 shrink-0">
        {/* Sidebar toggle */}
        <button
          onClick={onToggleSidebar}
          className="w-9 h-9 sm:w-8 sm:h-8 flex items-center justify-center rounded bg-white/5 border border-white/10 text-[#A0A0A0] hover:text-white hover:bg-white/10 transition-colors"
          title={sidebarVisible ? 'Ocultar miniaturas' : 'Mostrar miniaturas'}
          aria-label={sidebarVisible ? 'Ocultar panel de miniaturas' : 'Mostrar panel de miniaturas'}
        >
          {sidebarVisible ? (
            <PanelLeftClose className="w-4 h-4" />
          ) : (
            <PanelLeftOpen className="w-4 h-4" />
          )}
        </button>

        {/* Previous page */}
        <button
          onClick={goPrev}
          disabled={isFirst}
          className="w-9 h-9 sm:w-8 sm:h-8 flex items-center justify-center rounded bg-white/5 border border-white/10 text-[#A0A0A0] hover:text-white hover:bg-white/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          title="Pagina anterior"
          aria-label="Pagina anterior"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        {/* Page input */}
        <div className="flex items-center gap-1 sm:gap-1.5">
          <input
            ref={inputRef}
            type="number"
            inputMode="numeric"
            pattern="[0-9]*"
            min={1}
            max={totalPages || undefined}
            value={inputValue}
            onChange={handleInputChange}
            onFocus={handleInputFocus}
            onBlur={handleInputBlur}
            onKeyDown={handleInputKeyDown}
            className="w-11 h-9 sm:w-12 sm:h-8 text-center text-sm font-mono bg-[#0A0A0A] border border-white/10 rounded text-[#F5F5F5] focus:outline-none focus:border-[#D92B2B] transition-colors"
            aria-label="Numero de pagina"
            aria-valuemin={1}
            aria-valuemax={totalPages}
            aria-valuenow={currentPage}
          />
          <span className="text-xs text-[#A0A0A0] hidden xs:inline">
            de {totalPages || '?'}
          </span>
        </div>

        {/* Next page */}
        <button
          onClick={goNext}
          disabled={isLast}
          className="w-9 h-9 sm:w-8 sm:h-8 flex items-center justify-center rounded bg-white/5 border border-white/10 text-[#A0A0A0] hover:text-white hover:bg-white/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          title="Pagina siguiente"
          aria-label="Pagina siguiente"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* Center: Zoom controls */}
      <div className="flex items-center gap-1 sm:gap-2 shrink-0">
        <button
          onClick={zoomOut}
          disabled={zoom <= 0.5}
          className="w-9 h-9 sm:w-8 sm:h-8 flex items-center justify-center rounded bg-white/5 border border-white/10 text-[#A0A0A0] hover:text-white hover:bg-white/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          title="Zoom menos"
          aria-label="Reducir zoom"
        >
          <ZoomOut className="w-4 h-4" />
        </button>

        <span className="text-xs text-[#A0A0A0] font-mono min-w-[40px] sm:min-w-[48px] text-center select-none">
          {Math.round(zoom * 100)}%
        </span>

        <button
          onClick={zoomIn}
          disabled={zoom >= 3.0}
          className="w-9 h-9 sm:w-8 sm:h-8 flex items-center justify-center rounded bg-white/5 border border-white/10 text-[#A0A0A0] hover:text-white hover:bg-white/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          title="Zoom mas"
          aria-label="Aumentar zoom"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
      </div>

      {/* Right: Spacer — hidden on mobile */}
      <div className="hidden md:block w-[140px] shrink-0" />
    </div>
  );
}

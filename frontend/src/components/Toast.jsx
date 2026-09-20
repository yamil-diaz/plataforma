import React, { useEffect } from 'react';
import { CheckCircle, AlertCircle, X } from 'lucide-react';

export default function Toast({ message, type = 'error', onClose, duration = 4000 }) {
  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(() => onClose(), duration);
    return () => clearTimeout(timer);
  }, [message, duration, onClose]);

  if (!message) return null;

  const styles = type === 'success'
    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
    : 'bg-[#D92B2B]/10 border-[#D92B2B]/30 text-[#F03C3C]';

  const Icon = type === 'success' ? CheckCircle : AlertCircle;

  return (
    <div className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-lg border backdrop-blur-md shadow-lg max-w-sm ${styles}`}>
      <Icon className="w-4 h-4 flex-shrink-0" />
      <span className="text-sm flex-1">{message}</span>
      <button onClick={onClose} className="p-0.5 hover:opacity-70 transition-opacity">
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}

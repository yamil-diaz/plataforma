import React from 'react';
import { AlertCircle } from 'lucide-react';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('[ErrorBoundary]', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center px-6">
          <div className="max-w-md text-center">
            <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-white mb-2">Algo salió mal</h2>
            <p className="text-[#A0A0A0] text-sm mb-6">
              Ocurrió un error inesperado. Por favor, recarga la página e intenta de nuevo.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="bg-[#D92B2B] hover:bg-[#F03C3C] text-white font-bold px-6 py-3 rounded-xl transition-all"
            >
              Recargar página
            </button>
            <button
              onClick={() => window.location.href = '/'}
              className="ml-3 bg-white/10 hover:bg-white/20 text-white font-bold px-6 py-3 rounded-xl transition-all"
            >
              Volver al inicio
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

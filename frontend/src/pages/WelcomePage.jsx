import React from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle, ArrowRight } from 'lucide-react';

export default function WelcomePage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center px-6">
      <div className="max-w-md text-center">
        <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-6" />
        <h1 className="text-3xl font-bold text-white mb-4">Bienvenido!</h1>
        <p className="text-[#A0A0A0] mb-8">
          Tu suscripcion ha sido procesada exitosamente. Ya tienes acceso a todo el contenido premium de AeternumLibrary.
        </p>
        <button
          onClick={() => navigate('/')}
          className="bg-[#D92B2B] hover:bg-[#F03C3C] text-white font-bold px-8 py-3 rounded-xl transition-all inline-flex items-center gap-2"
        >
          Explorar libros <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

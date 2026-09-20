import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Navbar } from '../components/Navbar';
import { Footer } from '../components/Footer';
import { CreditCard, Clock, Truck, BookOpen, Check } from 'lucide-react';
import { API } from '../config/api';

export default function PricingPage() {
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadBooks = async () => {
      try {
        const { data } = await axios.get(`${API}/books`);
        setBooks(data.filter(b => b.price > 0).slice(0, 6));
      } catch (error) {
        console.error('Error loading books:', error);
      } finally {
        setLoading(false);
      }
    };
    loadBooks();
  }, []);

  return (
    <div className="min-h-screen bg-[#0A0A0A] flex flex-col">
      <Navbar />
      <div className="flex-1 max-w-5xl w-full mx-auto p-6 py-12">
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl font-black text-white tracking-tight mb-4 font-['Outfit']">
            Precios
          </h1>
          <p className="text-[#A0A0A0] text-lg max-w-2xl mx-auto">
            Elige cómo disfrutar del contenido en AeternumLibrary.
          </p>
        </div>

        {/* Tipos de compra */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
          <div className="bg-[#121212] border border-white/10 rounded-2xl p-8 text-center">
            <CreditCard className="w-10 h-10 text-[#D92B2B] mx-auto mb-4" />
            <h3 className="text-xl font-bold text-white mb-2">Compra Digital</h3>
            <p className="text-[#A0A0A0] text-sm mb-4">Acceso permanente al libro en la plataforma.</p>
            <ul className="text-left space-y-2">
              <li className="flex items-center gap-2 text-sm text-[#CCCCCC]">
                <Check className="w-4 h-4 text-green-400" /> Acceso de por vida
              </li>
              <li className="flex items-center gap-2 text-sm text-[#CCCCCC]">
                <Check className="w-4 h-4 text-green-400" /> Lee en cualquier dispositivo
              </li>
              <li className="flex items-center gap-2 text-sm text-[#CCCCCC]">
                <Check className="w-4 h-4 text-green-400" /> Multi-monedas (USD, PEN, EUR, etc.)
              </li>
            </ul>
          </div>

          <div className="bg-[#121212] border border-[#D4AF37]/30 rounded-2xl p-8 text-center relative">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-[#D4AF37] text-black text-xs font-bold px-3 py-1 rounded-full">
              AHORRA
            </div>
            <Clock className="w-10 h-10 text-[#D4AF37] mx-auto mb-4" />
            <h3 className="text-xl font-bold text-white mb-2">Alquiler Digital</h3>
            <p className="text-[#A0A0A0] text-sm mb-4">Acceso temporal por 7, 14 o 30 días.</p>
            <ul className="text-left space-y-2">
              <li className="flex items-center gap-2 text-sm text-[#CCCCCC]">
                <Check className="w-4 h-4 text-green-400" /> 30% del precio de compra
              </li>
              <li className="flex items-center gap-2 text-sm text-[#CCCCCC]">
                <Check className="w-4 h-4 text-green-400" /> Elige la duración
              </li>
              <li className="flex items-center gap-2 text-sm text-[#CCCCCC]">
                <Check className="w-4 h-4 text-green-400" /> Ideal para lectura rápida
              </li>
            </ul>
          </div>

          <div className="bg-[#121212] border border-white/10 rounded-2xl p-8 text-center">
            <Truck className="w-10 h-10 text-green-400 mx-auto mb-4" />
            <h3 className="text-xl font-bold text-white mb-2">Compra Física</h3>
            <p className="text-[#A0A0A0] text-sm mb-4">Libro físico enviado a tu dirección en Perú.</p>
            <ul className="text-left space-y-2">
              <li className="flex items-center gap-2 text-sm text-[#CCCCCC]">
                <Check className="w-4 h-4 text-green-400" /> Envío a todo Perú
              </li>
              <li className="flex items-center gap-2 text-sm text-[#CCCCCC]">
                <Check className="w-4 h-4 text-green-400" /> Pago en Soles (PEN)
              </li>
              <li className="flex items-center gap-2 text-sm text-[#CCCCCC]">
                <Check className="w-4 h-4 text-green-400" /> Seguimiento del pedido
              </li>
            </ul>
          </div>
        </div>

        {/* Ejemplos de precios */}
        <div className="text-center mb-8">
          <h2 className="text-2xl font-bold text-white mb-2">Ejemplos de Precios</h2>
          <p className="text-[#A0A0A0] text-sm">Los precios varían por libro y moneda.</p>
        </div>

        {loading ? (
          <p className="text-center text-[#A0A0A0]">Cargando libros...</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {books.map(book => (
              <div key={book.id} className="bg-[#121212] border border-white/5 rounded-xl p-4 flex gap-4">
                <img
                  src={book.cover_image_url || "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400"}
                  alt={book.title}
                  className="w-14 h-20 object-cover rounded-lg flex-shrink-0"
                />
                <div>
                  <h4 className="text-white text-sm font-semibold line-clamp-1">{book.title}</h4>
                  <p className="text-[#A0A0A0] text-xs">{book.author_name}</p>
                  <p className="text-[#D4AF37] font-bold text-sm mt-2">${book.price.toFixed(2)}</p>
                  <p className="text-[#606060] text-xs">Alquiler: ${(book.price * 0.3).toFixed(2)}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      <Footer />
    </div>
  );
}

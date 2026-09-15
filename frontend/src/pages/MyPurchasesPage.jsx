import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { Navbar } from '../components/Navbar';
import { useAuth } from '../contexts/AuthContext';
import { API } from '../config/api';
import { ShoppingBag, CreditCard, Clock, Truck, Package, Eye } from 'lucide-react';

export default function MyPurchasesPage() {
  const { user } = useAuth();
  const [purchases, setPurchases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    loadPurchases();
  }, []);

  const loadPurchases = async () => {
    try {
      const { data } = await axios.get(`${API}/user/purchases`);
      setPurchases(data);
    } catch (err) {
      console.error('Error loading purchases:', err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusStyle = (status) => {
    switch (status) {
      case 'approved': return 'bg-green-500/10 text-green-400 border-green-500/30';
      case 'pending': return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30';
      case 'rejected': return 'bg-red-500/10 text-red-400 border-red-500/30';
      case 'cancelled': return 'bg-gray-500/10 text-gray-400 border-gray-500/30';
      default: return 'bg-white/5 text-[#A0A0A0] border-white/10';
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'approved': return 'Pagado';
      case 'pending': return 'Pendiente';
      case 'rejected': return 'Rechazado';
      case 'cancelled': return 'Cancelado';
      default: return status;
    }
  };

  const getTypeIcon = (type) => {
    switch (type) {
      case 'digital_purchase': return <CreditCard className="w-4 h-4" />;
      case 'digital_rental': return <Clock className="w-4 h-4" />;
      case 'physical_purchase': return <Truck className="w-4 h-4" />;
      default: return <ShoppingBag className="w-4 h-4" />;
    }
  };

  const getTypeLabel = (type) => {
    switch (type) {
      case 'digital_purchase': return 'Digital';
      case 'digital_rental': return 'Alquiler';
      case 'physical_purchase': return 'Físico';
      default: return type;
    }
  };

  const filtered = filter === 'all' ? purchases : purchases.filter(p => p.order_type === filter);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center text-[#A0A0A0]">
        Cargando compras...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      <Navbar />
      <div className="max-w-5xl mx-auto px-6 py-12">
        <h1 className="text-3xl font-bold text-white mb-2 font-['Outfit']">Mis Compras</h1>
        <p className="text-[#A0A0A0] mb-8">Historial de todas tus compras</p>

        {/* Filtros */}
        <div className="flex gap-2 mb-6 flex-wrap">
          {[
            { key: 'all', label: 'Todas' },
            { key: 'digital_purchase', label: 'Digitales' },
            { key: 'digital_rental', label: 'Alquileres' },
            { key: 'physical_purchase', label: 'Físicos' },
          ].map(f => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`px-4 py-2 rounded-full text-sm font-semibold transition-all ${
                filter === f.key
                  ? 'bg-[#D92B2B] text-white'
                  : 'bg-white/5 text-[#A0A0A0] hover:bg-white/10 border border-white/10'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {filtered.length === 0 ? (
          <div className="text-center py-20">
            <ShoppingBag className="w-16 h-16 text-[#A0A0A0] mx-auto mb-4" />
            <p className="text-[#A0A0A0] text-lg mb-4">No tienes compras registradas</p>
            <Link to="/" className="text-[#D92B2B] hover:underline font-semibold">
              Explorar catálogo
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {filtered.map(p => (
              <div key={p.id} className="bg-[#121212] border border-white/10 rounded-2xl p-5 hover:border-white/20 transition-all">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex gap-4">
                    {p.cover_image_url && (
                      <img src={p.cover_image_url} alt="" className="w-12 h-16 object-cover rounded-lg flex-shrink-0" />
                    )}
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        {getTypeIcon(p.order_type)}
                        <span className="text-sm text-[#A0A0A0]">{getTypeLabel(p.order_type)}</span>
                      </div>
                      <h3 className="text-white font-semibold">{p.book_title || 'Libro'}</h3>
                      <p className="text-[#A0A0A0] text-xs mt-1">#{p.order_number}</p>
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className="text-[#D4AF37] font-bold">S/ {parseFloat(p.total).toFixed(2)}</p>
                    <span className={`inline-block mt-1 px-2 py-0.5 rounded-full text-xs border ${getStatusStyle(p.payment_status)}`}>
                      {getStatusLabel(p.payment_status)}
                    </span>
                  </div>
                </div>
                <div className="flex items-center justify-between mt-3 pt-3 border-t border-white/5">
                  <span className="text-xs text-[#A0A0A0]">
                    {new Date(p.created_at).toLocaleDateString('es-PE', {
                      day: '2-digit', month: 'short', year: 'numeric'
                    })}
                  </span>
                  {p.payment_status === 'approved' && p.order_type === 'digital_purchase' && (
                    <Link to={`/books/${p.book_id}`} className="text-xs text-[#D92B2B] hover:underline flex items-center gap-1">
                      <Eye className="w-3 h-3" /> Leer libro
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

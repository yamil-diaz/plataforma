import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { Navbar } from '../components/Navbar';
import { API } from '../config/api';
import { Package, Truck, CheckCircle, Clock, ExternalLink } from 'lucide-react';

export default function MyPhysicalOrdersPage() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadOrders();
  }, []);

  const loadOrders = async () => {
    try {
      const { data } = await axios.get(`${API}/user/physical-orders`);
      setOrders(data);
    } catch (err) {
      console.error('Error loading physical orders:', err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'delivered': return <CheckCircle className="w-5 h-5 text-green-400" />;
      case 'shipped': return <Truck className="w-5 h-5 text-blue-400" />;
      case 'preparing': return <Package className="w-5 h-5 text-yellow-400" />;
      default: return <Clock className="w-5 h-5 text-[#A0A0A0]" />;
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'pending': return 'Pendiente';
      case 'preparing': return 'Preparando';
      case 'shipped': return 'Enviado';
      case 'delivered': return 'Entregado';
      case 'cancelled': return 'Cancelado';
      default: return status;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center text-[#A0A0A0]">
        Cargando pedidos...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      <Navbar />
      <div className="max-w-5xl mx-auto px-6 py-12">
        <h1 className="text-3xl font-bold text-white mb-2 font-['Outfit']">Mis Pedidos Físicos</h1>
        <p className="text-[#A0A0A0] mb-8">Seguimiento de tus pedidos físicos</p>

        {orders.length === 0 ? (
          <div className="text-center py-20">
            <Package className="w-16 h-16 text-[#A0A0A0] mx-auto mb-4" />
            <p className="text-[#A0A0A0] text-lg mb-4">No tienes pedidos físicos</p>
            <Link to="/" className="text-[#D92B2B] hover:underline font-semibold">
              Explorar catálogo
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {orders.map(o => (
              <div key={o.id} className="bg-[#121212] border border-white/10 rounded-2xl p-6">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      {getStatusIcon(o.fulfillment_status)}
                      <span className="text-white font-bold">Pedido #{o.order_number}</span>
                    </div>
                    <p className="text-[#A0A0A0] text-sm">{o.book_title}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-[#D4AF37] font-bold">S/ {parseFloat(o.total).toFixed(2)}</p>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      o.fulfillment_status === 'delivered' ? 'bg-green-500/10 text-green-400' :
                      o.fulfillment_status === 'shipped' ? 'bg-blue-500/10 text-blue-400' :
                      'bg-yellow-500/10 text-yellow-400'
                    }`}>
                      {getStatusLabel(o.fulfillment_status)}
                    </span>
                  </div>
                </div>

                <div className="bg-[#0A0A0A] rounded-xl p-4 text-sm space-y-2">
                  <div className="flex justify-between">
                    <span className="text-[#A0A0A0]">Transportista</span>
                    <span className="text-white">{o.carrier || 'Shalom'}</span>
                  </div>
                  {o.tracking_number && (
                    <div className="flex justify-between">
                      <span className="text-[#A0A0A0]">Tracking</span>
                      <span className="text-white font-mono">{o.tracking_number}</span>
                    </div>
                  )}
                  {o.shipped_at && (
                    <div className="flex justify-between">
                      <span className="text-[#A0A0A0]">Enviado</span>
                      <span className="text-white">{new Date(o.shipped_at).toLocaleDateString('es-PE')}</span>
                    </div>
                  )}
                  {o.delivered_at && (
                    <div className="flex justify-between">
                      <span className="text-[#A0A0A0]">Entregado</span>
                      <span className="text-white">{new Date(o.delivered_at).toLocaleDateString('es-PE')}</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span className="text-[#A0A0A0]">Fecha de compra</span>
                    <span className="text-white">{new Date(o.created_at).toLocaleDateString('es-PE')}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

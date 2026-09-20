import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { Navbar } from '../components/Navbar';
import { API } from '../config/api';
import { ArrowLeft, Download, CreditCard, Clock, Truck, Package, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

export default function OrderDetailPage() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchOrder();
  }, [orderId]);

  const fetchOrder = async () => {
    try {
      const { data } = await axios.get(`${API}/checkout/${orderId}`, { withCredentials: true });
      setOrder(data);
    } catch (err) {
      console.error('Error loading order:', err);
      setError('No se pudo cargar la orden.');
    } finally {
      setLoading(false);
    }
  };

  const getCurrencySymbol = (currency) => {
    const symbols = { PEN: 'S/', USD: '$', CLP: '$' };
    return symbols[currency] || currency || 'S/';
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'approved': return <CheckCircle className="w-5 h-5 text-green-400" />;
      case 'rejected': return <XCircle className="w-5 h-5 text-red-400" />;
      case 'pending': return <AlertCircle className="w-5 h-5 text-yellow-400" />;
      default: return <Clock className="w-5 h-5 text-[#A0A0A0]" />;
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

  const getTypeLabel = (type) => {
    switch (type) {
      case 'digital_purchase': return 'Compra Digital';
      case 'digital_rental': return 'Alquiler Digital';
      case 'physical_purchase': return 'Compra Fisica';
      default: return type;
    }
  };

  const getPaymentMethodLabel = (provider) => {
    switch (provider) {
      case 'paddle': return 'Paddle';
      case 'culqi': return 'Culqi';
      case 'flow': return 'Flow';
      default: return provider || 'Desconocido';
    }
  };

  const handlePrint = () => {
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`<!DOCTYPE html>
<html><head><title>Recibo ${order.order_number}</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: Arial, sans-serif; padding: 40px; color: #1a1a1a; }
  .receipt { max-width: 600px; margin: 0 auto; }
  .header { text-align: center; margin-bottom: 30px; border-bottom: 2px solid #D92B2B; padding-bottom: 20px; }
  .header h1 { font-size: 24px; color: #D92B2B; margin-bottom: 5px; }
  .header p { color: #666; font-size: 14px; }
  .info { display: flex; justify-content: space-between; margin-bottom: 15px; padding: 10px 0; border-bottom: 1px solid #eee; }
  .info .label { color: #666; font-size: 13px; }
  .info .value { font-weight: bold; font-size: 14px; }
  .item { background: #f9f9f9; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
  .item h3 { font-size: 16px; margin-bottom: 5px; }
  .item p { font-size: 13px; color: #666; }
  .total { text-align: right; margin-top: 20px; padding-top: 15px; border-top: 2px solid #333; }
  .total .amount { font-size: 24px; font-weight: bold; color: #D92B2B; }
  .footer { text-align: center; margin-top: 30px; font-size: 12px; color: #999; }
</style></head><body>
<div class="receipt">
  <div class="header">
    <h1>AeternumLibrary</h1>
    <p>Recibo de compra</p>
  </div>
  <div class="info"><span class="label">Numero de orden</span><span class="value">${order.order_number}</span></div>
  <div class="info"><span class="label">Fecha</span><span class="value">${new Date(order.created_at).toLocaleDateString('es-PE', { day: '2-digit', month: 'long', year: 'numeric' })}</span></div>
  <div class="info"><span class="label">Estado</span><span class="value">${getStatusLabel(order.payment_status)}</span></div>
  <div class="info"><span class="label">Metodo de pago</span><span class="value">${getPaymentMethodLabel(order.provider)}</span></div>
  <div class="info"><span class="label">Tipo</span><span class="value">${getTypeLabel(order.order_type)}</span></div>
  <div class="item">
    <h3>${order.book_title || 'Libro'}</h3>
    <p>${getCurrencySymbol(order.currency)} ${parseFloat(order.total).toFixed(2)} ${order.currency}</p>
  </div>
  <div class="total">
    <span class="label">Total</span><br>
    <span class="amount">${getCurrencySymbol(order.currency)} ${parseFloat(order.total).toFixed(2)}</span>
  </div>
  <div class="footer">AeternumLibrary - La primera plataforma donde la lectura tiene recompensas</div>
</div>
<script>window.onload=function(){window.print();window.close();}</script>
</body></html>`);
    printWindow.document.close();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center text-[#A0A0A0]">
        Cargando orden...
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="min-h-screen bg-[#0A0A0A]">
        <Navbar />
        <div className="max-w-3xl mx-auto px-6 py-12 text-center">
          <AlertCircle className="w-16 h-16 text-red-400 mx-auto mb-4" />
          <p className="text-red-400 text-lg mb-4">{error || 'Orden no encontrada'}</p>
          <button onClick={() => navigate('/mis-compras')} className="text-[#D92B2B] hover:underline font-semibold">
            Volver a Mis Compras
          </button>
        </div>
      </div>
    );
  }

  return (
    <>
      <style>{`
        @media print {
          body * { visibility: hidden; }
          #print-area, #print-area * { visibility: visible; }
          #print-area { position: absolute; left: 0; top: 0; width: 100%; }
        }
      `}</style>
      <div className="min-h-screen bg-[#0A0A0A]">
        <Navbar />
        <div className="max-w-3xl mx-auto px-6 py-12" id="print-area">
          <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-[#A0A0A0] hover:text-white mb-6 text-sm">
            <ArrowLeft className="w-4 h-4" /> Volver
          </button>

          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
            <div>
              <h1 className="text-2xl font-bold text-white font-['Outfit']">Orden #{order.order_number}</h1>
              <p className="text-[#A0A0A0] text-sm mt-1">
                {new Date(order.created_at).toLocaleDateString('es-PE', { day: '2-digit', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
              </p>
            </div>
            {order.payment_status === 'approved' && (
              <button onClick={handlePrint} className="flex items-center gap-2 bg-[#D92B2B] hover:bg-[#b82424] text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors">
                <Download className="w-4 h-4" /> Descargar recibo
              </button>
            )}
          </div>

          <div className="bg-[#121212] border border-white/10 rounded-2xl p-6 mb-6">
            <div className="flex items-center gap-3 mb-6">
              {getStatusIcon(order.payment_status)}
              <div>
                <p className="text-white font-semibold">{getStatusLabel(order.payment_status)}</p>
                <p className="text-[#A0A0A0] text-xs">{getTypeLabel(order.order_type)}</p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="bg-white/5 rounded-xl p-4">
                <p className="text-[#A0A0A0] text-xs mb-1">Metodo de pago</p>
                <div className="flex items-center gap-2 text-white">
                  <CreditCard className="w-4 h-4 text-[#D4AF37]" />
                  <span className="font-semibold">{getPaymentMethodLabel(order.provider)}</span>
                </div>
              </div>
              <div className="bg-white/5 rounded-xl p-4">
                <p className="text-[#A0A0A0] text-xs mb-1">Moneda</p>
                <p className="text-white font-semibold">{order.currency}</p>
              </div>
            </div>
          </div>

          <div className="bg-[#121212] border border-white/10 rounded-2xl p-6 mb-6">
            <h2 className="text-white font-semibold mb-4">Detalle del articulo</h2>
            <div className="flex items-center gap-4">
              <div className="w-16 h-22 bg-white/10 rounded-lg flex-shrink-0 flex items-center justify-center">
                <Package className="w-6 h-6 text-[#A0A0A0]" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-white font-semibold truncate">{order.book_title || 'Libro'}</p>
                <p className="text-[#A0A0A0] text-sm mt-1">
                  {order.order_type === 'digital_rental' && order.rental_days
                    ? `Alquiler - ${order.rental_days} dias`
                    : getTypeLabel(order.order_type)}
                </p>
              </div>
              <div className="text-right flex-shrink-0">
                <p className="text-[#D4AF37] text-lg font-bold">{getCurrencySymbol(order.currency)} {parseFloat(order.total).toFixed(2)}</p>
              </div>
            </div>
          </div>

          <div className="bg-[#121212] border border-white/10 rounded-2xl p-6">
            <h2 className="text-white font-semibold mb-4">Resumen</h2>
            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-[#A0A0A0]">Subtotal</span>
                <span className="text-white">{getCurrencySymbol(order.currency)} {parseFloat(order.total).toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-[#A0A0A0]">Impuestos</span>
                <span className="text-white">{getCurrencySymbol(order.currency)} 0.00</span>
              </div>
              <div className="flex justify-between font-bold border-t border-white/10 pt-3">
                <span className="text-white">Total</span>
                <span className="text-[#D4AF37] text-lg">{getCurrencySymbol(order.currency)} {parseFloat(order.total).toFixed(2)}</span>
              </div>
            </div>
          </div>

          {order.payment_status === 'approved' && (
            <div className="mt-6 text-center">
              <Link to="/mis-compras" className="text-[#D92B2B] hover:underline text-sm font-semibold">
                Volver a Mis Compras
              </Link>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

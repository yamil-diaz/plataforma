import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Navbar } from '../components/Navbar';
import { API } from '../config/api';
import { CheckCircle, XCircle, Clock, AlertCircle } from 'lucide-react';

export default function PaymentResultPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState('loading');
  const [message, setMessage] = useState('');
  const [orderNumber, setOrderNumber] = useState('');

  const token = searchParams.get('token');
  const provider = searchParams.get('provider') || 'paddle';
  const ptxn = searchParams.get('_ptxn');
  const orderId = searchParams.get('order_id') || localStorage.getItem('paddle_pending_order_id');

  useEffect(() => {
    if (ptxn && orderId) {
      localStorage.removeItem('paddle_pending_order_id');
    }
  }, [ptxn, orderId]);

  useEffect(() => {
    // Paddle via _ptxn (retorno estándar de Paddle)
    if (ptxn) {
      if (orderId) {
        verifyOrderByStatus();
      } else {
        setStatus('pending');
        setMessage('Verificando pago...');
      }
      return;
    }
    // Paddle legacy: usar token
    if (provider === 'paddle' && token) {
      verifyPaddlePayment();
      return;
    }
    // Culqi u otro: verificar por order_id
    if (orderId) {
      verifyOrderByStatus();
      return;
    }
    setStatus('error');
    setMessage('Parámetros de pago no válidos');
  }, [ptxn, token, orderId, provider]);

  const verifyPaddlePayment = async () => {
    try {
      const { data } = await axios.get(`${API}/checkout/${orderId || ''}`);
      setStatus(data.payment_status || 'pending');
      setMessage(data.payment_status === 'approved' ? 'Pago procesado' : 'Pago no completado');
      setOrderNumber(data.order_number || '');
    } catch (err) {
      setStatus('error');
      setMessage(err.response?.data?.detail || 'Error al verificar el pago');
    }
  };

  const verifyOrderByStatus = async () => {
    try {
      const { data } = await axios.get(`${API}/checkout/${orderId}`);
      setStatus(data.payment_status || 'pending');
      setMessage(data.payment_status === 'approved' ? 'Pago procesado' : 'Pago no completado');
      setOrderNumber(data.order_number || '');
    } catch (err) {
      setStatus('error');
      setMessage(err.response?.data?.detail || 'Error al verificar el pago');
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'approved':
        return <CheckCircle className="w-20 h-20 text-green-400 mx-auto mb-6" />;
      case 'rejected':
      case 'cancelled':
      case 'expired':
        return <XCircle className="w-20 h-20 text-red-400 mx-auto mb-6" />;
      case 'pending':
        return <Clock className="w-20 h-20 text-yellow-400 mx-auto mb-6" />;
      default:
        return <AlertCircle className="w-20 h-20 text-[#A0A0A0] mx-auto mb-6" />;
    }
  };

  const getStatusTitle = () => {
    switch (status) {
      case 'approved': return 'Pago Aprobado';
      case 'rejected': return 'Pago Rechazado';
      case 'cancelled': return 'Pago Cancelado';
      case 'expired': return 'Pago Expirado';
      case 'pending': return 'Pago Pendiente';
      case 'loading': return 'Verificando pago...';
      default: return 'Error';
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      <Navbar />
      <div className="max-w-lg mx-auto px-6 py-20 text-center">
        {status === 'loading' ? (
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#D4AF37] mx-auto mb-6"></div>
        ) : (
          getStatusIcon()
        )}

        <h1 className="text-3xl font-bold text-white mb-4 font-['Outfit']">
          {getStatusTitle()}
        </h1>

        {message && (
          <p className="text-[#A0A0A0] mb-6">{message}</p>
        )}

        {orderNumber && (
          <div className="bg-[#121212] border border-white/10 rounded-xl p-4 mb-6 inline-block">
            <p className="text-sm text-[#A0A0A0]">Número de pedido</p>
            <p className="text-white font-mono font-bold">{orderNumber}</p>
          </div>
        )}

        <div className="flex flex-col gap-3 mt-8">
          {status === 'approved' && (
            <button
              onClick={() => navigate('/mis-libros')}
              className="w-full bg-[#D92B2B] hover:bg-[#F03C3C] text-white font-bold py-3 rounded-xl transition-all"
            >
              Ir a Mis Libros
            </button>
          )}
          <button
            onClick={() => navigate('/')}
            className="w-full bg-white/5 hover:bg-white/10 text-white font-semibold py-3 rounded-xl transition-all border border-white/10"
          >
            Volver al Catálogo
          </button>
        </div>
      </div>
    </div>
  );
}

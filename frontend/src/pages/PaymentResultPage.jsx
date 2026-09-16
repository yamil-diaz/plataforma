import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Navbar } from '../components/Navbar';
import { API } from '../config/api';
import { CheckCircle, XCircle, Clock, AlertCircle } from 'lucide-react';

const POLL_INTERVAL = 3000;
const MAX_POLLS = 20;

export default function PaymentResultPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState('loading');
  const [message, setMessage] = useState('');
  const [orderNumber, setOrderNumber] = useState('');
  const pollRef = useRef(null);
  const pollCountRef = useRef(0);

  const token = searchParams.get('token');
  const provider = searchParams.get('provider') || 'paddle';
  const ptxn = searchParams.get('_ptxn');
  const orderId = searchParams.get('order_id') || localStorage.getItem('paddle_pending_order_id');

  useEffect(() => {
    if (ptxn && orderId) {
      localStorage.removeItem('paddle_pending_order_id');
    }
  }, [ptxn, orderId]);

  const fetchOrderStatus = async () => {
    if (!orderId) return null;
    try {
      const { data } = await axios.get(`${API}/checkout/${orderId}`);
      return data;
    } catch {
      return null;
    }
  };

  const applyStatus = (data) => {
    if (!data) return;
    const s = data.payment_status || 'pending';
    setStatus(s);
    setMessage(s === 'approved' ? 'Pago procesado' : 'Pago no completado');
    setOrderNumber(data.order_number || '');
  };

  const startPolling = () => {
    pollCountRef.current = 0;
    pollRef.current = setInterval(async () => {
      pollCountRef.current += 1;
      if (pollCountRef.current > MAX_POLLS) {
        clearInterval(pollRef.current);
        setStatus('pending');
        setMessage('El pago está tardando más de lo esperado. Puedes revisar en "Mis Libros" más tarde.');
        return;
      }
      const data = await fetchOrderStatus();
      if (data && data.payment_status !== 'pending') {
        clearInterval(pollRef.current);
        applyStatus(data);
      }
    }, POLL_INTERVAL);
  };

  useEffect(() => {
    let cancelled = false;

    const verify = async () => {
      const data = await fetchOrderStatus();
      if (cancelled) return;

      if (data) {
        if (data.payment_status !== 'pending') {
          applyStatus(data);
        } else {
          setStatus('pending');
          setMessage('Pago pendiente de confirmación...');
          startPolling();
        }
      } else {
        setStatus('error');
        setMessage('Error al verificar el pago');
      }
    };

    if (ptxn) {
      if (orderId) {
        verify();
      } else {
        setStatus('pending');
        setMessage('Verificando pago...');
      }
    } else if (provider === 'paddle' && token) {
      verify();
    } else if (orderId) {
      verify();
    } else {
      setStatus('error');
      setMessage('Parámetros de pago no válidos');
    }

    return () => {
      cancelled = true;
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [ptxn, token, orderId, provider]);

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

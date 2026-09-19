import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Zap, Check, Loader2 } from 'lucide-react';
import { initializePaddle } from '@paddle/paddle-js';

const TIERS = [
  {
    name: 'Starter',
    description: 'Para lectores casuales',
    priceId: { month: 'pri_01m2e24vee4z439gft1wyw52fr', year: 'pri_01m2e24vee4z439gft1wyw52fr' },
    features: ['5 libros al mes', 'Lectura basica', 'Soporte por email'],
  },
  {
    name: 'Pro',
    description: 'Para lectores avidos',
    priceId: { month: 'pri_01m2e24vee4z439gft1wyw52fr', year: 'pri_01m2e24vee4z439gft1wyw52fr' },
    features: ['Libros ilimitados', 'Lectura premium', 'Soporte prioritario', 'Rayos bonus'],
  },
  {
    name: 'Advanced',
    description: 'Para bibliotecas completas',
    priceId: { month: 'pri_01m2e24vee4z439gft1wyw52fr', year: 'pri_01m2e24vee4z439gft1wyw52fr' },
    features: ['Todo de Pro', 'Acceso anticipado', 'API acceso', 'Soporte dedicado'],
  },
];

const ENV = import.meta.env.VITE_PADDLE_ENVIRONMENT || 'sandbox';
const CLIENT_TOKEN = import.meta.env.VITE_PADDLE_CLIENT_TOKEN || '';

export default function TestCheckoutPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [billing, setBilling] = useState('month');
  const [prices, setPrices] = useState({});
  const [loading, setLoading] = useState(true);
  const [paddleReady, setPaddleReady] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const paddleRef = useRef(null);
  const completedRef = useRef(false);

  useEffect(() => {
    if (!CLIENT_TOKEN) {
      setErrorMsg('VITE_PADDLE_CLIENT_TOKEN no esta configurado');
      setLoading(false);
      return;
    }

    initializePaddle({
      token: CLIENT_TOKEN,
      environment: ENV,
      checkout: {
        settings: {
          displayMode: 'overlay',
          theme: 'dark',
          locale: 'es',
          variant: 'one-page',
        },
      },
      eventCallback: (event) => {
        console.log('[PADDLE EVENT]', event.name, event);
        if (event.name === 'checkout.completed') {
          if (!completedRef.current) {
            completedRef.current = true;
            navigate('/welcome');
          }
        }
      },
    }).then((paddle) => {
      paddleRef.current = paddle;
      setPaddleReady(true);
      fetchPrices(paddle);
    }).catch((err) => {
      console.error('[PADDLE] Error initializing:', err);
      setErrorMsg('Error initializing Paddle: ' + err.message);
      setLoading(false);
    });
  }, [navigate]);

  const fetchPrices = async (paddle) => {
    try {
      const priceIds = TIERS.map((tier) => ({
        priceId: tier.priceId.month,
        quantity: 1,
      }));

      const result = await paddle.PricePreview({
        items: priceIds,
      });

      const priceMap = {};
      if (result && result.details && result.details.lineItems) {
        result.details.lineItems.forEach((item) => {
          priceMap[item.priceId] = {
            formattedTotal: item.formattedTotals?.total || '',
            unitPrice: item.unitPrice || {},
          };
        });
      }
      setPrices(priceMap);
    } catch (err) {
      console.error('[PADDLE] Error fetching prices:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubscribe = (tier) => {
    console.log('[PADDLE] Subscribe clicked for', tier.name, 'paddleRef:', !!paddleRef.current);
    if (!paddleRef.current) {
      alert('Paddle no esta listo. Refresca la pagina.');
      return;
    }

    try {
      paddleRef.current.Checkout.open({
        items: [{
          priceId: tier.priceId[billing],
          quantity: 1,
        }],
        customer: {
          email: user?.email || '',
        },
        settings: {
          displayMode: 'overlay',
          theme: 'dark',
          locale: 'es',
          variant: 'one-page',
        },
      });
    } catch (err) {
      console.error('[PADDLE] Checkout.open error:', err);
      alert('Error al abrir checkout: ' + err.message);
    }
  };

  if (errorMsg) {
    return (
      <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center">
        <div className="text-center max-w-md">
          <p className="text-red-400 text-lg mb-2">{errorMsg}</p>
          <p className="text-[#A0A0A0] text-sm">VITE_PADDLE_CLIENT_TOKEN: {CLIENT_TOKEN ? 'configurado' : 'FALTA'}</p>
          <p className="text-[#A0A0A0] text-sm">VITE_PADDLE_ENVIRONMENT: {ENV}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0A0A] py-16 px-6">
      <div className="max-w-5xl mx-auto text-center mb-12">
        <h1 className="text-4xl font-bold text-white mb-4">Elige tu plan</h1>
        <p className="text-[#A0A0A0] text-lg">Accede a todo el contenido de AeternumLibrary</p>

        <div className="flex justify-center gap-2 mt-8">
          <button
            onClick={() => setBilling('month')}
            className={`px-6 py-2 rounded-xl font-semibold transition-all ${
              billing === 'month' ? 'bg-[#D92B2B] text-white' : 'bg-white/10 text-[#A0A0A0]'
            }`}
          >
            Mensual
          </button>
          <button
            onClick={() => setBilling('year')}
            className={`px-6 py-2 rounded-xl font-semibold transition-all ${
              billing === 'year' ? 'bg-[#D92B2B] text-white' : 'bg-white/10 text-[#A0A0A0]'
            }`}
          >
            Anual
          </button>
        </div>
      </div>

      <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6">
        {TIERS.map((tier) => {
          const priceData = prices[tier.priceId[billing]];
          const displayPrice = priceData?.formattedTotal || (loading ? '...' : '$10.00');

          return (
            <div key={tier.name} className="bg-[#121212] border border-white/10 rounded-2xl p-8 flex flex-col">
              <h3 className="text-xl font-bold text-white">{tier.name}</h3>
              <p className="text-[#A0A0A0] text-sm mt-1">{tier.description}</p>
              <div className="mt-4 mb-6">
                {loading ? (
                  <Loader2 className="w-6 h-6 text-[#D4AF37] animate-spin" />
                ) : (
                  <span className="text-4xl font-bold text-[#D4AF37]">{displayPrice}</span>
                )}
                <span className="text-[#A0A0A0] text-sm">/{billing === 'month' ? 'mes' : 'anio'}</span>
              </div>
              <ul className="space-y-3 mb-8 flex-1">
                {tier.features.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-[#A0A0A0]">
                    <Check className="w-4 h-4 text-green-400" /> {f}
                  </li>
                ))}
              </ul>
              <button
                onClick={() => handleSubscribe(tier)}
                className="w-full bg-[#D92B2B] hover:bg-[#F03C3C] text-white font-bold py-3 rounded-xl transition-all flex items-center justify-center gap-2 cursor-pointer relative z-10"
                style={{ opacity: paddleReady ? 1 : 0.5, cursor: paddleReady ? 'pointer' : 'not-allowed' }}
              >
                {!paddleReady ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Zap className="w-4 h-4" />
                )}
                {paddleReady ? 'Subscribe' : 'Cargando Paddle...'}
              </button>
            </div>
          );
        })}
      </div>

      <div className="max-w-5xl mx-auto mt-12 text-center">
        <p className="text-[#A0A0A0] text-xs">
          Entorno: <span className="text-[#D4AF37]">{ENV}</span> | Token: <span className="text-[#D4AF37]">{CLIENT_TOKEN ? 'configurado (' + CLIENT_TOKEN.substring(0, 8) + '...)' : 'FALTA'}</span> | Paddle: <span className="text-[#D4AF37]">{paddleReady ? 'listo' : 'cargando...'}</span>
        </p>
      </div>
    </div>
  );
}

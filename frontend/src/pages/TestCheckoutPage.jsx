import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { isPaddleReady, onCheckoutCompleted, onCheckoutClosed } from '../utils/paddle';
import { Zap, Check } from 'lucide-react';

const TIERS = [
  {
    name: 'Starter',
    description: 'Para lectores casuales',
    price: { month: '9.99', year: '99.99' },
    priceId: { month: 'pri_starter_month', year: 'pri_starter_year' },
    features: ['5 libros al mes', 'Lectura basica', 'Soporte por email'],
  },
  {
    name: 'Pro',
    description: 'Para lectores avidos',
    price: { month: '29.99', year: '299.99' },
    priceId: { month: 'pri_pro_month', year: 'pri_pro_year' },
    features: ['Libros ilimitados', 'Lectura premium', 'Soporte prioritario', 'Rayos bonus'],
  },
  {
    name: 'Advanced',
    description: 'Para bibliotecas completas',
    price: { month: '49.99', year: '499.99' },
    priceId: { month: 'pri_advanced_month', year: 'pri_advanced_year' },
    features: ['Todo de Pro', 'Acceso anticipado', 'API acceso', 'Soporte dedicado'],
  },
];

export default function TestCheckoutPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [billing, setBilling] = useState('month');
  const completedRef = useRef(false);

  useEffect(() => {
    onCheckoutCompleted(() => {
      if (!completedRef.current) {
        completedRef.current = true;
        navigate('/welcome');
      }
    });
    onCheckoutClosed(() => {});
  }, [navigate]);

  const handleSubscribe = (tier) => {
    if (!isPaddleReady()) {
      alert('Paddle no esta listo. Verifica VITE_PADDLE_CLIENT_TOKEN en Render.');
      return;
    }

    window.Paddle.Checkout.open({
      items: [{
        priceId: tier.priceId[billing],
        quantity: 1,
      }],
      settings: {
        displayMode: 'overlay',
        theme: 'dark',
        locale: 'es',
        variant: 'one-page',
      },
      customer: {
        email: user?.email || '',
      },
    });
  };

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
        {TIERS.map((tier) => (
          <div key={tier.name} className="bg-[#121212] border border-white/10 rounded-2xl p-8 flex flex-col">
            <h3 className="text-xl font-bold text-white">{tier.name}</h3>
            <p className="text-[#A0A0A0] text-sm mt-1">{tier.description}</p>
            <div className="mt-4 mb-6">
              <span className="text-4xl font-bold text-[#D4AF37]">${tier.price[billing]}</span>
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
              className="w-full bg-[#D92B2B] hover:bg-[#F03C3C] text-white font-bold py-3 rounded-xl transition-all flex items-center justify-center gap-2"
            >
              <Zap className="w-4 h-4" /> Subscribe
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

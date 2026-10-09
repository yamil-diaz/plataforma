import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Store, AlertCircle, CheckCircle, Clock } from 'lucide-react';
import { formatApiError } from '../utils/apiError';

const API = import.meta.env.VITE_API_URL || '/api';

export default function BecomeSellerPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [applicationStatus, setApplicationStatus] = useState(null);
  
  const [formData, setFormData] = useState({
    business_name: '',
    business_type: 'individual',
    tax_id: '',
    phone: '',
    address: '',
    city: '',
    country: 'Perú',
    description: ''
  });

  useEffect(() => {
    loadApplicationStatus();
  }, []);

  const loadApplicationStatus = async () => {
    try {
      const { data } = await axios.get(`${API}/seller/application/status`);
      setApplicationStatus(data);
    } catch (err) {
      console.error('Error cargando estado:', err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      await axios.post(`${API}/seller/apply`, formData);
      setSuccess(true);
      setTimeout(() => navigate('/'), 3000);
    } catch (err) {
      setError(formatApiError(err, 'Error al enviar solicitud'));
    } finally {
      setLoading(false);
    }
  };

  if (applicationStatus?.has_application) {
    const statusColors = {
      pending: { bg: 'bg-yellow-900/20', border: 'border-yellow-500/30', text: 'text-yellow-400', icon: Clock },
      approved: { bg: 'bg-green-900/20', border: 'border-green-500/30', text: 'text-green-400', icon: CheckCircle },
      rejected: { bg: 'bg-red-900/20', border: 'border-red-500/30', text: 'text-red-400', icon: AlertCircle }
    };
    const status = statusColors[applicationStatus.status];
    const StatusIcon = status.icon;

    return (
      <div className="min-h-screen bg-[#0A0A0A] pt-24 pb-20 px-4">
        <div className="max-w-2xl mx-auto">
          <div className={`${status.bg} border ${status.border} rounded-2xl p-8 text-center`}>
            <StatusIcon className={`w-16 h-16 ${status.text} mx-auto mb-4`} />
            <h2 className={`text-2xl font-bold ${status.text} mb-2`}>
              {applicationStatus.status === 'pending' && 'Solicitud en Revisión'}
              {applicationStatus.status === 'approved' && '¡Eres Vendedor!'}
              {applicationStatus.status === 'rejected' && 'Solicitud Rechazada'}
            </h2>
            <p className="text-[#A0A0A0] mb-4">
              {applicationStatus.status === 'pending' && 'Tu solicitud está siendo revisada por nuestro equipo. Te notificaremos cuando sea aprobada.'}
              {applicationStatus.status === 'approved' && 'Tu cuenta ha sido verificada como vendedor. Ya puedes publicar y vender libros.'}
              {applicationStatus.status === 'rejected' && applicationStatus.admin_note}
            </p>
            {applicationStatus.status === 'approved' && (
              <button onClick={() => navigate('/dashboard')} className="ae-btn ae-btn-primary">
                Ir a Mi Panel de Vendedor
              </button>
            )}
            {applicationStatus.status === 'rejected' && (
              <button onClick={() => {setApplicationStatus(null)}} className="ae-btn ae-btn-primary">
                Volver a Aplicar
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (success) {
    return (
      <div className="min-h-screen bg-[#0A0A0A] pt-24 pb-20 px-4">
        <div className="max-w-2xl mx-auto">
          <div className="bg-green-900/20 border border-green-500/30 rounded-2xl p-8 text-center">
            <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-green-400 mb-2">¡Solicitud Enviada!</h2>
            <p className="text-[#A0A0A0]">Tu solicitud ha sido enviada correctamente. Te notificaremos cuando sea revisada.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0A0A] pt-24 pb-20 px-4">
      <div className="max-w-3xl mx-auto">
        <div className="text-center mb-10">
          <div className="w-16 h-16 rounded-xl bg-[#D92B2B] flex items-center justify-center mx-auto mb-4">
            <Store className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-4xl font-bold text-white mb-3">Conviértete en Vendedor</h1>
          <p className="text-[#A0A0A0] text-lg">Vende tus libros digitales y físicos en AETERNUM</p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-950/20 border border-red-500/30 rounded-lg flex items-start gap-3 text-red-400">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="ae-card p-8 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">
                Nombre del Negocio *
              </label>
              <input
                type="text"
                required
                value={formData.business_name}
                onChange={(e) => setFormData({...formData, business_name: e.target.value})}
                className="ae-input w-full"
                placeholder="Ej: Librería Digital"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">
                Tipo de Negocio *
              </label>
              <select
                required
                value={formData.business_type}
                onChange={(e) => setFormData({...formData, business_type: e.target.value})}
                className="ae-input w-full"
              >
                <option value="individual">Individual</option>
                <option value="company">Empresa</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">
                RUC / DNI
              </label>
              <input
                type="text"
                value={formData.tax_id}
                onChange={(e) => setFormData({...formData, tax_id: e.target.value})}
                className="ae-input w-full"
                placeholder="Opcional"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">
                Teléfono *
              </label>
              <input
                type="tel"
                required
                value={formData.phone}
                onChange={(e) => setFormData({...formData, phone: e.target.value})}
                className="ae-input w-full"
                placeholder="+51 999 999 999"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">
              Dirección *
            </label>
            <input
              type="text"
              required
              value={formData.address}
              onChange={(e) => setFormData({...formData, address: e.target.value})}
              className="ae-input w-full"
              placeholder="Calle, número, distrito"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">
                Ciudad *
              </label>
              <input
                type="text"
                required
                value={formData.city}
                onChange={(e) => setFormData({...formData, city: e.target.value})}
                className="ae-input w-full"
                placeholder="Lima, Arequipa, etc."
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">
                País *
              </label>
              <input
                type="text"
                required
                value={formData.country}
                onChange={(e) => setFormData({...formData, country: e.target.value})}
                className="ae-input w-full"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">
              Descripción de tu Negocio *
            </label>
            <textarea
              required
              rows="4"
              value={formData.description}
              onChange={(e) => setFormData({...formData, description: e.target.value})}
              className="ae-input w-full"
              placeholder="Cuéntanos sobre los libros que vendes, tu experiencia, etc."
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="ae-btn ae-btn-primary w-full text-lg py-4"
          >
            {loading ? 'Enviando...' : 'Enviar Solicitud'}
          </button>
        </form>
      </div>
    </div>
  );
}

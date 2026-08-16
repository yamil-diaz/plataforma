import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Navbar } from '../components/Navbar';
import axios from 'axios';
import { QrCode, ArrowLeft, Plus, Copy, Power, X, Eye, Download, Printer } from 'lucide-react';
import QRCode from 'qrcode';
import { LOGO_URL, computeLogoSize, computeLogoZoneSize } from '../utils/qrLogo';

const API = import.meta.env.VITE_API_URL || '/api';

const CODE_REGEX = /^[A-Za-z0-9_-]{1,32}$/;

// Generación visual del QR (FASE 7 y 7.1): la imagen codifica EXACTAMENTE
// window.location.origin + "/register?ref=" + code. Se genera en el navegador
// (sin endpoints nuevos, sin almacenamiento, sin tablas) y es reproducible
// desde el código y la URL. Fondo blanco + margen para máxima escaneabilidad.
// errorCorrectionLevel 'H' es obligatorio en FASE 7.1 porque el logo de
// Aeternum (15 % del ancho + zona blanca de protección) ocupa el centro.
const QR_OPTIONS = {
  width: 512,
  margin: 4,
  errorCorrectionLevel: 'H',
  color: { dark: '#000000', light: '#ffffff' },
};

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export default function AdminQRCodesPage() {
  const [qrCodes, setQrCodes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({ code: '', name: '' });
  const [formError, setFormError] = useState('');
  const [creating, setCreating] = useState(false);

  const [viewQr, setViewQr] = useState(null);
  const [qrImage, setQrImage] = useState('');
  const [qrImageLoading, setQrImageLoading] = useState(false);

  useEffect(() => {
    fetchQrCodes();
  }, []);

  const fetchQrCodes = async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await axios.get(`${API}/admin/qr-codes`, { withCredentials: true });
      setQrCodes(data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al cargar los códigos QR');
    } finally {
      setLoading(false);
    }
  };

  const buildRegistrationUrl = (code) => {
    const origin = typeof window !== 'undefined' ? window.location.origin : '';
    return `${origin}/register?ref=${code}`;
  };

  const handleCopy = async (code) => {
    const url = buildRegistrationUrl(code);
    try {
      await navigator.clipboard.writeText(url);
      setSuccess(`Enlace copiado: ${url}`);
      setTimeout(() => setSuccess(''), 4000);
    } catch (err) {
      setError(`No se pudo copiar el enlace. Cópialo manualmente: ${url}`);
    }
  };

  // Logo oficial de Aeternum (asset local /favicon.svg), cargado una sola vez.
  let logoPromise = null;
  const loadLogo = () => {
    if (!logoPromise) {
      logoPromise = new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = () => {
          logoPromise = null;
          reject(new Error('No se pudo cargar el logo'));
        };
        img.src = LOGO_URL;
      });
    }
    return logoPromise;
  };

  // Única función de generación (FASE 7.1): QR dinámico + logo centrado.
  // El PNG final se reutiliza para Ver QR, Descargar PNG e Imprimir.
  const generateBrandedQrDataUrl = async (code) => {
    const url = buildRegistrationUrl(code);
    const size = QR_OPTIONS.width;
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    await QRCode.toCanvas(canvas, url, QR_OPTIONS);
    const logo = await loadLogo();
    const ctx = canvas.getContext('2d');
    const logoSize = computeLogoSize(size);
    const zoneSize = computeLogoZoneSize(size);
    const cx = size / 2;
    const cy = size / 2;
    ctx.fillStyle = '#ffffff';
    ctx.beginPath();
    ctx.arc(cx, cy, zoneSize / 2, 0, Math.PI * 2);
    ctx.fill();
    ctx.drawImage(logo, cx - logoSize / 2, cy - logoSize / 2, logoSize, logoSize);
    return canvas.toDataURL('image/png');
  };

  const handleView = async (qr) => {
    setViewQr(qr);
    setQrImage('');
    setQrImageLoading(true);
    setError('');
    try {
      setQrImage(await generateBrandedQrDataUrl(qr.code));
    } catch (err) {
      setError('No se pudo generar la imagen del QR');
    } finally {
      setQrImageLoading(false);
    }
  };

  const handleDownloadQr = () => {
    if (!qrImage || !viewQr) return;
    const safeCode = CODE_REGEX.test(viewQr.code) ? viewQr.code : 'QR';
    const link = document.createElement('a');
    link.href = qrImage;
    link.download = `QR_${safeCode}.png`;
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  const handlePrintQr = () => {
    if (!qrImage || !viewQr) return;
    const url = buildRegistrationUrl(viewQr.code);
    const win = window.open('', '_blank', 'width=600,height=700');
    if (!win) {
      setError('El navegador bloqueó la ventana de impresión. Permite ventanas emergentes e inténtalo de nuevo.');
      return;
    }
    win.document.write(`<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8" /><title>QR ${escapeHtml(viewQr.code)}</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: Arial, Helvetica, sans-serif; background: #fff; color: #111; text-align: center; padding: 24px; }
  .qr-name { font-size: 18px; font-weight: 700; margin-bottom: 4px; }
  .qr-code { font-size: 14px; font-weight: 700; color: #555; margin-bottom: 16px; letter-spacing: 1px; }
  img { width: 320px; height: 320px; border: 1px solid #eee; padding: 16px; background: #fff; }
  .qr-url { margin-top: 16px; font-size: 13px; color: #333; word-break: break-all; }
  @media print { body { padding: 8px; } img { width: 240px; height: 240px; } }
</style></head><body>
  <div class="qr-name">${escapeHtml(viewQr.name)}</div>
  <div class="qr-code">${escapeHtml(viewQr.code)}</div>
  <img src="${qrImage}" alt="QR ${escapeHtml(viewQr.code)}" />
  <div class="qr-url">${escapeHtml(url)}</div>
</body></html>`);
    win.document.close();
    win.focus();
    win.onafterprint = () => win.close();
    setTimeout(() => win.print(), 250);
  };

  const handleToggle = async (qr) => {
    const desactivar = qr.is_active;
    if (desactivar && !window.confirm(`¿Desactivar el código QR "${qr.code}"? Dejará de registrar visitas y nuevos registros.`)) {
      return;
    }
    try {
      const { data } = await axios.patch(
        `${API}/admin/qr-codes/${qr.id}`,
        { is_active: !qr.is_active },
        { withCredentials: true }
      );
      setQrCodes(qrCodes.map(q => q.id === qr.id ? { ...q, is_active: data.is_active } : q));
      setSuccess(desactivar ? `Código QR "${qr.code}" desactivado` : `Código QR "${qr.code}" activado`);
      setTimeout(() => setSuccess(''), 4000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Error al actualizar el código QR');
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    const code = form.code.trim();
    const name = form.name.trim();
    if (!CODE_REGEX.test(code)) {
      setFormError('El código debe tener entre 1 y 32 caracteres: letras, números, guiones (-) o guiones bajos (_).');
      return;
    }
    if (!name) {
      setFormError('El nombre es obligatorio.');
      return;
    }
    setCreating(true);
    setFormError('');
    try {
      await axios.post(`${API}/admin/qr-codes`, { code, name }, { withCredentials: true });
      setShowModal(false);
      setForm({ code: '', name: '' });
      setSuccess(`Código QR "${code}" creado`);
      setTimeout(() => setSuccess(''), 4000);
      fetchQrCodes();
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Error al crear el código QR');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A] pb-24 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-6xl mx-auto px-6 pt-12 w-full">
        <Link to="/dashboard" className="flex items-center gap-2 text-[#A0A0A0] hover:text-white transition-colors mb-6 text-sm font-medium">
          <ArrowLeft className="w-4 h-4" /> Volver al Panel
        </Link>

        <div className="flex flex-col md:flex-row items-start md:items-center justify-between mb-8 gap-4">
          <div className="flex items-center gap-3">
            <QrCode className="w-7 h-7 text-purple-500" />
            <div>
              <h1 className="text-3xl font-bold text-white font-['Outfit']">Códigos QR</h1>
              <p className="text-sm text-[#A0A0A0] mt-1">
                Gestiona los códigos QR de registro de la plataforma y sus estadísticas.
              </p>
            </div>
          </div>

          <button
            onClick={() => { setFormError(''); setShowModal(true); }}
            className="flex items-center gap-2 bg-[#D92B2B] hover:bg-[#F03C3C] text-white px-4 py-2.5 rounded-lg text-sm font-semibold transition-colors"
          >
            <Plus className="w-4 h-4" /> Crear código QR
          </button>
        </div>

        {error && <div className="bg-red-500/10 border border-red-500/30 text-red-500 p-4 rounded-lg text-sm mb-6 font-medium">{error}</div>}
        {success && <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 p-4 rounded-lg text-sm mb-6 font-medium">{success}</div>}

        {loading ? (
          <div className="text-center text-[#A0A0A0] py-20">Cargando códigos QR...</div>
        ) : qrCodes.length === 0 ? (
          <div className="bg-[#121212] border border-white/5 rounded-xl p-12 text-center">
            <p className="text-[#A0A0A0] mb-4">Aún no hay códigos QR.</p>
            <button onClick={() => setShowModal(true)} className="text-[#D92B2B] hover:underline font-semibold">Crea el primer código QR</button>
          </div>
        ) : (
          <div className="bg-[#121212] border border-white/10 rounded-xl overflow-hidden shadow-xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse min-w-[900px]">
                <thead>
                  <tr className="bg-[#1A1A1A] border-b border-white/10 text-[#A0A0A0] text-xs uppercase tracking-wider">
                    <th className="p-4 font-semibold">Código</th>
                    <th className="p-4 font-semibold">Nombre</th>
                    <th className="p-4 font-semibold text-center">Estado</th>
                    <th className="p-4 font-semibold text-center">Visitas</th>
                    <th className="p-4 font-semibold text-center">Registros</th>
                    <th className="p-4 font-semibold">Enlace</th>
                    <th className="p-4 font-semibold text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {qrCodes.map(qr => (
                    <tr key={qr.id} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                      <td className="p-4 text-white font-mono font-semibold">{qr.code}</td>
                      <td className="p-4 text-[#A0A0A0] text-sm">{qr.name}</td>
                      <td className="p-4 text-center">
                        {qr.is_active ? (
                          <span className="bg-emerald-500/10 text-emerald-400 px-2 py-1 rounded-full text-[10px] font-bold uppercase border border-emerald-500/20">Activo</span>
                        ) : (
                          <span className="bg-red-500/10 text-red-500 px-2 py-1 rounded-full text-[10px] font-bold uppercase border border-red-500/20">Inactivo</span>
                        )}
                      </td>
                      <td className="p-4 text-[#A0A0A0] text-sm text-center"><span className="text-white font-medium">{qr.visits_count}</span></td>
                      <td className="p-4 text-[#A0A0A0] text-sm text-center"><span className="text-white font-medium">{qr.registrations_count}</span></td>
                      <td className="p-4">
                        <span className="text-xs text-[#A0A0A0] font-mono truncate block max-w-[220px]">{buildRegistrationUrl(qr.code)}</span>
                      </td>
                      <td className="p-4 text-right">
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => handleView(qr)}
                            title="Ver QR"
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-500/10 text-purple-400 hover:bg-purple-500/20 border border-purple-500/30 rounded-lg transition-colors text-xs font-semibold"
                          >
                            <Eye className="w-3.5 h-3.5" /> Ver QR
                          </button>
                          <button
                            onClick={() => handleCopy(qr.code)}
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#D4AF37]/10 text-[#D4AF37] hover:bg-[#D4AF37]/20 border border-[#D4AF37]/30 rounded-lg transition-colors text-xs font-semibold"
                          >
                            <Copy className="w-3.5 h-3.5" /> Copiar enlace
                          </button>
                          <button
                            onClick={() => handleToggle(qr)}
                            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors text-xs font-semibold border ${
                              qr.is_active
                                ? 'bg-red-500/10 text-red-500 hover:bg-red-500/20 border-red-500/30'
                                : 'bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 border-emerald-500/30'
                            }`}
                          >
                            <Power className="w-3.5 h-3.5" /> {qr.is_active ? 'Desactivar' : 'Activar'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-[#121212] border border-white/10 rounded-2xl w-full max-w-md shadow-2xl overflow-hidden">
            <div className="flex justify-between items-center p-6 border-b border-white/10">
              <h2 className="text-xl font-bold text-white">Crear Código QR</h2>
              <button onClick={() => setShowModal(false)} className="text-[#A0A0A0] hover:text-white transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreate} className="p-6 space-y-4">
              {formError && <div className="bg-red-500/10 border border-red-500/30 text-red-500 p-4 rounded-lg text-sm font-medium">{formError}</div>}
              <div>
                <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Código</label>
                <input
                  required
                  type="text"
                  maxLength="32"
                  placeholder="Ej. QR001"
                  value={form.code}
                  onChange={(e) => setForm({ ...form, code: e.target.value })}
                  className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-white font-mono focus:border-purple-500 focus:outline-none"
                />
                <p className="text-[10px] text-[#A0A0A0] mt-1">Entre 1 y 32 caracteres: letras, números, guiones (-) o guiones bajos (_).</p>
              </div>
              <div>
                <label className="block text-xs font-semibold text-[#A0A0A0] uppercase tracking-wider mb-2">Nombre</label>
                <input
                  required
                  type="text"
                  placeholder="Ej. Volante principal"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full bg-[#0A0A0A] border border-white/10 rounded-lg px-4 py-3 text-white focus:border-purple-500 focus:outline-none"
                />
              </div>
              <div className="pt-4 flex gap-3">
                <button type="button" onClick={() => setShowModal(false)} className="flex-1 bg-white/5 hover:bg-white/10 text-white font-semibold py-3 rounded-lg transition-colors">
                  Cancelar
                </button>
                <button type="submit" disabled={creating} className="flex-1 bg-[#D92B2B] hover:bg-[#F03C3C] text-white font-semibold py-3 rounded-lg transition-colors disabled:opacity-50">
                  {creating ? 'Creando...' : 'Crear QR'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      {viewQr && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-[#121212] border border-white/10 rounded-2xl w-full max-w-md shadow-2xl overflow-hidden">
            <div className="flex justify-between items-center p-6 border-b border-white/10">
              <h2 className="text-xl font-bold text-white">Código QR</h2>
              <button onClick={() => setViewQr(null)} className="text-[#A0A0A0] hover:text-white transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4 text-center">
              <div>
                <p className="text-[#A0A0A0] text-sm">{viewQr.name}</p>
                <p className="text-white font-mono font-semibold">{viewQr.code}</p>
              </div>
              <div className="bg-white rounded-xl p-4 inline-block">
                {qrImageLoading ? (
                  <div className="w-[320px] h-[320px] flex items-center justify-center text-[#A0A0A0] text-sm">Generando QR...</div>
                ) : qrImage ? (
                  <img src={qrImage} alt={`QR ${viewQr.code}`} className="w-[320px] h-[320px]" />
                ) : (
                  <div className="w-[320px] h-[320px] flex items-center justify-center text-red-500 text-sm">No se pudo generar la imagen</div>
                )}
              </div>
              <p className="text-xs text-[#A0A0A0] font-mono break-all">{buildRegistrationUrl(viewQr.code)}</p>
              <div className="flex gap-3 pt-2">
                <button
                  onClick={handleDownloadQr}
                  disabled={!qrImage}
                  className="flex-1 bg-[#D4AF37] hover:bg-[#F3CE56] text-black font-semibold py-3 rounded-lg transition-colors disabled:opacity-40 flex items-center justify-center gap-2"
                >
                  <Download className="w-4 h-4" /> Descargar PNG
                </button>
                <button
                  onClick={handlePrintQr}
                  disabled={!qrImage}
                  className="flex-1 bg-white/10 hover:bg-white/20 text-white font-semibold py-3 rounded-lg transition-colors disabled:opacity-40 flex items-center justify-center gap-2"
                >
                  <Printer className="w-4 h-4" /> Imprimir
                </button>
              </div>
              <button onClick={() => setViewQr(null)} className="w-full bg-white/5 hover:bg-white/10 text-white font-semibold py-2.5 rounded-lg transition-colors">
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
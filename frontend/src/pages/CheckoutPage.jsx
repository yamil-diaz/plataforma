import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Navbar } from '../components/Navbar';
import { useAuth } from '../contexts/AuthContext';
import { API } from '../config/api';
import { openPaddleCheckout, isPaddleReady, onCheckoutClosed, onCheckoutCompleted } from '../utils/paddle';
import { CreditCard, Zap, Clock, Truck, CheckCircle, AlertCircle } from 'lucide-react';

export default function CheckoutPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user, refreshUser } = useAuth();
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [book, setBook] = useState(null);
  const [bookPrices, setBookPrices] = useState({});
  const [availableCurrencies, setAvailableCurrencies] = useState([]);
  const [selectedCurrency, setSelectedCurrency] = useState('PEN');
  const [itemType, setItemType] = useState('digital_purchase');
  const [rentalDays, setRentalDays] = useState(14);
  const [addresses, setAddresses] = useState([]);
  const [selectedAddress, setSelectedAddress] = useState(null);
  const [showAddressForm, setShowAddressForm] = useState(false);
  const [newAddress, setNewAddress] = useState({
    recipient_name: '', recipient_phone: '', address_line1: '',
    address_line2: '', district: '', city: '', department: '', postal_code: ''
  });

  const bookId = searchParams.get('book_id');

  useEffect(() => {
    if (!bookId) {
      navigate('/');
      return;
    }
    loadBook();
    loadAddresses();
    loadCurrencies();
  }, [bookId]);

  // Cleanup: si el usuario navega fuera, limpiar el pending order
  useEffect(() => {
    return () => {
      // Si el usuario cierra la pagina/navega mientras Paddle esta abierto,
      // el pending order queda en localStorage para que PaymentResultPage lo recupere
    };
  }, []);

  const loadBook = async () => {
    try {
      const { data } = await axios.get(`${API}/books/${bookId}`);
      setBook(data);
      if (!data.price || data.price <= 0) {
        setItemType('digital_purchase');
      }
      loadBookPrices(bookId);
    } catch (err) {
      setError('Libro no encontrado');
    } finally {
      setLoading(false);
    }
  };

  const loadBookPrices = async (id) => {
    try {
      const { data } = await axios.get(`${API}/books/${id}/prices`);
      setBookPrices(data.prices || {});
    } catch (err) {
      console.error('Error loading book prices:', err);
    }
  };

  const loadCurrencies = async () => {
    try {
      const { data } = await axios.get(`${API}/commerce/currencies`);
      setAvailableCurrencies(data.currencies || []);
    } catch (err) {
      setAvailableCurrencies([{ code: 'PEN', symbol: 'S/' }]);
    }
  };

  const loadAddresses = async () => {
    try {
      const { data } = await axios.get(`${API}/user/addresses`);
      setAddresses(data);
      if (data.length > 0) {
        setSelectedAddress(data.find(a => a.is_default)?.id || data[0].id);
      }
    } catch (err) {
      console.error('Error loading addresses:', err);
    }
  };

  const handleCreateAddress = async () => {
    try {
      const { data } = await axios.post(`${API}/user/addresses`, newAddress);
      setShowAddressForm(false);
      setNewAddress({
        recipient_name: '', recipient_phone: '', address_line1: '',
        address_line2: '', district: '', city: '', department: '', postal_code: ''
      });
      await loadAddresses();
      setSelectedAddress(data.id);
    } catch (err) {
      alert(err.response?.data?.detail || 'Error al crear dirección');
    }
  };

  const currentPriceData = bookPrices[selectedCurrency] || null;
  const currentSymbol = currentPriceData?.symbol || selectedCurrency;

  const calculatePrice = () => {
    if (!currentPriceData) return 0;
    if (itemType === 'digital_purchase') return currentPriceData.price;
    if (itemType === 'digital_rental') return currentPriceData.rental_price || 0;
    if (itemType === 'physical_purchase') return parseFloat(book?.physical_price || 0);
    return 0;
  };

  const checkoutCompletedRef = useRef(false);

  const handleCheckout = async () => {
    if (!book) return;
    setProcessing(true);
    setError(null);

    try {
      const payload = {
        book_id: parseInt(bookId),
        item_type: itemType,
        currency: selectedCurrency,
      };
      if (itemType === 'digital_rental') {
        payload.rental_days = rentalDays;
      }
      if (itemType === 'physical_purchase') {
        if (!selectedAddress) {
          setError('Selecciona una dirección de envío');
          setProcessing(false);
          return;
        }
        payload.address_id = selectedAddress;
        payload.currency = 'PEN';
      }

      const { data } = await axios.post(`${API}/checkout`, payload);

      // Paddle (digitales): SIEMPRE usar overlay (el redirect URL de Paddle sandbox
      // apunta a nuestro dominio en vez de a la checkout page de Paddle)
      if (data.transaction_id) {
        if (!isPaddleReady()) {
          setError('El sistema de pago no está disponible. Recarga la pagina e intentalo de nuevo.');
          setProcessing(false);
          return;
        }
        localStorage.setItem('paddle_pending_order_id', String(data.order_id));

        checkoutCompletedRef.current = false;
        onCheckoutCompleted((orderId) => {
          if (!checkoutCompletedRef.current) {
            checkoutCompletedRef.current = true;
            localStorage.removeItem('paddle_pending_order_id');
            navigate(`/checkout/result?order_id=${orderId}`);
          }
        });

        onCheckoutClosed(() => {
          if (!checkoutCompletedRef.current) {
            localStorage.removeItem('paddle_pending_order_id');
            setProcessing(false);
            setError('Checkout cancelado. Puedes intentar de nuevo.');
          }
        });

        const result = openPaddleCheckout(data.transaction_id);
        if (!result.success) {
          // Si el overlay falla, intentar redirect como ultimo recurso
          if (data.payment_url) {
            window.location.href = data.payment_url;
          } else if (result.error === 'paddle_no_token') {
            setError('El sistema de pago no está configurado. Contacta al administrador.');
          } else {
            setError('No se pudo abrir el checkout. Recarga la pagina e intentalo de nuevo.');
          }
          setProcessing(false);
          localStorage.removeItem('paddle_pending_order_id');
        }
        return;
      }

      // Culqi (fisicos): redirigir a resultado con order_id para tokenizacion
      if (data.checkout_type === 'culqi_token') {
        setError('Culqi checkout pendiente de implementacion en frontend');
        return;
      }

      setError('Error al crear el pago. Intenta de nuevo.');
    } catch (err) {
      const detail = err.response?.data?.detail || '';
      if (detail.includes('no está configurado') || detail.includes('no configurado') || err.response?.status === 503) {
        setError('El sistema de pagos no está disponible en este momento. Por favor, contacta a soporte para más información.');
      } else if (err.response?.status === 502) {
        setError('Error al conectar con el proveedor de pagos. Intenta de nuevo más tarde.');
      } else {
        setError(detail || 'Error al procesar el checkout. Intenta de nuevo.');
      }
    } finally {
      // Solo resetear processing si NO es Paddle (Paddle mantiene el overlay abierto)
      if (!localStorage.getItem('paddle_pending_order_id')) {
        setProcessing(false);
      }
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center text-[#A0A0A0]">
        Cargando...
      </div>
    );
  }

  if (error && !book) {
    return (
      <div className="min-h-screen bg-[#0A0A0A]">
        <Navbar />
        <div className="max-w-2xl mx-auto px-6 py-20 text-center">
          <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <p className="text-white text-lg">{error}</p>
          <button onClick={() => navigate('/')} className="mt-4 text-[#D92B2B] hover:underline">
            Volver al catálogo
          </button>
        </div>
      </div>
    );
  }

  const price = calculatePrice();
  const shippingCost = itemType === 'physical_purchase' ? 10.00 : 0;
  const total = price + shippingCost;
  const displayCurrency = itemType === 'physical_purchase' ? 'PEN' : selectedCurrency;
  const displaySymbol = itemType === 'physical_purchase' ? 'S/' : currentSymbol;

  return (
    <div className="min-h-screen bg-[#0A0A0A]">
      <Navbar />
      <div className="max-w-3xl mx-auto px-6 py-12">
        <h1 className="text-3xl font-bold text-white mb-8 font-['Outfit']">Checkout</h1>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 mb-6 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Resumen del libro */}
        <div className="bg-[#121212] border border-white/10 rounded-2xl p-6 mb-6">
          <div className="flex gap-4">
            {book.cover_image_url && (
              <img src={book.cover_image_url} alt={book.title} className="w-20 h-28 object-cover rounded-lg" />
            )}
            <div>
              <h2 className="text-xl font-bold text-white">{book.title}</h2>
              <p className="text-[#A0A0A0]">{book.author_name}</p>
              <p className="text-sm text-[#A0A0A0] mt-1">{book.category}</p>
            </div>
          </div>
        </div>

        {/* Selector de moneda (solo para digitales) */}
        {itemType !== 'physical_purchase' && availableCurrencies.length > 1 && (
          <div className="bg-[#121212] border border-white/10 rounded-2xl p-6 mb-6">
            <h3 className="text-lg font-bold text-white mb-4">Moneda de pago</h3>
            <div className="flex gap-3">
              {availableCurrencies.map(c => {
                const hasPrice = bookPrices[c.code];
                return (
                  <button
                    key={c.code}
                    onClick={() => hasPrice && setSelectedCurrency(c.code)}
                    disabled={!hasPrice}
                    className={`flex-1 py-3 rounded-xl font-semibold transition-all border ${
                      selectedCurrency === c.code
                        ? 'border-[#D92B2B] bg-[#D92B2B]/10 text-white'
                        : hasPrice
                          ? 'border-white/10 bg-white/5 text-[#A0A0A0] hover:border-white/20'
                          : 'border-white/5 bg-white/2 text-[#555] cursor-not-allowed'
                    }`}
                  >
                    <span className="block text-lg">{c.symbol}</span>
                    <span className="block text-xs">{c.code}</span>
                    {!hasPrice && <span className="block text-xs text-[#666]">Sin precio</span>}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Tipo de compra */}
        <div className="bg-[#121212] border border-white/10 rounded-2xl p-6 mb-6">
          <h3 className="text-lg font-bold text-white mb-4">Tipo de compra</h3>
          <div className="space-y-3">
            {currentPriceData && currentPriceData.price > 0 && (
              <label className={`flex items-center gap-3 p-4 rounded-xl border cursor-pointer transition-all ${
                itemType === 'digital_purchase' ? 'border-[#D92B2B] bg-[#D92B2B]/10' : 'border-white/10 hover:border-white/20'
              }`}>
                <input type="radio" name="itemType" value="digital_purchase"
                  checked={itemType === 'digital_purchase'}
                  onChange={() => setItemType('digital_purchase')}
                  className="sr-only" />
                <CreditCard className="w-5 h-5 text-[#D92B2B]" />
                <div className="flex-1">
                  <p className="text-white font-semibold">Compra digital</p>
                  <p className="text-[#A0A0A0] text-sm">Acceso permanente</p>
                </div>
                <span className="text-[#D4AF37] font-bold">{displaySymbol} {currentPriceData.price.toFixed(2)}</span>
              </label>
            )}

            {currentPriceData && currentPriceData.rental_price > 0 && (
              <label className={`flex items-center gap-3 p-4 rounded-xl border cursor-pointer transition-all ${
                itemType === 'digital_rental' ? 'border-[#D92B2B] bg-[#D92B2B]/10' : 'border-white/10 hover:border-white/20'
              }`}>
                <input type="radio" name="itemType" value="digital_rental"
                  checked={itemType === 'digital_rental'}
                  onChange={() => setItemType('digital_rental')}
                  className="sr-only" />
                <Clock className="w-5 h-5 text-[#D4AF37]" />
                <div className="flex-1">
                  <p className="text-white font-semibold">Alquiler digital</p>
                  <p className="text-[#A0A0A0] text-sm">Acceso temporal</p>
                </div>
                <span className="text-[#D4AF37] font-bold">{displaySymbol} {currentPriceData.rental_price.toFixed(2)}</span>
              </label>
            )}

            {book.is_physical && book.physical_price > 0 && (
              <label className={`flex items-center gap-3 p-4 rounded-xl border cursor-pointer transition-all ${
                itemType === 'physical_purchase' ? 'border-[#D92B2B] bg-[#D92B2B]/10' : 'border-white/10 hover:border-white/20'
              }`}>
                <input type="radio" name="itemType" value="physical_purchase"
                  checked={itemType === 'physical_purchase'}
                  onChange={() => { setItemType('physical_purchase'); setSelectedCurrency('PEN'); }}
                  className="sr-only" />
                <Truck className="w-5 h-5 text-green-400" />
                <div className="flex-1">
                  <p className="text-white font-semibold">Compra física</p>
                  <p className="text-[#A0A0A0] text-sm">Envío a tu dirección (solo Perú)</p>
                </div>
                <span className="text-[#D4AF37] font-bold">S/ {parseFloat(book.physical_price).toFixed(2)}</span>
              </label>
            )}
          </div>
        </div>

        {/* Duración de alquiler */}
        {itemType === 'digital_rental' && (
          <div className="bg-[#121212] border border-white/10 rounded-2xl p-6 mb-6">
            <h3 className="text-lg font-bold text-white mb-4">Duración del alquiler</h3>
            <div className="flex gap-3">
              {[7, 14, 30].map(days => (
                <button
                  key={days}
                  onClick={() => setRentalDays(days)}
                  className={`flex-1 py-3 rounded-xl font-semibold transition-all ${
                    rentalDays === days
                      ? 'bg-[#D92B2B] text-white'
                      : 'bg-white/5 text-[#A0A0A0] hover:bg-white/10'
                  }`}
                >
                  {days} días
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Dirección de envío (físico) */}
        {itemType === 'physical_purchase' && (
          <div className="bg-[#121212] border border-white/10 rounded-2xl p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-white">Dirección de envío</h3>
              <button onClick={() => setShowAddressForm(!showAddressForm)}
                className="text-sm text-[#D92B2B] hover:underline">
                {showAddressForm ? 'Cancelar' : '+ Nueva dirección'}
              </button>
            </div>

            {showAddressForm && (
              <div className="bg-[#0A0A0A] rounded-xl p-4 mb-4 space-y-3">
                <input placeholder="Nombre receptor" value={newAddress.recipient_name}
                  onChange={e => setNewAddress({...newAddress, recipient_name: e.target.value})}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white text-sm" />
                <input placeholder="Teléfono" value={newAddress.recipient_phone}
                  onChange={e => setNewAddress({...newAddress, recipient_phone: e.target.value})}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white text-sm" />
                <input placeholder="Dirección línea 1" value={newAddress.address_line1}
                  onChange={e => setNewAddress({...newAddress, address_line1: e.target.value})}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white text-sm" />
                <input placeholder="Línea 2 (opcional)" value={newAddress.address_line2}
                  onChange={e => setNewAddress({...newAddress, address_line2: e.target.value})}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white text-sm" />
                <div className="grid grid-cols-2 gap-3">
                  <input placeholder="Distrito" value={newAddress.district}
                    onChange={e => setNewAddress({...newAddress, district: e.target.value})}
                    className="bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white text-sm" />
                  <input placeholder="Ciudad" value={newAddress.city}
                    onChange={e => setNewAddress({...newAddress, city: e.target.value})}
                    className="bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white text-sm" />
                </div>
                <input placeholder="Departamento" value={newAddress.department}
                  onChange={e => setNewAddress({...newAddress, department: e.target.value})}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white text-sm" />
                <button onClick={handleCreateAddress}
                  className="w-full bg-[#D92B2B] text-white py-2 rounded-lg font-semibold hover:bg-[#F03C3C] transition-colors">
                  Guardar dirección
                </button>
              </div>
            )}

            {addresses.length === 0 && !showAddressForm && (
              <p className="text-[#A0A0A0] text-sm">No tienes direcciones registradas. Crea una nueva.</p>
            )}

            {addresses.map(addr => (
              <label key={addr.id} className={`flex items-start gap-3 p-4 rounded-xl border cursor-pointer transition-all mb-2 ${
                selectedAddress === addr.id ? 'border-[#D92B2B] bg-[#D92B2B]/10' : 'border-white/10 hover:border-white/20'
              }`}>
                <input type="radio" name="address" value={addr.id}
                  checked={selectedAddress === addr.id}
                  onChange={() => setSelectedAddress(addr.id)}
                  className="mt-1" />
                <div>
                  <p className="text-white text-sm font-semibold">{addr.recipient_name} - {addr.recipient_phone}</p>
                  <p className="text-[#A0A0A0] text-xs">{addr.address_line1}{addr.address_line2 ? `, ${addr.address_line2}` : ''}</p>
                  <p className="text-[#A0A0A0] text-xs">{addr.district}, {addr.city}, {addr.department}</p>
                </div>
              </label>
            ))}
          </div>
        )}

        {/* Resumen de pago */}
        <div className="bg-[#121212] border border-white/10 rounded-2xl p-6 mb-6">
          <h3 className="text-lg font-bold text-white mb-4">Resumen</h3>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-[#A0A0A0]">
                {itemType === 'digital_purchase' ? 'Compra digital' :
                 itemType === 'digital_rental' ? `Alquiler ${rentalDays} días` :
                 'Compra física'}
              </span>
              <span className="text-white">{displaySymbol} {price.toFixed(2)}</span>
            </div>
            {itemType === 'physical_purchase' && (
              <div className="flex justify-between text-sm">
                <span className="text-[#A0A0A0]">Envío (Shalom)</span>
                <span className="text-white">S/ {shippingCost.toFixed(2)}</span>
              </div>
            )}
            <div className="border-t border-white/10 pt-2 mt-2">
              <div className="flex justify-between">
                <span className="text-white font-bold">Total</span>
                <span className="text-[#D4AF37] font-bold text-lg">{displaySymbol} {total.toFixed(2)}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Botón de pago */}
        <button
          onClick={handleCheckout}
          disabled={processing || (!currentPriceData && itemType !== 'physical_purchase')}
          className="w-full bg-[#D92B2B] hover:bg-[#F03C3C] disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold py-4 rounded-xl transition-all flex items-center justify-center gap-2"
        >
          {processing ? (
            <>
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
              Procesando...
            </>
          ) : (
            <>
              <Zap className="w-5 h-5" />
              Pagar {displaySymbol} {total.toFixed(2)}
            </>
          )}
        </button>

        <p className="text-center text-[#A0A0A0] text-xs mt-4">
          {itemType === 'physical_purchase'
            ? 'Serás redirigido para completar el pago de forma segura.'
            : 'Se abrirá el checkout de pago de forma segura.'}
        </p>
      </div>
    </div>
  );
}

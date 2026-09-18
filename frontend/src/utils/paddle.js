/**
 * paddle.js — Inicialización y utilidades de Paddle.js v2.
 *
 * CRÍTICO: Este archivo está diseñado para evitar que Vite/esbuild
 * elimine Paddle.Initialize() y Paddle.Checkout.open() como dead code.
 *
 * Cuando VITE_PADDLE_CLIENT_TOKEN no existe, import.meta.env lo reemplaza
 * por undefined. Si el token se usa en un if() directo, esbuild elimina
 * todo el bloque como dead code.
 *
 * Solución: llamar Paddle.Initialize() SIEMPRE que window.Paddle exista,
 * sin condicionar al token. El token se pasa como string (puede ser ''),
 * y Paddle.js maneja internamente si es válido.
 */

var _initialized = false;
var _paddleAvailable = false;
var _checkoutCompletedCallback = null;

export function isPaddleLoaded() {
  return typeof window !== 'undefined' && typeof window.Paddle !== 'undefined';
}

export function isPaddleReady() {
  return _paddleAvailable;
}

export function initializePaddle() {
  if (_initialized) return;
  _initialized = true;

  if (!isPaddleLoaded()) {
    console.error('[PADDLE] Paddle.js no cargado desde CDN');
    return;
  }

  var token = '';
  try {
    token = import.meta.env.VITE_PADDLE_CLIENT_TOKEN || '';
  } catch (e) {
    token = '';
  }

  window.Paddle.Initialize({
    token: token,
    eventCallback: function (event) {
      if (event && event.name === 'checkout.completed') {
        var pendingOrderId = localStorage.getItem('paddle_pending_order_id');
        if (pendingOrderId && _checkoutCompletedCallback) {
          _checkoutCompletedCallback(pendingOrderId);
        }
      }
    },
  });

  _paddleAvailable = true;
}

export function onCheckoutCompleted(callback) {
  _checkoutCompletedCallback = callback;
}

export function openPaddleCheckout(transactionId) {
  if (_paddleAvailable && isPaddleLoaded()) {
    window.Paddle.Checkout.open({
      transactionId: transactionId,
      settings: {
        displayMode: 'overlay',
        theme: 'dark',
        locale: 'es',
      },
    });
    return { success: true };
  }

  if (!isPaddleLoaded()) {
    return { success: false, error: 'paddle_not_loaded' };
  }

  return { success: false, error: 'paddle_not_initialized' };
}

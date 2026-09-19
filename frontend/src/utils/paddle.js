/**
 * paddle.js — Inicialización y utilidades de Paddle.js v2.
 * Usa @paddle/paddle-js (npm) en vez del CDN para evitar bloqueadores de ads.
 */

import { initializePaddle as initPaddle } from '@paddle/paddle-js';

var _paddleInstance = null;
var _checkoutCompletedCallback = null;
var _checkoutClosedCallback = null;

const CLIENT_TOKEN = import.meta.env.VITE_PADDLE_CLIENT_TOKEN || '';
const ENV = import.meta.env.VITE_PADDLE_ENVIRONMENT || 'sandbox';

export function isPaddleLoaded() {
  return true;
}

export function isPaddleReady() {
  return _paddleInstance !== null;
}

export async function initializePaddle() {
  if (_paddleInstance) return;

  if (!CLIENT_TOKEN) {
    console.warn('[PADDLE] VITE_PADDLE_CLIENT_TOKEN no configurado');
    return;
  }

  try {
    _paddleInstance = await initPaddle({
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
      eventCallback: function (event) {
        if (!event || !event.name) return;

        console.log('[PADDLE EVENT]', event.name, event);

        if (event.name === 'checkout.completed') {
          var pendingOrderId = localStorage.getItem('paddle_pending_order_id');
          if (pendingOrderId && _checkoutCompletedCallback) {
            _checkoutCompletedCallback(pendingOrderId);
          }
        } else if (event.name === 'checkout.closed') {
          if (_checkoutClosedCallback) {
            _checkoutClosedCallback();
          }
        }
      },
    });
    console.log('[PADDLE] SDK inicializado correctamente via @paddle/paddle-js');
  } catch (err) {
    console.error('[PADDLE] Error initializing:', err);
  }
}

export function onCheckoutCompleted(callback) {
  _checkoutCompletedCallback = callback;
}

export function onCheckoutClosed(callback) {
  _checkoutClosedCallback = callback;
}

export function openPaddleCheckout(transactionId) {
  if (!_paddleInstance) {
    return { success: false, error: 'paddle_not_initialized' };
  }

  try {
    _paddleInstance.Checkout.open({
      transactionId: transactionId,
      settings: {
        displayMode: 'overlay',
        theme: 'dark',
        locale: 'es',
        variant: 'one-page',
      },
    });
    return { success: true };
  } catch (err) {
    console.error('[PADDLE] Checkout.open error:', err);
    return { success: false, error: err.message };
  }
}

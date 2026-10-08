/**
 * paddle.js — Inicialización y utilidades de Paddle.js v2.
 * El client token se carga desde /api/config/public (y fallback VITE).
 */

import { initializePaddle as initPaddle } from '@paddle/paddle-js';
import axios from 'axios';
import { API } from '../config/api';

var _paddleInstance = null;
var _initPromise = null;
var _checkoutCompletedCallback = null;
var _checkoutClosedCallback = null;
var _runtimeToken = '';
var _runtimeEnv = '';

async function loadPaddleConfig() {
  if (_runtimeToken) return;
  // 1) runtime desde backend
  try {
    const { data } = await axios.get(`${API}/config/public`, { timeout: 8000 });
    if (data && data.paddle_client_token) {
      _runtimeToken = data.paddle_client_token;
      _runtimeEnv = data.paddle_environment || 'production';
      return;
    }
  } catch (e) {
    console.warn('[PADDLE] config/public no disponible', e.message);
  }
  // 2) fallback build-time
  _runtimeToken = import.meta.env.VITE_PADDLE_CLIENT_TOKEN || '';
  _runtimeEnv = import.meta.env.VITE_PADDLE_ENVIRONMENT || 'sandbox';
}

export function isPaddleLoaded() {
  return _paddleInstance !== null;
}

export function isPaddleReady() {
  return _paddleInstance !== null;
}

export async function initializePaddle() {
  if (_paddleInstance) return _paddleInstance;
  if (_initPromise) return _initPromise;

  _initPromise = (async () => {
    await loadPaddleConfig();
    const token = _runtimeToken;
    const environment = _runtimeEnv;

    if (!token) {
      console.warn('[PADDLE] No hay client token (ni runtime ni VITE)');
      _initPromise = null;
      return null;
    }

    // reintentos: el SDK a veces falla la primera vez
    let lastErr = null;
    for (let attempt = 1; attempt <= 3; attempt++) {
      try {
        _paddleInstance = await initPaddle({
          token,
          environment,
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
              if (_checkoutClosedCallback) _checkoutClosedCallback();
            }
          },
        });
        console.log('[PADDLE] SDK listo', attempt, 'env=', environment, 'token=', token.slice(0, 12) + '...');
        _initPromise = null;
        return _paddleInstance;
      } catch (err) {
        lastErr = err;
        console.error('[PADDLE] init intento', attempt, err);
        await new Promise((r) => setTimeout(r, 400 * attempt));
      }
    }
    console.error('[PADDLE] init falló tras reintentos', lastErr);
    _initPromise = null;
    return null;
  })();

  return _initPromise;
}

export async function ensurePaddleReady() {
  if (_paddleInstance) return true;
  await initializePaddle();
  return _paddleInstance !== null;
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

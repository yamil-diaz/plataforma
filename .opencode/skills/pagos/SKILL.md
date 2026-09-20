---
name: pagos
description: Sistema de pagos de AeternumLibrary - Paddle (digital internacional), Culqi (fisico Peru), Flow (Chile), webhooks, checkout, alquileres
---

## Sistema de pagos

### Proveedores

| Proveedor | Uso | Moneda | Region |
|-----------|-----|--------|--------|
| Paddle | Libros digitales | Multi-monedas | Internacional |
| Culqi | Libros fisicos | PEN (Soles) | Peru |
| Flow | Libros digitales | CLP (Pesos) | Chile |

### Flujo Paddle (digital)

1. Usuario selecciona libro y opcion de compra
2. Frontend init Paddle.js con `Paddle.Setup({ seller: ..., product: ... })`
3. Paddle maneja checkout (overlay)
4. Paddle envia webhook a `POST /api/webhooks/paddle`
5. Backend valida webhook con `PADDLE_WEBHOOK_SECRET`
6. Se registra compra en tabla `purchases`
7. Se da acceso al libro

### Flujo Culqi (fisico)

1. Usuario selecciona libro fisico
2. Frontend envia datos a `POST /api/checkout/culqi`
3. Backend crea cargo con Culqi API
4. Se registra en tabla `physical_orders` con costo de envio
5. Culqi envia webhook de confirmacion

### Alquiler digital

- Precio: 30% del precio de compra
- Acceso temporal (30 dias?)
- Se registra en tabla `purchases` con tipo `rental`

### Webhooks

- `POST /api/webhooks/paddle` - Webhooks de Paddle
- `POST /api/webhooks/culqi` - Webhooks de Culqi
- Handler unificado en `backend/webhook_handler.py`
- Idempotencia: verificar si la compra ya existe antes de crear

### Codigo relevante

- Servicio: `backend/commerce_service.py`
- Proveedores: `backend/payment_providers.py`
- Webhooks: `backend/webhook_handler.py`
- Flow: `backend/flow_service.py`
- Frontend checkout: `frontend/src/pages/CheckoutPage.jsx`
- Frontend paddle: `frontend/src/utils/paddle.js`

### Notas importantes

- Los webhooks deben ser idempotentes (pueden recibirse multiples veces)
- Paddle envia IPs whitelisteadas; Culqi usa HMAC verification
- En produccion, verificar que los webhooks apunten a la URL correcta
- El persistent disk almacena los libros; los pagos dan acceso pero no copian archivos

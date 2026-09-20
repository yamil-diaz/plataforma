# Checklist de Migración a Producción de Paddle

## Antes de empezar
- [ ] Completar wizard de onboarding en vendors.paddle.com
- [ ] Pasar verificación KYC (identidad + empresa)
- [ ] Esperar aprobación de Paddle (1-3 días hábiles)

## Credenciales de producción (obtener en Paddle dashboard)
- [ ] API Key → empieza con `pdl_` (sin `sdbx`)
- [ ] Client-side token → empieza con `live_`
- [ ] Webhook secret → empieza con `pdl_ntfset_`

## Configurar en Render (Environment Variables)
- [ ] `PADDLE_API_KEY` = nueva API key de producción
- [ ] `VITE_PADDLE_CLIENT_TOKEN` = nuevo client token de producción
- [ ] `PADDLE_WEBHOOK_SECRET` = nuevo webhook secret de producción
- [ ] `PADDLE_ENVIRONMENT` = `production`
- [ ] `FRONTEND_URL` = `https://aeternumlibrary.com`

## Configurar en Paddle Dashboard
- [ ] Webhook URL: `https://aeternumlibrary.com/api/paddle/webhook`
- [ ] Webhook events: `transaction.completed`, `transaction.payment_failed`, `transaction.updated`
- [ ] Domain approval: agregar `aeternumlibrary.com` en Checkout → Website approval
- [ ] Default payment link: `https://aeternumlibrary.com/checkout`

## Deploy
- [ ] Push a main en git
- [ ] Render hará redeploy automático
- [ ] Verificar en logs que PADDLE_ENVIRONMENT=production

## Verificación
- [ ] Abrir https://aeternumlibrary.com/checkout?book_id=176
- [ ] Hacer un pago real con tarjeta
- [ ] Verificar en Paddle dashboard que el pago aparece como "completed"
- [ ] Verificar que el dinero aparece en Payouts
- [ ] Verificar que el webhook llega (logs de Render)
- [ ] Verificar que la compra aparece en "Mis Compras"
- [ ] Verificar que se envía el email de confirmación

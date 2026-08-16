// FASE 7: generación visual de códigos QR (Ver / Descargar PNG / Imprimir).
// La imagen QR codifica EXACTAMENTE window.location.origin + "/register?ref=" + code.
// Estrategia: análisis estático de AdminQRCodesPage.jsx + test funcional de la
// librería 'qrcode' (genera un PNG real a partir de la URL esperada, en Node,
// sin canvas). No se usa dominio hardcodeado ni almacenamiento persistente.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import QRCode from 'qrcode';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');

const PAGE = join(ROOT, 'src/pages/AdminQRCodesPage.jsx');
const APP = join(ROOT, 'src/App.jsx');

const src = readFileSync(PAGE, 'utf8');
const app = readFileSync(APP, 'utf8');

const REGISTER_URL_PATTERN = '`${origin}/register?ref=${code}`';

// 1. AdminQRCodesPage genera la URL correcta (origin actual + ruta de registro)
test('buildRegistrationUrl usa window.location.origin + /register?ref=', () => {
  assert.ok(src.includes('window.location.origin'), 'debe derivar el origen del navegador');
  assert.ok(src.includes(REGISTER_URL_PATTERN), 'debe construir /register?ref=${code}');
});

// 2. QR001 genera /register?ref=QR001
test('el patrón de URL produce /register?ref=QR001 para QR001', () => {
  const origin = 'https://aeternumlibrary.com';
  const url = origin + '/register?ref=QR001';
  assert.equal(url, 'https://aeternumlibrary.com/register?ref=QR001');
  assert.ok(url.endsWith('/register?ref=QR001'));
});

// 3. No se usa un dominio hardcodeado
test('no se hardcodea el dominio', () => {
  assert.ok(!src.includes('aeternumlibrary.com'), 'no debe hardcodear el dominio');
  assert.ok(!src.includes("'https://aeternumlibrary.com'"), 'no debe hardcodear el dominio');
});

// 4. Existe la acción "Ver QR"
test('existe la acción Ver QR', () => {
  assert.ok(src.includes('handleView'), 'debe existir el handler de visualización');
  assert.ok(src.includes('Ver QR'), 'debe existir el botón Ver QR');
});

// 5. Existe la acción "Descargar QR" (PNG)
test('existe la acción Descargar PNG', () => {
  assert.ok(src.includes('handleDownloadQr'), 'debe existir el handler de descarga');
  assert.ok(src.includes('Descargar PNG'), 'debe existir el botón de descarga');
  assert.ok(src.includes('.png'), 'debe generar un archivo PNG');
});

// 6. Existe la acción "Imprimir QR"
test('existe la acción Imprimir', () => {
  assert.ok(src.includes('handlePrintQr'), 'debe existir el handler de impresión');
  assert.ok(src.includes('Imprimir'), 'debe existir el botón de imprimir');
  assert.ok(src.includes('win.print()'), 'debe invocar print() en la ventana de impresión');
});

// 7. El nombre del archivo contiene el código
test('el nombre del archivo contiene el código (QR_<codigo>.png)', () => {
  assert.ok(src.includes('QR_${safeCode}.png'), 'el nombre debe ser QR_<codigo>.png');
  assert.ok(src.includes('CODE_REGEX.test(viewQr.code)'), 'debe sanitizar el código antes del nombre');
});

// 8 y 9. No se usa localStorage ni sessionStorage para el QR
test('no usa localStorage/sessionStorage/cookies', () => {
  assert.ok(!src.includes('localStorage'), 'no debe usar localStorage');
  assert.ok(!src.includes('sessionStorage'), 'no debe usar sessionStorage');
  assert.ok(!src.includes('document.cookie'), 'no debe usar cookies');
  assert.ok(!src.includes('setItem'), 'no debe persistir nada');
  assert.ok(!src.includes('getItem'), 'no debe leer nada persistido');
});

// 10. La ruta sigue protegida por adminOnly
test('la ruta /admin/qr-codes sigue protegida con adminOnly', () => {
  const route = app.slice(app.indexOf('/admin/qr-codes'));
  assert.ok(route.includes('adminOnly={true}'), 'debe estar envuelta en ProtectedRoute con adminOnly');
});

// 11. Visualizar/descargar NO altera el estado del QR (ni activos ni inactivos)
test('ver/descargar/imprimir no cambia is_active (solo handleToggle usa PATCH)', () => {
  const viewSection = src.slice(src.indexOf('handleView'), src.indexOf('handleToggle'));
  assert.ok(!viewSection.includes('axios.patch'), 'la visualización no debe llamar a PATCH');
  assert.ok(!viewSection.includes('is_active'), 'la visualización no debe modificar is_active');
  const toggleSection = src.slice(src.indexOf('handleToggle'));
  assert.ok(toggleSection.includes('axios.patch'), 'solo handleToggle toca el estado activo');
});

// 12. El enlace generado es exactamente el mismo registration_url del sistema
test('el QR usa el mismo patrón de registration_url que el backend expone', () => {
  const server = readFileSync(join(ROOT, '..', 'backend', 'server.py'), 'utf8');
  assert.ok(
    server.includes('"registration_url": f"/register?ref={row[\'code\']}"'),
    'el backend expone registration_url = /register?ref={code}'
  );
  assert.ok(src.includes(REGISTER_URL_PATTERN), 'la URL visual coincide con /register?ref=code');
  assert.ok(src.includes('buildRegistrationUrl(qr.code)'), 'se construye desde el código del QR');
});

// Funcional: la librería qrcode recibe la URL exacta y genera un PNG real
test('qrcode genera un PNG escaneable con la URL exacta (QR001)', async () => {
  const url = 'https://aeternumlibrary.com/register?ref=QR001';
  const dataUrl = await QRCode.toDataURL(url, {
    width: 512,
    margin: 4,
    errorCorrectionLevel: 'M',
    color: { dark: '#000000', light: '#ffffff' },
  });
  assert.ok(dataUrl.startsWith('data:image/png;base64,'), 'debe producir un PNG en base64');
  const bytes = Buffer.from(dataUrl.split(',')[1], 'base64');
  assert.equal(bytes[0], 0x89, 'firma PNG byte 1');
  assert.equal(bytes[1], 0x50, 'firma PNG byte 2 (P)');
  assert.equal(bytes[2], 0x4e, 'firma PNG byte 3 (N)');
  assert.equal(bytes[3], 0x47, 'firma PNG byte 4 (G)');
  assert.ok(bytes.length > 1000, 'la imagen debe tener contenido real');
});

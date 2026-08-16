import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');

const PAGE = join(ROOT, 'src/pages/AdminQRCodesPage.jsx');
const APP = join(ROOT, 'src/App.jsx');
const DASH = join(ROOT, 'src/pages/DashboardPage.jsx');

const src = readFileSync(PAGE, 'utf8');
const app = readFileSync(APP, 'utf8');
const dash = readFileSync(DASH, 'utf8');

// 1. La ruta usa el mecanismo adminOnly existente (ProtectedRoute)
test('la ruta /admin/qr-codes usa el adminOnly existente', () => {
  const route = app.slice(app.indexOf('/admin/qr-codes'));
  assert.ok(route.includes('adminOnly={true}'), 'debe estar envuelta en ProtectedRoute con adminOnly');
  assert.ok(route.includes('AdminQRCodesPage'), 'debe renderizar AdminQRCodesPage');
});

// 2. El menú administrativo enlaza a la página
test('el menú admin del dashboard enlaza a /admin/qr-codes', () => {
  assert.ok(dash.includes('to="/admin/qr-codes"'), 'DashboardPage debe tener el enlace administrativo');
});

// 3. Título y botón de creación
test('la página muestra el título y el botón de crear', () => {
  assert.ok(src.includes('Códigos QR'), 'debe mostrar el título');
  assert.ok(src.includes('Crear código QR'), 'debe mostrar el botón de creación');
});

// 4. Muestra los QR con estado, visitas, registros y enlace
test('la página lista los QR con estado, visitas, registros y enlace', () => {
  assert.ok(src.includes('qrCodes.map('), 'debe renderizar el listado');
  assert.ok(src.includes('Activo'), 'debe mostrar el estado Activo');
  assert.ok(src.includes('Inactivo'), 'debe mostrar el estado Inactivo');
  assert.ok(src.includes('>Visitas<'), 'columna Visitas');
  assert.ok(src.includes('>Registros<'), 'columna Registros');
  assert.ok(src.includes('>Enlace<'), 'columna Enlace');
  assert.ok(src.includes('>Acciones<'), 'columna Acciones');
});

// 5. Genera /register?ref=CODE con el origen actual del navegador
test('genera /register?ref=CODE usando el origen del navegador', () => {
  assert.ok(src.includes("`${origin}/register?ref=${code}`"), 'debe construir el enlace con el código');
  assert.ok(src.includes('window.location.origin'), 'debe usar el origen actual del navegador');
  assert.ok(!src.includes('aeternumlibrary.com'), 'no debe hardcodear el dominio');
});

// 6. No usa localStorage/sessionStorage/cookies
test('no usa localStorage/sessionStorage/cookies', () => {
  assert.ok(!src.includes('localStorage'), 'no debe usar localStorage');
  assert.ok(!src.includes('sessionStorage'), 'no debe usar sessionStorage');
  assert.ok(!src.includes('document.cookie'), 'no debe usar cookies');
  assert.ok(!src.includes('setItem'), 'no debe persistir nada');
});

// 7. Crear QR envía code y name al endpoint correcto
test('crear QR envía code y name a POST /api/admin/qr-codes', () => {
  assert.ok(src.includes('axios.post(`${API}/admin/qr-codes`'), 'debe llamar al endpoint de creación');
  assert.ok(src.includes('{ code, name }'), 'debe enviar code y name');
  assert.ok(src.includes('CODE_REGEX'), 'debe validar el código en frontend');
});

// 8. Activar/desactivar llama al endpoint correcto
test('activar/desactivar llama a PATCH /api/admin/qr-codes/{id}', () => {
  assert.ok(src.includes('axios.patch('), 'debe llamar al endpoint de toggle');
  assert.ok(src.includes('`${API}/admin/qr-codes/${qr.id}`'), 'debe apuntar a /admin/qr-codes/{id}');
  assert.ok(src.includes('is_active'), 'debe enviar is_active');
  assert.ok(src.includes('window.confirm'), 'debe confirmar antes de desactivar');
});

// 9. Copiar enlace usa el portapapeles
test('copiar enlace usa navigator.clipboard.writeText', () => {
  assert.ok(src.includes('navigator.clipboard.writeText'), 'debe usar el portapapeles');
});

// 10. Errores no rompen la página
test('los errores no rompen la página: hay estado de error y catch', () => {
  assert.ok(src.includes('setError'), 'debe existir estado de error');
  assert.ok(src.includes('catch (err)'), 'debe capturar errores');
  assert.ok(src.includes('err.response?.data?.detail'), 'debe leer el detail del backend');
});
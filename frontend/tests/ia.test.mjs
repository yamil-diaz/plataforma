// FASE 8.10: INTERFAZ DE USUARIO DE LA IA DE AETERNUM (/ia).
// Estrategia: análisis estático de IAPage.jsx / App.jsx / Navbar.jsx
// (contratos de seguridad y UX) + tests funcionales de la lógica pura
// (utils/iaChat.js) que la página importa. Sin navegador, sin almacenamiento.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { buildChatBody, parseErrorDetail } from '../src/utils/iaChat.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');

const PAGE = readFileSync(join(ROOT, 'src/pages/IAPage.jsx'), 'utf8');
const APP = readFileSync(join(ROOT, 'src/App.jsx'), 'utf8');
const NAVBAR = readFileSync(join(ROOT, 'src/components/Navbar.jsx'), 'utf8');

// ── 1. Ruta protegida (sin adminOnly) ───────────────────────────────────────
test('la ruta /ia existe y requiere autenticación', () => {
  assert.ok(APP.includes('path="/ia"'), 'debe existir la ruta /ia');
  assert.ok(APP.includes('<ProtectedRoute>'), 'debe usar ProtectedRoute');
});

test('la ruta /ia NO es adminOnly', () => {
  const idx = APP.indexOf('path="/ia"');
  const block = APP.slice(idx, idx + 400);
  assert.ok(!block.includes('adminOnly'), 'un usuario normal debe poder acceder');
});

// ── 2. Sin almacenamiento persistente de conversaciones ─────────────────────
test('IAPage no usa localStorage ni sessionStorage ni document.cookie', () => {
  assert.ok(!PAGE.includes('localStorage.'), 'no debe usar localStorage');
  assert.ok(!PAGE.includes('localStorage['), 'no debe usar localStorage');
  assert.ok(!PAGE.includes('sessionStorage.'), 'no debe usar sessionStorage');
  assert.ok(!PAGE.includes('sessionStorage['), 'no debe usar sessionStorage');
  assert.ok(!PAGE.includes('document.cookie'), 'no debe usar document.cookie');
});

// ── 3. API consumida ────────────────────────────────────────────────────────
test('usa POST /api/ai/chat, GET /api/ai/conversations y los mensajes', () => {
  assert.ok(PAGE.includes('`${API}/ai/chat`'), 'debe llamar a /ai/chat');
  assert.ok(PAGE.includes('${API}/ai/conversations`'), 'debe listar conversaciones');
  assert.ok(
    PAGE.includes('`${API}/ai/conversations/${conversationId}/messages`'),
    'debe cargar mensajes de una conversación'
  );
});

test('usa DELETE /api/ai/conversations/{id} para eliminar', () => {
  assert.ok(
    PAGE.includes('`${API}/ai/conversations/${deleteTarget.id}`'),
    'debe eliminar la conversación en el backend'
  );
});

// ── 4. El body del chat NUNCA envía identidad ni costes ─────────────────────
test('buildChatBody solo envía message (+ conversation_id cuando existe)', () => {
  const body = buildChatBody({ message: 'Hola', conversationId: 7 });
  assert.deepEqual(body, { message: 'Hola', conversation_id: 7 });
});

test('buildChatBody sin conversación envía solo message (el servidor crea)', () => {
  const body = buildChatBody({ message: 'Hola', conversationId: null });
  assert.deepEqual(body, { message: 'Hola' });
});

test('buildChatBody nunca incluye user_id, role, provider, model ni coste', () => {
  const body = buildChatBody({ message: 'Hola', conversationId: 3 });
  const keys = Object.keys(body);
  assert.ok(!keys.includes('user_id'), 'no envía user_id');
  assert.ok(!keys.includes('role'), 'no envía role');
  assert.ok(!keys.includes('provider'), 'no envía provider');
  assert.ok(!keys.includes('model'), 'no envía model');
  assert.ok(!keys.includes('cost'), 'no envía coste');
  assert.ok(!keys.includes('coste'), 'no envía coste');
});

test('contexto del lector queda preparado pero vacío por defecto', () => {
  const body = buildChatBody({ message: 'Hola', conversationId: 1, context: null });
  assert.deepEqual(body, { message: 'Hola', conversation_id: 1 });
  const withContext = buildChatBody({
    message: 'Hola',
    conversationId: null,
    context: { bookId: 10, pageNumber: 3, chapterId: 5 },
  });
  assert.deepEqual(withContext, {
    message: 'Hola',
    book_id: 10,
    page_number: 3,
    chapter_id: 5,
  });
  assert.ok(!withContext.user_id && !withContext.role, 'el contexto tampoco añade identidad');
});

// ── 5. Rayos: solo información visual, nunca cálculo ────────────────────────
test('IAPage muestra el saldo pero no calcula ni descuenta Rayos', () => {
  assert.ok(PAGE.includes('user.rayos_balance'), 'debe mostrar el saldo del usuario');
  const lines = PAGE.split('\n').filter((l) => l.includes('rayos_balance'));
  for (const line of lines) {
    assert.ok(
      !/[+*/-]\s*\d/.test(line) && !line.includes('parseInt') && !line.includes('Number(') && !line.includes('price') && !line.includes('tarifa'),
      `el saldo solo se muestra, no se calcula: ${line.trim()}`
    );
  }
  assert.ok(!PAGE.toLowerCase().includes('tarifa'), 'no debe inventar una tarifa de IA');
  assert.ok(!PAGE.includes('axios.post(`${API}/ai/chat`'), 'el envío no descuenta saldo');
});

// ── 6. UX requerida ─────────────────────────────────────────────────────────
test('existe mensaje de bienvenida y estado vacío', () => {
  assert.ok(PAGE.includes('Bienvenido a la IA de Aeternum'), 'debe haber bienvenida');
  assert.ok(PAGE.includes('No tienes conversaciones todavía'), 'debe haber estado vacío');
});

test('existe estado de carga', () => {
  assert.ok(PAGE.includes('Cargando mensajes'), 'debe haber loading de mensajes');
  assert.ok(PAGE.includes('animate-spin'), 'debe haber indicador de carga');
});

test('existe manejo de errores con mensaje visible', () => {
  assert.ok(PAGE.includes('parseErrorDetail'), 'debe usar mensajes legibles de error');
  assert.ok(PAGE.includes('No se pudo enviar el mensaje'), 'debe haber fallback de error');
});

test('input multilinea con Enter para enviar y Shift+Enter para salto de línea', () => {
  assert.ok(PAGE.includes('<textarea'), 'debe ser textarea multilinea');
  assert.ok(PAGE.includes("e.key === 'Enter' && !e.shiftKey"), 'Enter envía');
  assert.ok(PAGE.includes('e.shiftKey'), 'Shift+Enter salta de línea');
});

test('existen botones de enviar, nueva conversación y eliminar', () => {
  assert.ok(PAGE.includes('handleSend'), 'debe existir envío');
  assert.ok(PAGE.includes('Nueva conversación'), 'debe existir el botón Nueva conversación');
  assert.ok(PAGE.includes('handleDeleteConfirm'), 'debe existir eliminación');
  assert.ok(PAGE.includes('Eliminar conversación'), 'debe existir modal de confirmación');
});

test('auto-scroll y disabled mientras se procesa', () => {
  assert.ok(PAGE.includes('scrollIntoView'), 'debe haber auto-scroll');
  assert.ok(PAGE.includes('disabled={sending'), 'el input se deshabilita al enviar');
  assert.ok(PAGE.includes('disabled={sending || !input.trim()}'), 'el botón se deshabilita al enviar');
});

test('el estado se actualiza tras crear, enviar, eliminar y cambiar conversación', () => {
  assert.ok(PAGE.includes('data.conversation_id'), 'usa la conversación devuelta por el backend');
  assert.ok(PAGE.includes('fetchConversations()'), 'refresca la lista tras operaciones');
  assert.ok(PAGE.includes('setSelectedId(null)'), 'limpia la selección al crear/eliminar');
});

test('la UI no envía user_id como autoridad en ningún request', () => {
  assert.ok(!PAGE.includes('user_id'), 'no debe referenciar user_id en el frontend');
  assert.ok(!PAGE.includes('user.id'), 'no debe enviar la identidad del usuario');
});

test('el enlace IA está en la Navbar y solo para usuarios autenticados', () => {
  assert.ok(NAVBAR.includes('to="/ia"'), 'debe existir el enlace en la Navbar');
  const idx = NAVBAR.indexOf('to="/ia"');
  const block = NAVBAR.slice(Math.max(0, idx - 120), idx);
  assert.ok(block.includes('user &&'), 'debe ser visible solo con sesión iniciada');
});

// ── 7. Lógica pura: parseErrorDetail ────────────────────────────────────────
test('parseErrorDetail usa el detail del backend', () => {
  const err = { response: { data: { detail: 'No tienes suficientes Rayos' } } };
  assert.equal(parseErrorDetail(err, 'fallback'), 'No tienes suficientes Rayos');
});

test('parseErrorDetail usa fallback seguro sin detalle', () => {
  assert.equal(parseErrorDetail(null, 'fallback'), 'fallback');
  assert.equal(parseErrorDetail({ message: 'Network Error' }, 'fallback'), 'fallback');
  assert.equal(parseErrorDetail({}, 'fallback'), 'fallback');
});
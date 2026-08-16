import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { sanitizeRef } from '../src/utils/ref.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');

// 1. /register sin ref -> ref = null
test('sin ref (searchParams.get devuelve null) -> null', () => {
  assert.equal(sanitizeRef(null), null);
  assert.equal(sanitizeRef(undefined), null);
});

// 2. /register?ref=QR001 -> QR001
test('ref QR001 -> "QR001"', () => {
  assert.equal(sanitizeRef('QR001'), 'QR001');
});

// 3. /register?ref=QR-001 -> QR-001
test('ref QR-001 -> "QR-001"', () => {
  assert.equal(sanitizeRef('QR-001'), 'QR-001');
});

// 4. /register?ref=QR_001 -> QR_001
test('ref QR_001 -> "QR_001"', () => {
  assert.equal(sanitizeRef('QR_001'), 'QR_001');
});

// 5. ref inválido -> null
test('ref inválido -> null', () => {
  assert.equal(sanitizeRef('FAKE!!!'), null);
  assert.equal(sanitizeRef('<script>'), null);
  assert.equal(sanitizeRef(''), null);
  assert.equal(sanitizeRef('con espacio'), null);
  assert.equal(sanitizeRef('QR001'.repeat(7)), null);
  assert.equal(sanitizeRef('QR.001'), null);
});

// 6. el registro normal no cambia: sin ref, el body NO incluye la clave ref
test('sin ref el POST no incluye el campo ref', () => {
  const body = JSON.stringify({ name: 'A', email: 'a@b.c', password: 'x', ref: undefined });
  assert.equal(body, JSON.stringify({ name: 'A', email: 'a@b.c', password: 'x' }));
  assert.ok(!body.includes('ref'));
});

// 7. no se usan localStorage/sessionStorage/cookies para guardar el ref
test('RegisterPage.jsx no usa almacenamiento persistente para el ref', () => {
  const src = readFileSync(join(ROOT, 'src/pages/RegisterPage.jsx'), 'utf8');
  assert.ok(!src.includes('localStorage'), 'RegisterPage.jsx no debe usar localStorage');
  assert.ok(!src.includes('sessionStorage'), 'RegisterPage.jsx no debe usar sessionStorage');
  assert.ok(!src.includes('document.cookie'), 'RegisterPage.jsx no debe usar cookies');
});

test('AuthContext.jsx no usa almacenamiento persistente para el ref', () => {
  const src = readFileSync(join(ROOT, 'src/contexts/AuthContext.jsx'), 'utf8');
  assert.ok(!src.includes('localStorage'), 'AuthContext.jsx no debe usar localStorage');
  assert.ok(!src.includes('sessionStorage'), 'AuthContext.jsx no debe usar sessionStorage');
  assert.ok(!src.includes('document.cookie'), 'AuthContext.jsx no debe usar cookies');
});

// Estáticos: el valor capturado se transporta por estado de React
test('RegisterPage captura ?ref= con useSearchParams y lo pasa a register()', () => {
  const src = readFileSync(join(ROOT, 'src/pages/RegisterPage.jsx'), 'utf8');
  assert.ok(src.includes('useSearchParams'), 'debe usar useSearchParams');
  assert.ok(src.includes("searchParams.get('ref')"), 'debe leer el parámetro ref');
  assert.ok(src.includes('sanitizeRef'), 'debe validar con sanitizeRef');
  assert.ok(src.includes('register(name, email, password, ref)'), 'debe pasar el ref a register()');
});

test('AuthContext envía el ref en el body del POST /register', () => {
  const src = readFileSync(join(ROOT, 'src/contexts/AuthContext.jsx'), 'utf8');
  assert.ok(src.includes('ref: ref || undefined'), 'debe incluir ref en el body (omitido si es null)');
});

// ── FASE 5: tracking de visita (best effort) ──────────────────────────────

test('tracking: sin ref válido no se llama al endpoint de visita', () => {
  const src = readFileSync(join(ROOT, 'src/pages/RegisterPage.jsx'), 'utf8');
  assert.ok(src.includes('if (!ref) return;'), 'sin ref válido el tracking no se dispara');
});

test('tracking: con ref válido se llama al endpoint una vez por montaje', () => {
  const src = readFileSync(join(ROOT, 'src/pages/RegisterPage.jsx'), 'utf8');
  assert.ok(src.includes('useEffect'), 'debe usar useEffect (una sola vez por montaje)');
  assert.ok(src.includes("useEffect(() => {"), 'el tracking debe estar en un useEffect');
  assert.ok(src.includes('axios'), 'debe usar axios para el tracking');
  assert.ok(src.includes('.post(`${API}/qr/${ref}/visit`'), 'debe llamar a POST /api/qr/{ref}/visit');
});

test('tracking: best effort, un error no rompe el registro ni muestra errores', () => {
  const src = readFileSync(join(ROOT, 'src/pages/RegisterPage.jsx'), 'utf8');
  assert.ok(src.includes('.catch(() => {})'), 'los errores de tracking se tragan silenciosamente');
  assert.ok(src.includes('AbortController'), 'aborta la petición al desmontar (StrictMode)');
  const submit = src.slice(src.indexOf('handleSubmit'));
  assert.ok(!submit.includes('visit'), 'el submit del registro no depende del tracking');
});

test('tracking: no usa localStorage/sessionStorage/cookies', () => {
  const src = readFileSync(join(ROOT, 'src/pages/RegisterPage.jsx'), 'utf8');
  assert.ok(!src.includes('localStorage'), 'RegisterPage.jsx no debe usar localStorage');
  assert.ok(!src.includes('sessionStorage'), 'RegisterPage.jsx no debe usar sessionStorage');
  assert.ok(!src.includes('document.cookie'), 'RegisterPage.jsx no debe usar cookies');
});

test('tracking: el ref no se guarda en ningún almacenamiento persistente', () => {
  const src = readFileSync(join(ROOT, 'src/pages/RegisterPage.jsx'), 'utf8');
  assert.ok(!src.includes('setItem'), 'no debe persistir el ref con setItem');
  assert.ok(!src.includes('getItem'), 'no debe leer el ref con getItem');
});
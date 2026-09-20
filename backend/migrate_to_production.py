#!/usr/bin/env python3
"""
Migración de sandbox a producción de Paddle.
Ejecutar después de que Paddle apruebe la cuenta de producción.

Este script NO cambia env vars — eso se hace en Render.
Solo documenta los pasos y verifica la configuración.
"""
import os
import sys

def check_sandbox_config():
    """Verifica la configuración actual de sandbox."""
    print("=" * 60)
    print("CONFIGURACIÓN ACTUAL (SANDBOX)")
    print("=" * 60)

    api_key = os.getenv("PADDLE_API_KEY", "")
    env = os.getenv("PADDLE_ENVIRONMENT", "sandbox")

    if "sdbx" in api_key:
        print(f"  API Key: {api_key[:20]}... (SANDBOX)")
    else:
        print(f"  API Key: {api_key[:20]}... (PRODUCCIÓN)")

    print(f"  Environment: {env}")
    print()

def print_migration_steps():
    """Imprime los pasos de migración."""
    print("=" * 60)
    print("PASOS PARA MIGRAR A PRODUCCIÓN")
    print("=" * 60)
    print()
    print("1. COMPLETAR WIZARD DE PADDLE")
    print("   - Ir a vendors.paddle.com")
    print("   - Completar onboarding")
    print("   - Pasar verificación KYC")
    print()
    print("2. OBTENER CREDENCIALES DE PRODUCCIÓN")
    print("   - API Key: Developer Tools → Authentication → API Keys")
    print("   - Client Token: Developer Tools → Authentication → Client-side token")
    print("   - Webhook Secret: Developer Tools → Notifications → Endpoint secret")
    print()
    print("3. CONFIGURAR EN RENDER (Environment Variables)")
    print("   PADDLE_API_KEY=<tu_api_key_de_produccion>")
    print("   VITE_PADDLE_CLIENT_TOKEN=<tu_client_token_de_produccion>")
    print("   PADDLE_WEBHOOK_SECRET=<tu_webhook_secret_de_produccion>")
    print("   PADDLE_ENVIRONMENT=production")
    print("   FRONTEND_URL=https://aeternumlibrary.com")
    print()
    print("4. CONFIGURAR WEBHOOK EN PADDLE")
    print("   - URL: https://aeternumlibrary.com/api/paddle/webhook")
    print("   - Events: transaction.completed, transaction.payment_failed, transaction.updated")
    print()
    print("5. CONFIGURAR DOMINIO EN PADDLE")
    print("   - Checkout → Website approval → Agregar aeternumlibrary.com")
    print()
    print("6. CONFIGURAR DEFAULT PAYMENT LINK")
    print("   - Checkout → Checkout settings → Default payment link")
    print("   - Poner: https://aeternumlibrary.com/checkout")
    print()
    print("7. REDEPLOY EN RENDER")
    print("   - Push a main para redeploy automático")
    print("   - Verificar que las env vars se actualicen")
    print()
    print("8. PROBAR PAGO REAL")
    print("   - Usar tarjeta real en https://aeternumlibrary.com/checkout?book_id=176")
    print("   - Verificar que el webhook llega y marca como 'approved'")
    print("   - Verificar que el dinero aparece en Paddle dashboard")
    print()

if __name__ == "__main__":
    check_sandbox_config()
    print_migration_steps()

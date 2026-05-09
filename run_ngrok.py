from pyngrok import ngrok
import time

print("=" * 60)
print("INICIANDO SERVIDOR PUBLICO")
print("=" * 60)

public_url = ngrok.connect(5000, "http")
print("\nURL PUBLICA PARA TUS TECNICOS:")
print(public_url)
print("\n" + "=" * 60)
print("Esta URL funciona desde cualquier dispositivo")
print("Tus tecnicos pueden acceder desde su telefono")
print("\nPresiona Ctrl+C para detener")
print("=" * 60 + "\n")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nDeteniendo servidor...")
    ngrok.kill()
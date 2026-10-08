# Skill: Screenshots para debug

Cuando el usuario necesite mostrarte una captura de pantalla:

1. Pídele que guarde la imagen en `C:\Users\Z\Desktop\plataforma\screenshots\`
2. Usa la herramienta `Read` para leer la imagen (soporta PNG, JPG, etc.)
3. Analiza lo que ves en la imagen y guía al usuario

Ejemplo:
```
usuario: mira pantalla1.png
asistente: [usa Read para leer C:\Users\Z\Desktop\plataforma\screenshots\pantalla1.png]
```

Esto permite debug visual sin necesidad de herramientas externas.

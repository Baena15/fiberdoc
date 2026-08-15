# FiberDoc — Frontend React

SPA en React + TypeScript + Tailwind CSS que consume la API REST del backend
Django (sesión + CSRF). Vistas de esta fase:

- **Login** (`/login`): autenticación por sesión contra `POST /api/auth/login/`.
- **Panel de obra** (`/`): selector de obra y tarjetas de elementos de red con
  semáforo agregado (OK / aviso / fuera de umbral) a partir de
  `GET /api/elementos/{id}/resumen/`.
- **SpliceMatrix** (`/elementos/:id`): matriz de fusiones entre dos cables del
  elemento (`GET /api/elementos/{id}/matriz/`), con detalle de fusión al tocar
  una celda.

## Desarrollo

```bash
npm install
npm run dev
```

El dev server de Vite (puerto 5173) proxifica `/api` y `/admin` a
`http://localhost:8000` (ver `vite.config.ts`), de modo que las cookies de
sesión y CSRF funcionan como same-origin sin configurar CORS. Arranca el
backend con `python manage.py runserver` y datos demo con
`python manage.py seed_demo` (usuarios `admin` / `capataz` / `fusionador`,
password `FibraSur-demo-2026`).

## Build

```bash
npm run build
```

Genera `frontend/dist/` con los estáticos de producción. En producción Django
puede servir este directorio (la configuración concreta se resolverá en la
fase de despliegue).

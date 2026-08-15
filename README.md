# FiberDoc — Backend (TFM, semana 1)

Backend de **FiberDoc**: documentación y trazabilidad de redes FTTH (fusiones,
CTOs, splitters, obras y unidades de obra) para contratas instaladoras.

Stack: **Django 5 + DRF + PostgreSQL 16 (Docker)**, drf-spectacular (OpenAPI),
pytest/pytest-django, Pillow y psycopg 3.

## Requisitos

- Python 3.12 y pip (dev local), o
- Docker + Docker Compose (entorno completo con Postgres 16).

## Quickstart — desarrollo local (SQLite)

Sin `DATABASE_URL` el proyecto cae a SQLite, suficiente para desarrollo y tests:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

- Admin: <http://localhost:8000/admin/>
- API navegable: <http://localhost:8000/api/>
- Swagger/OpenAPI: <http://localhost:8000/api/docs/>

Para crear el superusuario del admin: `python manage.py createsuperuser`.

## Quickstart — Docker (PostgreSQL 16)

```bash
cp .env.example .env
docker compose up --build
# En otra terminal:
docker compose exec web python manage.py seed_demo
```

El servicio `web` aplica las migraciones al arrancar y usa
`DATABASE_URL=postgres://fiberdoc:fiberdoc@db:5432/fiberdoc`.

## Credenciales demo (seed_demo)

Todos los usuarios demo usan la password **`FibraSur-demo-2026`**:

| Usuario      | Rol                | Acceso admin |
|--------------|--------------------|--------------|
| `admin`      | ADMIN_CONTRATA     | sí (staff)   |
| `capataz`    | CAPATAZ            | no           |
| `fusionador` | FUSIONADOR         | no           |

Contrata: **FibraSur Instalaciones** · Cliente: **NorteNet** · Obra: **OB-2026-014**
(1 ODF, 3 empalmes, 4 CTOs con splitters 1:4→1:8 en cascada, troncal 144F,
distribución 24F, 150 fusiones ~85 % OK / 12 % WARNING / 3 % FUERA con 2
subsanadas, pasos de tubo en EMPALME-01 y tarifa con 6 ítems).

## Estructura

```
fiberdoc/
├── manage.py
├── config/                 # settings (env), urls, wsgi, asgi
├── apps/
│   ├── accounts/           # Contrata (tenant), User custom, Trabajador
│   ├── core/               # Cliente, PerfilOperadora, EsquemaColor, TarifaUO/TarifaItem
│   └── network/            # Obra, OrdenTrabajo, ElementoRed, Cable, PasoTubo,
│                           # Splitter, Puerto, Fusion, Conexion + API + seed_demo
├── tests/                  # pytest: invariantes I1-I4, multi-tenant, API, auth SPA
├── frontend/               # SPA React 19 + TS + Vite + Tailwind (login, panel, SpliceMatrix)
├── Dockerfile / docker-compose.yml
├── requirements.txt        # fijado
└── .github/workflows/ci.yml
```

## API

Autenticación por **sesión Django** (`/api-auth/login/` en desarrollo).
Permiso `IsSameContrata`: cada queryset se filtra por `request.user.contrata`,
así que un usuario de otra contrata recibe **404** en detalle y listados vacíos.

ViewSets CRUD: `obras`, `elementos`, `cables`, `fusiones`, `conexiones`,
`pasos-tubo`, `splitters`, `puertos`, `ordenes`.

Endpoints especiales:

- `GET /api/elementos/{id}/resumen/` → conteos por estado y por nivel
  (OK/WARNING/FUERA según umbrales de la obra).
- `GET /api/elementos/{id}/matriz/?cable_a=&cable_b=` → filas *sparse* de
  fusiones entre dos cables (para la matriz React).

Endpoints de autenticación SPA (sesión Django):

- `POST /api/auth/login/` `{username, password}` → 200 `{id, username, rol, contrata}` / 401
- `POST /api/auth/logout/` → 204
- `GET /api/auth/me/` → 200 usuario actual / 401 (siembra la cookie `csrftoken`)

## Frontend React (`frontend/`)

SPA en **React 19 + TypeScript + Vite + Tailwind CSS** (requisito TFM: vistas
React consumiendo datos reales del backend). Tres vistas:

- **Login** (`/login`) — sesión Django vía `/api/auth/login/` (CSRF por cookie).
- **Panel de obra** (`/`) — selector de obra y tarjetas de elementos con
  semáforo agregado (peor nivel de su `/resumen/`) y conteos OK/WARNING/FUERA.
- **SpliceMatrix** (`/elementos/:id`) — matriz de fusiones entre dos cables
  (rejilla `n_tubos × fibras_por_tubo` construida sobre las filas sparse de
  `/matriz/`), celda coloreada por nivel y modal de detalle. Mobile-first
  (técnico con guantes junto a la furgoneta).

Desarrollo (con el backend corriendo en `:8000`):

```bash
cd frontend
npm install
npm run dev        # vite proxy /api y /admin -> http://localhost:8000
npm run build      # build de producción en frontend/dist/
```

## Tests y verificación

```bash
pytest                              # batería completa
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py seed_demo          # sobre BD migrada
```

CI en `.github/workflows/ci.yml`: pytest contra PostgreSQL 16 (servicio de
GitHub Actions), `check` y `makemigrations --check`.

## Decisiones de diseño

- **Multi-tenant por FK**: una FK `contrata` (en el modelo o accesible por la
  cadena de FKs) y filtrado de querysets + permiso `IsSameContrata`. Sin
  django-tenants ni esquemas: suficiente para el alcance del TFM.
- **Sin GIS**: lat/long como `DecimalField` simples; no se necesita PostGIS.
- **Sin .sor**: la subida de trazas OTDR queda fuera de la semana 1 (Pillow ya
  está preparado para futuros uploads).
- **Sesión, no JWT**: el frontend será una SPA servida desde el mismo dominio;
  la sesión de Django simplifica CSRF y admin.
- **Índices únicos parciales** (`UniqueConstraint(condition=Q(activa=True))`)
  para el invariante I1 en `Fusion`/`Conexion` (puerto_a y puerto_b) y para la
  posición de bandeja; CHECKs de `Puerto` por tipo y de pérdida 0–3 dB (I3).
- **Concurrencia optimista** en `Fusion`/`Conexion` con campo `version`.
- **`Trabajador.contrata`**: se añade aunque el SPEC no la lista explícitamente,
  para poder filtrar por tenant trabajadores sin usuario asociado.
- **TarifaUO/TarifaItem**: cabecera por cliente + líneas con
  código/descripción/precio/unidad (los ejemplos de código del SPEC —FUS-EMPALME,
  MONT-CTO-16, M-TENDIDO— son ítems).

## Limitaciones conocidas de esta entrega

- Sin Celery/Redis, sin subida de archivos. El frontend React aún no se sirve
  desde Django en producción (se hará en la fase de despliegue).
- El Dockerfile/compose se ha validado por inspección en el sandbox de desarrollo
  (Docker no disponible ahí); `docker compose up --build` es la vía prevista.

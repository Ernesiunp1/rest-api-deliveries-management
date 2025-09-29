# 🚴‍♂️ API de Gestión de Domicilios

API desarrollada con **FastAPI** para la gestión de domicilios, clientes, entregas y pagos.  
Permite organizar de manera centralizada el flujo de pedidos, asignación de domiciliarios, administración de clientes y control de pagos.

---

## 🚀 Tecnologías
- **FastAPI** (Framework principal)
- **SQLAlchemy** (ORM)
- **SQLite** (Base de datos por defecto)
- **Pydantic** (Validación de esquemas)
- **CORS Middleware** (Integración con frontend Angular/Ionic)

---

## 📂 Estructura Básica
main.py # Punto de entrada de la API
db/db.py # Configuración de la base de datos
routes/client_route # Rutas de clientes
routes/delivery_route# Rutas de entregas
models/models.py # Modelos SQLAlchemy
schemas/schemas.py # Validación de datos (Pydantic)


---

## ⚙️ Configuración de la Base de Datos
Por defecto, la API utiliza **SQLite** (`domicilios.db`):

```python
SQLALCHEMY_DATABASE_URL = "sqlite:///./domicilios.db"
```

🔑 Autenticación

La API maneja autenticación basada en usuario y roles (por ejemplo, ADMIN) para restringir operaciones críticas como la actualización o eliminación de clientes.

📌 Endpoints Principales
👥 Clientes (/client)

POST /create_client → Crear un cliente nuevo.

GET /get_all → Listar todos los clientes.

GET /by_name → Buscar un cliente por nombre (incluye entregas asociadas).

PUT /update → Actualizar cliente (solo ADMIN).

DELETE /delete → Desactivar cliente (solo ADMIN).

📦 Entregas (/deliveries)

GET / → Listar todas las entregas (con paginación y filtro por estado).

GET /filtered → Filtrar entregas por rango de fechas (today, week, month, custom).

POST /new_delivery → Crear entrega y generar automáticamente el pago asociado.

POST /generate-label/ → Generar etiqueta en PDF con datos del envío.

GET /get_deliveries_by_status → Filtrar entregas por estado.

GET /client → Obtener entregas de un cliente específico.

PUT /add_rider → Asignar domiciliario a una entrega.

PUT /update → Actualizar datos de una entrega.

GET /states → Obtener lista de estados de entrega disponibles.

▶️ Ejecución

Clona el proyecto y ejecuta con:

uvicorn main:app --reload


La API estará disponible en:
👉 http://localhost:8000

Documentación automática:

Swagger UI → http://localhost:8000/docs

ReDoc → http://localhost:8000/redoc

📌 Próximos Módulos

La API incluye también rutas para:

Usuarios (/users)

Riders (/riders)

Pagos (/payments)

# SGSM - Sistema de Gestión de Salud Médica

## Descripción

Sistema completo para la gestión de citas médicas con:
- **ORM SQLAlchemy 2.0** con 5+ entidades mapeadas
- **Migraciones con Alembic** (2 versiones de migración)
- **Repositorios CRUD** optimizados sin problema N+1
- **Pruebas de integración** con pytest
- **Pipeline CI/CD** con GitHub Actions

## Requisitos

- Python 3.9+
- SQLAlchemy 2.0+
- Alembic 1.13+
- Flask 3.0+
- pytest 7.4+

## Instalación

```bash
# Clonar repositorio
git clone https://github.com/BrayanUmb/SGSM.git
cd SGSM

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

## Estructura del Proyecto

```
SGSM/
├── app.py                      # Configuración Flask y SQLAlchemy
├── models.py                   # Modelos ORM (SQLAlchemy 2.0)
├── repositories.py             # Repositorios CRUD optimizados
├── alembic/                    # Configuración de Alembic
│   ├── versions/
│   │   ├── 001_initial_schema.py    # Migración inicial (crea tablas)
│   │   └── 002_add_indexes.py       # Migración de índices
│   ├── env.py                  # Configuración de env
│   └── script.py.mako
├── alembic.ini                 # Configuración Alembic
├── tests/                      # Pruebas
│   ├── conftest.py            # Configuración pytest
│   ├── test_integration_citas.py    # Pruebas de integración (RF-05, RF-06)
│   └── test_repositories.py    # Pruebas unitarias repositorios
├── .github/
│   └── workflows/
│       └── ci-cd.yml          # Pipeline CI/CD GitHub Actions
├── requirements.txt           # Dependencias Python
└── .gitignore
```

## Modelos de Datos

### Entidades Principales (6)

1. **Usuario** - Base de todos los usuarios
   - id, nombre_usuario, contrasena, correo, rol, activo
   - Roles: paciente, médico, admin, recepcionista

2. **Paciente** - Información de pacientes
   - id, id_usuario, numero_documento, tipo_documento, eps, telefono, fecha_nacimiento

3. **Médico** - Información de médicos
   - id, id_usuario, id_especialidad, numero_licencia, colegio_profesional, disponible

4. **Especialidad** - Especialidades médicas
   - id, nombre, descripcion

5. **Cita** - Citas agendadas
   - id, id_paciente, id_medico, id_consultorio, fecha, hora, estado, motivo_consulta, notas

6. **Consultorio** - Espacios físicos para las citas
   - id, numero, piso, capacidad

## Migraciones con Alembic

### Versión 1: Schema Inicial
```bash
# Crear tablas principales
python -m alembic upgrade head
```

Crea:
- usuarios
- especialidades
- pacientes
- medicos
- consultorios
- citas

### Versión 2: Índices para Optimización
Agrega índices para:
- Búsquedas por nombre_usuario, correo
- Búsquedas por numero_documento
- Búsquedas por numero_licencia
- Búsquedas por estado y fecha de citas
- Índices compuestos para queries frecuentes

## Repositorios CRUD Optimizados

### PacienteRepository
```python
from repositories import PacienteRepository

# Crear
paciente = repo.crear(id_usuario=1, numero_documento="123", ...)

# Obtener por documento (con usuario cargado)
paciente = repo.obtener_por_documento("123")

# Obtener todos
pacientes = repo.obtener_todos()
```

### MedicoRepository
```python
from repositories import MedicoRepository

# Obtener solo disponibles (evita N+1)
medicos = repo.obtener_disponibles()

# Obtener por especialidad
medicos = repo.obtener_por_especialidad(especialidad_id)
```

### CitaRepository - Optimización N+1
```python
from repositories import CitaRepository

# Obtener cita con TODAS las relaciones en una sola query
cita = repo.obtener_por_id(1)
# Acceso sin queries adicionales:
cita.paciente.usuario.nombre_usuario
cita.medico.especialidad.nombre
cita.consultorio.numero

# Obtener citas de paciente optimizado
citas = repo.obtener_citas_paciente(paciente_id)  # Una query, no N+1
```

## Pruebas de Integración

### RF-05: Agendar Cita

```bash
pytest tests/test_integration_citas.py::TestAgendarCita -v
```

Pruebas:
- ✅ Crear cita exitosamente
- ✅ Validar que no se agenda con médico no disponible
- ✅ Evitar problema N+1 al obtener citas

### RF-06: Confirmar Cita

```bash
pytest tests/test_integration_citas.py::TestConfirmarCita -v
```

Pruebas:
- ✅ Confirmar cita (cambiar estado PENDIENTE → CONFIRMADA)
- ✅ Transiciones de estado completas
- ✅ Filtrar citas por estado

## Ejecutar Todas las Pruebas

```bash
# Con cobertura
pytest tests/ -v --cov=. --cov-report=html

# Ver reporte en navegador
open htmlcov/index.html
```

## Pipeline CI/CD

El archivo `.github/workflows/ci-cd.yml` ejecuta:

1. **Tests** - Python 3.9, 3.10, 3.11
   - Pruebas unitarias con pytest
   - Reporte de cobertura
   - Upload a Codecov

2. **Linting**
   - flake8 (código)
   - black (formato)
   - isort (imports)

3. **Validación Migraciones**
   - Upgrade y downgrade automático

Cada push a `main` o `develop` ejecuta el pipeline.

## Uso Básico

```python
from app import create_app, db
from models import Usuario, Paciente
from repositories import PacienteRepository
from sqlalchemy.orm import Session

# Crear app
app = create_app("development")

with app.app_context():
    # Crear usuario
    usuario = Usuario(
        nombre_usuario="juan",
        contrasena="hashed_pwd",
        correo="juan@example.com",
        rol="paciente"
    )
    db.session.add(usuario)
    db.session.commit()
    
    # Crear paciente con repositorio
    repo = PacienteRepository(db.session)
    paciente = repo.crear(
        id_usuario=usuario.id,
        numero_documento="1234567890",
        tipo_documento="CC",
        eps="Aura"
    )
    
    print(f"Paciente creado: {paciente.numero_documento}")
```

## Características Principales

✅ **SQLAlchemy 2.0 Moderno**
- Type hints completos
- Mapped columns
- Relaciones bien definidas

✅ **Evitar N+1**
- Uso de `joinedload()` en repositorios
- Queries optimizadas
- Una sola query para traer datos relacionados

✅ **Migraciones Profesionales**
- Alembic configurado
- 2 versiones de migración
- Upgrade/downgrade automático

✅ **Pruebas Robustas**
- SQLite en memoria
- Cobertura de código
- Pruebas de integración

✅ **CI/CD Completo**
- GitHub Actions
- Tests automáticos
- Linting
- Validación de migraciones

## Próximos Pasos

1. Implementar rutas Flask para CRUD
2. Agregar validaciones y manejo de errores
3. Implementar autenticación JWT
4. Agregar más especialidades y consultorios
5. Crear frontend con React/Vue

## Licencia

MIT

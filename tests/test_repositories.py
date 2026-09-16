"""
Pruebas unitarias de repositorios
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import Base
from models import Usuario, Paciente, Medico, Especialidad, Cita, Consultorio, RolEnum, EstadoCitaEnum
from repositories import PacienteRepository, MedicoRepository, CitaRepository


@pytest.fixture(scope="function")
def db_session():
    """Crea una sesión de base de datos en memoria para cada prueba"""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestPacienteRepository:
    """Pruebas del repositorio de Pacientes"""
    
    def test_crear_paciente(self, db_session):
        """Crear un nuevo paciente"""
        # Preparar usuario
        usuario = Usuario(
            nombre_usuario="paciente_test",
            contrasena="pass",
            correo="paciente@test.com",
            rol=RolEnum.PACIENTE
        )
        db_session.add(usuario)
        db_session.flush()
        
        # Crear paciente
        repo = PacienteRepository(db_session)
        paciente = repo.crear(
            id_usuario=usuario.id,
            numero_documento="1111111111",
            tipo_documento="CC",
            eps="Test EPS",
            telefono="3001111111"
        )
        
        assert paciente.id is not None
        assert paciente.numero_documento == "1111111111"
        assert paciente.eps == "Test EPS"
    
    def test_obtener_paciente_por_documento(self, db_session):
        """Obtener paciente por número de documento"""
        usuario = Usuario(
            nombre_usuario="paciente_doc",
            contrasena="pass",
            correo="doc@test.com",
            rol=RolEnum.PACIENTE
        )
        db_session.add(usuario)
        db_session.flush()
        
        repo = PacienteRepository(db_session)
        paciente_creado = repo.crear(
            id_usuario=usuario.id,
            numero_documento="2222222222",
            tipo_documento="CC",
            eps="Test EPS"
        )
        
        paciente_encontrado = repo.obtener_por_documento("2222222222")
        assert paciente_encontrado.id == paciente_creado.id
        assert paciente_encontrado.usuario.nombre_usuario == "paciente_doc"


class TestMedicoRepository:
    """Pruebas del repositorio de Médicos"""
    
    def test_crear_medico(self, db_session):
        """Crear un nuevo médico"""
        # Crear especialidad
        especialidad = Especialidad(nombre="Cardiología", descripcion="Corazón")
        db_session.add(especialidad)
        db_session.flush()
        
        # Crear usuario
        usuario = Usuario(
            nombre_usuario="medico_test",
            contrasena="pass",
            correo="medico@test.com",
            rol=RolEnum.MEDICO
        )
        db_session.add(usuario)
        db_session.flush()
        
        # Crear médico
        repo = MedicoRepository(db_session)
        medico = repo.crear(
            id_usuario=usuario.id,
            id_especialidad=especialidad.id,
            numero_licencia="MED123",
            disponible=True
        )
        
        assert medico.id is not None
        assert medico.numero_licencia == "MED123"
        assert medico.disponible == True
    
    def test_obtener_medicos_disponibles(self, db_session):
        """Obtener solo médicos disponibles"""
        especialidad = Especialidad(nombre="Pediatría")
        db_session.add(especialidad)
        db_session.flush()
        
        # Médico disponible
        usuario1 = Usuario(
            nombre_usuario="medico_disponible",
            contrasena="pass",
            correo="medico1@test.com",
            rol=RolEnum.MEDICO
        )
        db_session.add(usuario1)
        db_session.flush()
        
        # Médico no disponible
        usuario2 = Usuario(
            nombre_usuario="medico_no_disponible",
            contrasena="pass",
            correo="medico2@test.com",
            rol=RolEnum.MEDICO
        )
        db_session.add(usuario2)
        db_session.flush()
        
        repo = MedicoRepository(db_session)
        repo.crear(
            id_usuario=usuario1.id,
            id_especialidad=especialidad.id,
            numero_licencia="MED001",
            disponible=True
        )
        repo.crear(
            id_usuario=usuario2.id,
            id_especialidad=especialidad.id,
            numero_licencia="MED002",
            disponible=False
        )
        
        disponibles = repo.obtener_disponibles()
        assert len(disponibles) == 1
        assert disponibles[0].usuario.nombre_usuario == "medico_disponible"


class TestCitaRepository:
    """Pruebas del repositorio de Citas"""
    
    def test_crear_cita(self, db_session):
        """Crear una nueva cita"""
        # Setup
        especialidad = Especialidad(nombre="General")
        db_session.add(especialidad)
        db_session.flush()
        
        usuario_paciente = Usuario(
            nombre_usuario="pac_cita",
            contrasena="pass",
            correo="pac_cita@test.com",
            rol=RolEnum.PACIENTE
        )
        db_session.add(usuario_paciente)
        db_session.flush()
        
        paciente = Paciente(
            id_usuario=usuario_paciente.id,
            numero_documento="9999999999",
            tipo_documento="CC",
            eps="Test"
        )
        db_session.add(paciente)
        db_session.flush()
        
        usuario_medico = Usuario(
            nombre_usuario="med_cita",
            contrasena="pass",
            correo="med_cita@test.com",
            rol=RolEnum.MEDICO
        )
        db_session.add(usuario_medico)
        db_session.flush()
        
        medico = Medico(
            id_usuario=usuario_medico.id,
            id_especialidad=especialidad.id,
            numero_licencia="MED999"
        )
        db_session.add(medico)
        db_session.flush()
        
        consultorio = Consultorio(numero="101", piso=1)
        db_session.add(consultorio)
        db_session.flush()
        
        # Test
        repo = CitaRepository(db_session)
        fecha = (datetime.now() + timedelta(days=1)).isoformat()
        cita = repo.crear(
            id_paciente=paciente.id,
            id_medico=medico.id,
            id_consultorio=consultorio.id,
            fecha=fecha,
            hora="10:00",
            motivo_consulta="Consulta general"
        )
        
        assert cita.id is not None
        assert cita.estado == EstadoCitaEnum.PENDIENTE
        assert cita.motivo_consulta == "Consulta general"

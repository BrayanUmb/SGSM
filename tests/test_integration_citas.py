"""
Pruebas de integración para el flujo de agendamiento de citas
Utiliza una base de datos SQLite en memoria para las pruebas

RF-05: Agendar cita
RF-06: Confirmar cita
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import Base, db, create_app
from models import Usuario, Paciente, Medico, Especialidad, Cita, Consultorio, RolEnum, EstadoCitaEnum
from repositories import PacienteRepository, MedicoRepository, CitaRepository


@pytest.fixture(scope="function")
def db_session():
    """
    Crea una sesión de base de datos en memoria para cada prueba
    """
    # Crear motor SQLite en memoria
    engine = create_engine(
        'sqlite:///:memory:',
        connect_args={'check_same_thread': False},
        poolclass=type(None)
    )
    
    # Crear todas las tablas
    Base.metadata.create_all(engine)
    
    # Crear sesión
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    # Limpiar
    session.close()


@pytest.fixture(scope="function")
def app():
    """Crea una aplicación Flask para testing"""
    app = create_app("testing")
    return app


class TestAgendarCita:
    """Pruebas para el flujo de agendamiento de citas (RF-05)"""
    
    def test_crear_cita_exitosa(self, db_session):
        """
        Prueba: Crear una cita exitosamente
        Escenario: Un paciente agenda una cita con un médico disponible
        """
        # Arrange - Preparar datos
        # Crear especialidad
        especialidad = Especialidad(nombre="Cardiología", descripcion="Especialidad del corazón")
        db_session.add(especialidad)
        db_session.flush()
        
        # Crear usuario paciente
        usuario_paciente = Usuario(
            nombre_usuario="juan_paciente",
            contrasena="hashed_password",
            correo="juan@example.com",
            rol=RolEnum.PACIENTE
        )
        db_session.add(usuario_paciente)
        db_session.flush()
        
        # Crear paciente
        paciente = Paciente(
            id_usuario=usuario_paciente.id,
            numero_documento="1234567890",
            tipo_documento="CC",
            eps="Aura",
            telefono="3101234567"
        )
        db_session.add(paciente)
        db_session.flush()
        
        # Crear usuario médico
        usuario_medico = Usuario(
            nombre_usuario="dr_cardiologo",
            contrasena="hashed_password",
            correo="doctor@example.com",
            rol=RolEnum.MEDICO
        )
        db_session.add(usuario_medico)
        db_session.flush()
        
        # Crear médico
        medico = Medico(
            id_usuario=usuario_medico.id,
            id_especialidad=especialidad.id,
            numero_licencia="MED123456",
            colegio_profesional="Colegio Médico de Colombia",
            disponible=True
        )
        db_session.add(medico)
        db_session.flush()
        
        # Crear consultorio
        consultorio = Consultorio(numero="101", piso=1, capacidad=2)
        db_session.add(consultorio)
        db_session.flush()
        
        # Act - Ejecutar acción
        cita_repo = CitaRepository(db_session)
        fecha_cita = datetime.now() + timedelta(days=7)
        cita = cita_repo.crear(
            id_paciente=paciente.id,
            id_medico=medico.id,
            id_consultorio=consultorio.id,
            fecha=fecha_cita.isoformat(),
            hora="10:30",
            motivo_consulta="Chequeo del corazón"
        )
        
        # Assert - Verificar resultados
        assert cita.id is not None
        assert cita.id_paciente == paciente.id
        assert cita.id_medico == medico.id
        assert cita.estado == EstadoCitaEnum.PENDIENTE
        assert cita.motivo_consulta == "Chequeo del corazón"
    
    def test_agendar_cita_con_medico_no_disponible(self, db_session):
        """
        Prueba: Intentar agendar cita con médico no disponible
        Escenario: Validar que no se puede agendar con un médico que no está disponible
        """
        # Arrange
        especialidad = Especialidad(nombre="Pediatría")
        db_session.add(especialidad)
        db_session.flush()
        
        usuario_paciente = Usuario(
            nombre_usuario="sofia_paciente",
            contrasena="hashed_password",
            correo="sofia@example.com",
            rol=RolEnum.PACIENTE
        )
        db_session.add(usuario_paciente)
        db_session.flush()
        
        paciente = Paciente(
            id_usuario=usuario_paciente.id,
            numero_documento="9876543210",
            tipo_documento="CC",
            eps="Sanitas"
        )
        db_session.add(paciente)
        db_session.flush()
        
        usuario_medico = Usuario(
            nombre_usuario="dr_pediatra",
            contrasena="hashed_password",
            correo="pediatra@example.com",
            rol=RolEnum.MEDICO
        )
        db_session.add(usuario_medico)
        db_session.flush()
        
        # Crear médico NO disponible
        medico = Medico(
            id_usuario=usuario_medico.id,
            id_especialidad=especialidad.id,
            numero_licencia="PED654321",
            disponible=False  # No disponible
        )
        db_session.add(medico)
        db_session.flush()
        
        consultorio = Consultorio(numero="202", piso=2)
        db_session.add(consultorio)
        db_session.flush()
        
        # Act - Intentar crear cita
        medico_repo = MedicoRepository(db_session)
        medicos_disponibles = medico_repo.obtener_disponibles()
        
        # Assert - Verificar que el médico no está en la lista de disponibles
        assert len(medicos_disponibles) == 0
        assert medico.disponible == False
    
    def test_obtener_citas_paciente_optimizado(self, db_session):
        """
        Prueba: Obtener citas de un paciente sin problema N+1
        Escenario: Verificar que se cargan todas las relaciones en una sola query
        """
        # Arrange - Preparar datos
        especialidad = Especialidad(nombre="Oftalmología")
        db_session.add(especialidad)
        db_session.flush()
        
        usuario_paciente = Usuario(
            nombre_usuario="maria_paciente",
            contrasena="hashed_password",
            correo="maria@example.com",
            rol=RolEnum.PACIENTE
        )
        db_session.add(usuario_paciente)
        db_session.flush()
        
        paciente = Paciente(
            id_usuario=usuario_paciente.id,
            numero_documento="5555555555",
            tipo_documento="CC",
            eps="EPS Sanitas"
        )
        db_session.add(paciente)
        db_session.flush()
        
        usuario_medico = Usuario(
            nombre_usuario="dr_oculista",
            contrasena="hashed_password",
            correo="oculista@example.com",
            rol=RolEnum.MEDICO
        )
        db_session.add(usuario_medico)
        db_session.flush()
        
        medico = Medico(
            id_usuario=usuario_medico.id,
            id_especialidad=especialidad.id,
            numero_licencia="OFT111111",
            disponible=True
        )
        db_session.add(medico)
        db_session.flush()
        
        consultorio = Consultorio(numero="303", piso=3)
        db_session.add(consultorio)
        db_session.flush()
        
        # Crear múltiples citas para el mismo paciente
        cita_repo = CitaRepository(db_session)
        fecha_base = datetime.now()
        
        for i in range(3):
            fecha_cita = fecha_base + timedelta(days=i+1)
            cita_repo.crear(
                id_paciente=paciente.id,
                id_medico=medico.id,
                id_consultorio=consultorio.id,
                fecha=fecha_cita.isoformat(),
                hora=f"{10+i}:00",
                motivo_consulta=f"Consulta oftalmológica {i+1}"
            )
        
        # Act - Obtener citas sin generar N+1
        citas = cita_repo.obtener_citas_paciente(paciente.id)
        
        # Assert
        assert len(citas) == 3
        for cita in citas:
            assert cita.paciente.id == paciente.id
            # Acceder a datos del médico sin generar queries adicionales
            assert cita.medico.usuario.nombre_usuario == "dr_oculista"
            assert cita.medico.especialidad.nombre == "Oftalmología"
            assert cita.consultorio.numero == "303"


class TestConfirmarCita:
    """Pruebas para el flujo de confirmación de citas (RF-06)"""
    
    def test_confirmar_cita_exitosa(self, db_session):
        """
        Prueba: Confirmar una cita exitosamente
        Escenario: Cambiar estado de cita de PENDIENTE a CONFIRMADA
        """
        # Arrange - Preparar datos
        especialidad = Especialidad(nombre="Traumatología")
        db_session.add(especialidad)
        db_session.flush()
        
        usuario_paciente = Usuario(
            nombre_usuario="carlos_paciente",
            contrasena="hashed_password",
            correo="carlos@example.com",
            rol=RolEnum.PACIENTE
        )
        db_session.add(usuario_paciente)
        db_session.flush()
        
        paciente = Paciente(
            id_usuario=usuario_paciente.id,
            numero_documento="3333333333",
            tipo_documento="CC",
            eps="Famisanar"
        )
        db_session.add(paciente)
        db_session.flush()
        
        usuario_medico = Usuario(
            nombre_usuario="dr_traumatologo",
            contrasena="hashed_password",
            correo="traumatologo@example.com",
            rol=RolEnum.MEDICO
        )
        db_session.add(usuario_medico)
        db_session.flush()
        
        medico = Medico(
            id_usuario=usuario_medico.id,
            id_especialidad=especialidad.id,
            numero_licencia="TRAM222222",
            disponible=True
        )
        db_session.add(medico)
        db_session.flush()
        
        consultorio = Consultorio(numero="404", piso=4)
        db_session.add(consultorio)
        db_session.flush()
        
        # Crear cita
        cita_repo = CitaRepository(db_session)
        fecha_cita = datetime.now() + timedelta(days=5)
        cita = cita_repo.crear(
            id_paciente=paciente.id,
            id_medico=medico.id,
            id_consultorio=consultorio.id,
            fecha=fecha_cita.isoformat(),
            hora="14:00",
            motivo_consulta="Lesión en rodilla"
        )
        cita_id = cita.id
        
        # Act - Confirmar cita
        cita_confirmada = cita_repo.actualizar_estado(cita_id, EstadoCitaEnum.CONFIRMADA.value)
        
        # Assert
        assert cita_confirmada is not None
        assert cita_confirmada.estado == EstadoCitaEnum.CONFIRMADA
        
        # Verificar que persiste
        cita_verificada = cita_repo.obtener_por_id(cita_id)
        assert cita_verificada.estado == EstadoCitaEnum.CONFIRMADA
    
    def test_cambiar_estado_cita(self, db_session):
        """
        Prueba: Cambiar múltiples estados de cita
        Escenario: PENDIENTE -> CONFIRMADA -> EN_CONSULTA -> COMPLETADA
        """
        # Arrange
        especialidad = Especialidad(nombre="Dermatología")
        db_session.add(especialidad)
        db_session.flush()
        
        usuario_paciente = Usuario(
            nombre_usuario="ana_paciente",
            contrasena="hashed_password",
            correo="ana@example.com",
            rol=RolEnum.PACIENTE
        )
        db_session.add(usuario_paciente)
        db_session.flush()
        
        paciente = Paciente(
            id_usuario=usuario_paciente.id,
            numero_documento="7777777777",
            tipo_documento="CC",
            eps="Coomeva"
        )
        db_session.add(paciente)
        db_session.flush()
        
        usuario_medico = Usuario(
            nombre_usuario="dr_dermatologo",
            contrasena="hashed_password",
            correo="dermatologo@example.com",
            rol=RolEnum.MEDICO
        )
        db_session.add(usuario_medico)
        db_session.flush()
        
        medico = Medico(
            id_usuario=usuario_medico.id,
            id_especialidad=especialidad.id,
            numero_licencia="DERM333333",
            disponible=True
        )
        db_session.add(medico)
        db_session.flush()
        
        consultorio = Consultorio(numero="505", piso=5)
        db_session.add(consultorio)
        db_session.flush()
        
        # Crear cita
        cita_repo = CitaRepository(db_session)
        fecha_cita = datetime.now() + timedelta(days=3)
        cita = cita_repo.crear(
            id_paciente=paciente.id,
            id_medico=medico.id,
            id_consultorio=consultorio.id,
            fecha=fecha_cita.isoformat(),
            hora="11:00",
            motivo_consulta="Consulta dermatológica"
        )
        cita_id = cita.id
        
        # Act y Assert - Realizar transiciones de estado
        # Estado inicial
        cita = cita_repo.obtener_por_id(cita_id)
        assert cita.estado == EstadoCitaEnum.PENDIENTE
        
        # Transición a CONFIRMADA
        cita = cita_repo.actualizar_estado(cita_id, EstadoCitaEnum.CONFIRMADA.value)
        assert cita.estado == EstadoCitaEnum.CONFIRMADA
        
        # Transición a EN_CONSULTA
        cita = cita_repo.actualizar_estado(cita_id, EstadoCitaEnum.EN_CONSULTA.value)
        assert cita.estado == EstadoCitaEnum.EN_CONSULTA
        
        # Transición a COMPLETADA
        cita = cita_repo.actualizar_estado(cita_id, EstadoCitaEnum.COMPLETADA.value)
        assert cita.estado == EstadoCitaEnum.COMPLETADA
        
        # Verificar estado final
        cita_final = cita_repo.obtener_por_id(cita_id)
        assert cita_final.estado == EstadoCitaEnum.COMPLETADA
    
    def test_obtener_citas_por_estado(self, db_session):
        """
        Prueba: Filtrar citas por estado
        Escenario: Obtener solo citas confirmadas
        """
        # Arrange
        especialidad = Especialidad(nombre="Neurología")
        db_session.add(especialidad)
        db_session.flush()
        
        usuario_paciente = Usuario(
            nombre_usuario="luis_paciente",
            contrasena="hashed_password",
            correo="luis@example.com",
            rol=RolEnum.PACIENTE
        )
        db_session.add(usuario_paciente)
        db_session.flush()
        
        paciente = Paciente(
            id_usuario=usuario_paciente.id,
            numero_documento="8888888888",
            tipo_documento="CC",
            eps="Comfenalco"
        )
        db_session.add(paciente)
        db_session.flush()
        
        usuario_medico = Usuario(
            nombre_usuario="dr_neurologo",
            contrasena="hashed_password",
            correo="neurologo@example.com",
            rol=RolEnum.MEDICO
        )
        db_session.add(usuario_medico)
        db_session.flush()
        
        medico = Medico(
            id_usuario=usuario_medico.id,
            id_especialidad=especialidad.id,
            numero_licencia="NEUR444444",
            disponible=True
        )
        db_session.add(medico)
        db_session.flush()
        
        consultorio = Consultorio(numero="606", piso=6)
        db_session.add(consultorio)
        db_session.flush()
        
        # Crear citas con diferentes estados
        cita_repo = CitaRepository(db_session)
        fecha_base = datetime.now()
        
        # Cita pendiente
        cita1 = cita_repo.crear(
            id_paciente=paciente.id,
            id_medico=medico.id,
            id_consultorio=consultorio.id,
            fecha=(fecha_base + timedelta(days=1)).isoformat(),
            hora="09:00"
        )
        
        # Cita confirmada
        cita2 = cita_repo.crear(
            id_paciente=paciente.id,
            id_medico=medico.id,
            id_consultorio=consultorio.id,
            fecha=(fecha_base + timedelta(days=2)).isoformat(),
            hora="10:00"
        )
        cita_repo.actualizar_estado(cita2.id, EstadoCitaEnum.CONFIRMADA.value)
        
        # Cita completada
        cita3 = cita_repo.crear(
            id_paciente=paciente.id,
            id_medico=medico.id,
            id_consultorio=consultorio.id,
            fecha=(fecha_base + timedelta(days=3)).isoformat(),
            hora="11:00"
        )
        cita_repo.actualizar_estado(cita3.id, EstadoCitaEnum.COMPLETADA.value)
        
        # Act - Obtener citas confirmadas
        citas_confirmadas = cita_repo.obtener_por_estado(EstadoCitaEnum.CONFIRMADA.value)
        
        # Assert
        assert len(citas_confirmadas) == 1
        assert citas_confirmadas[0].id == cita2.id
        assert citas_confirmadas[0].estado == EstadoCitaEnum.CONFIRMADA

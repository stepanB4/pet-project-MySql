# database.py
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Date, Boolean, Enum, ForeignKey, \
    TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import enum

# Строка подключения к MySQL
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:Avaxui123@localhost/booking_system"

# Создаем движок
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300
)

# Создаем сессию
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для моделей
Base = declarative_base()


# Enum для корпусов
class BuildingEnum(str, enum.Enum):
    ГУК = "ГУК"
    УЛК = "УЛК"
    ИБМ = "ИБМ"
    МТ = "МТ"
    СМ = "СМ"
    Э = "Э"
    ХимЛаб = "ХимЛаб"
    #Тестовый корпус для проверки импорта csv
    TT = "TT"


# Enum для статусов бронирования
class BookingStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"


# Модель таблицы аудиторий
class Classroom(Base):
    __tablename__ = "classrooms"

    id = Column(Integer, primary_key=True, index=True)
    room_number = Column(String(20), nullable=False)
    building = Column(Enum(BuildingEnum), nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    # Связь со слотами
    slots = relationship("Slot", back_populates="classroom")


# Модель таблицы слотов
class Slot(Base):
    __tablename__ = "slots"

    id = Column(Integer, primary_key=True, index=True)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"), nullable=False)
    date = Column(Date, nullable=False)
    lesson_number = Column(Integer, nullable=False)  # 1-8
    is_booked = Column(Boolean, default=False)
    teacher_name = Column(String(255), nullable=True)

    # Дополнительные поля для бронирования
    group_name = Column(String(100), nullable=True)
    event_type = Column(String(255), nullable=True)
    previous_classroom = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True)
    status = Column(Enum(BookingStatus), default=BookingStatus.pending)

    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    classroom = relationship("Classroom", back_populates="slots")


# Модель таблицы администраторов
class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


# Функция для получения сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Создание таблиц при запуске
def create_tables():
    Base.metadata.create_all(bind=engine)


# Вспомогательные функции
def get_lesson_time(lesson_number: int) -> str:
    lessons = {
        1: "8:30-10:05",
        2: "10:15-11:50",
        3: "12:00-13:35",
        4: "13:50-15:25",
        5: "15:40-17:15",
        6: "17:25-19:00",
        7: "19:10-20:45",
        8: "20:55-22:30"
    }
    return lessons.get(lesson_number, "Неизвестно")
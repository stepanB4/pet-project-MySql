# from flask import Flask, render_template
#
# app = Flask(__name__)
#
# @app.route("/")
# def home():
#     return render_template("index.html")  # Подключаем HTML-шаблон
#
# if __name__ == "__main__":
#     app.run(debug=True)
#
# # Страница "О нас"
# @app.route("/about")
# def about():
#     return "<h1>О нас</h1><p>Мы изучаем Flask!</p>"
#
# # Страница "Контакты"
# @app.route("/contact")
# def contact():
#     return "<h1>Контакты</h1><p>Свяжитесь с нами: email@example.com</p>"
#
# if __name__ == "__main__":
#     app.run(debug=True)
# from fastapi import FastAPI, Depends, HTTPException, Request
# from fastapi.responses import HTMLResponse
# from fastapi.staticfiles import StaticFiles
# from fastapi.templating import Jinja2Templates
# from sqlalchemy import create_engine, Column, Integer, String, Date, Text
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import sessionmaker, Session
# from pydantic import BaseModel
# from datetime import date, datetime, timedelta
# from typing import List, Optional
# import os
#
# # Database setup
# SQLALCHEMY_DATABASE_URL = "sqlite:///./calendar.db"
# engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base = declarative_base()
#
#
# # Database models
# class CalendarEvent(Base):
#     __tablename__ = "calendar_events"
#
#     id = Column(Integer, primary_key=True, index=True)
#     title = Column(String(200), nullable=False)
#     description = Column(Text, nullable=True)
#     event_date = Column(Date, nullable=False)
#     event_type = Column(String(50), default="normal")
#     color = Column(String(7), default="#3b82f6")
#     created_at = Column(Date, default=date.today)
#
#
# # Pydantic models
# class EventCreate(BaseModel):
#     title: str
#     description: Optional[str] = None
#     event_date: date
#     event_type: str = "normal"
#     color: str = "#3b82f6"
#
#
# class EventResponse(BaseModel):
#     id: int
#     title: str
#     description: Optional[str]
#     event_date: date
#     event_type: str
#     color: str
#
#     class Config:
#         orm_mode = True
#
#
# # Create tables
# Base.metadata.create_all(bind=engine)
#
# # FastAPI app
# app = FastAPI(title="Calendar API")
#
# # Templates
# templates = Jinja2Templates(directory="templates")
#
#
# # Dependency
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
#
#
# # Database functions
# def get_events_by_month(db: Session, year: int, month: int):
#     start_date = date(year, month, 1)
#     if month == 12:
#         end_date = date(year + 1, 1, 1)
#     else:
#         end_date = date(year, month + 1, 1)
#
#     return db.query(CalendarEvent).filter(
#         CalendarEvent.event_date >= start_date,
#         CalendarEvent.event_date < end_date
#     ).all()
#
#
# def create_event(db: Session, event: EventCreate):
#     db_event = CalendarEvent(
#         title=event.title,
#         description=event.description,
#         event_date=event.event_date,
#         event_type=event.event_type,
#         color=event.color
#     )
#     db.add(db_event)
#     db.commit()
#     db.refresh(db_event)
#     return db_event
#
#
# def delete_event(db: Session, event_id: int):
#     db_event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()
#     if db_event:
#         db.delete(db_event)
#         db.commit()
#     return db_event
#
#
# # Routes
# @app.get("/", response_class=HTMLResponse)
# async def read_calendar(request: Request, db: Session = Depends(get_db)):
#     today = date.today()
#     events = get_events_by_month(db, today.year, today.month)
#
#     # Format events for template
#     events_dict = {}
#     for event in events:
#         date_key = event.event_date.isoformat()
#         if date_key not in events_dict:
#             events_dict[date_key] = []
#         events_dict[date_key].append({
#             'id': event.id,
#             'title': event.title,
#             'description': event.description,
#             'type': event.event_type,
#             'color': event.color
#         })
#
#     return templates.TemplateResponse("calendar.html", {
#         "request": request,
#         "current_year": today.year,
#         "current_month": today.month,
#         "events": events_dict
#     })
#
#
# @app.get("/api/events/{year}/{month}")
# async def get_events(year: int, month: int, db: Session = Depends(get_db)):
#     events = get_events_by_month(db, year, month)
#     return [EventResponse.from_orm(event) for event in events]
#
#
# @app.post("/api/events/", response_model=EventResponse)
# async def create_new_event(event: EventCreate, db: Session = Depends(get_db)):
#     return create_event(db, event)
#
#
# @app.delete("/api/events/{event_id}")
# async def delete_event_by_id(event_id: int, db: Session = Depends(get_db)):
#     event = delete_event(db, event_id)
#     if not event:
#         raise HTTPException(status_code=404, detail="Event not found")
#     return {"message": "Event deleted successfully"}
#
#
# @app.get("/api/events/date/{event_date}")
# async def get_events_by_date(event_date: date, db: Session = Depends(get_db)):
#     events = db.query(CalendarEvent).filter(CalendarEvent.event_date == event_date).all()
#     return [EventResponse.from_orm(event) for event in events]
#
#
# if __name__ == "__main__":
#     import uvicorn
#
#     uvicorn.run(app, host="0.0.0.0", port=8000)
# from fastapi import FastAPI, HTTPException, Request
# from fastapi.responses import HTMLResponse
# from fastapi.templating import Jinja2Templates
# from pydantic import BaseModel, ConfigDict
# from datetime import date, datetime, timedelta
# from typing import List, Optional
# import random
#
# # FastAPI app
# app = FastAPI(title="Calendar API")
#
# # Templates
# templates = Jinja2Templates(directory="templates")
#
#
# # In-memory storage (замените на БД в будущем)
# class EventStorage:
#     def __init__(self):
#         self.events = []
#         self.next_id = 1
#         self._initialize_sample_data()
#
#     def _initialize_sample_data(self):
#         """Инициализация демо-данными"""
#         sample_events = [
#             {
#                 "title": "Встреча с командой",
#                 "description": "Еженедельная планерка",
#                 "event_date": date.today().replace(day=random.randint(1, 28)),
#                 "event_type": "meeting",
#                 "color": "#10b981"
#             },
#             {
#                 "title": "День рождения",
#                 "description": "День рождения коллеги",
#                 "event_date": date.today().replace(day=random.randint(1, 28)),
#                 "event_type": "personal",
#                 "color": "#8b5cf6"
#             },
#             {
#                 "title": "Дедлайн проекта",
#                 "description": "Сдача финальной версии",
#                 "event_date": date.today().replace(day=random.randint(1, 28)),
#                 "event_type": "important",
#                 "color": "#ef4444"
#             },
#             {
#                 "title": "Врач",
#                 "description": "Регулярный осмотр",
#                 "event_date": date.today().replace(day=random.randint(1, 28)),
#                 "event_type": "personal",
#                 "color": "#f59e0b"
#             },
#             {
#                 "title": "Презентация",
#                 "description": "Презентация для клиента",
#                 "event_date": date.today().replace(day=random.randint(1, 28)),
#                 "event_type": "meeting",
#                 "color": "#3b82f6"
#             }
#         ]
#
#         for event_data in sample_events:
#             self.create_event(event_data)
#
#     def get_events_by_month(self, year: int, month: int):
#         """Получить события за месяц"""
#         start_date = date(year, month, 1)
#         if month == 12:
#             end_date = date(year + 1, 1, 1)
#         else:
#             end_date = date(year, month + 1, 1)
#
#         return [
#             event for event in self.events
#             if start_date <= event["event_date"] < end_date
#         ]
#
#     def create_event(self, event_data: dict):
#         """Создать событие"""
#         event = {
#             "id": self.next_id,
#             "title": event_data["title"],
#             "description": event_data.get("description"),
#             "event_date": event_data["event_date"],
#             "event_type": event_data.get("event_type", "normal"),
#             "color": event_data.get("color", "#3b82f6")
#         }
#         self.events.append(event)
#         self.next_id += 1
#         return event
#
#     def delete_event(self, event_id: int):
#         """Удалить событие"""
#         for i, event in enumerate(self.events):
#             if event["id"] == event_id:
#                 return self.events.pop(i)
#         return None
#
#     def get_events_by_date(self, event_date: date):
#         """Получить события на конкретную дату"""
#         return [event for event in self.events if event["event_date"] == event_date]
#
#
# # Инициализация хранилища
# event_storage = EventStorage()
#
#
# # Pydantic models (для будущей миграции на БД)
# class EventCreate(BaseModel):
#     title: str
#     description: Optional[str] = None
#     event_date: date
#     event_type: str = "normal"
#     color: str = "#3b82f6"
#
#
# class EventResponse(BaseModel):
#     model_config = ConfigDict(from_attributes=True)
#
#     id: int
#     title: str
#     description: Optional[str]
#     event_date: date
#     event_type: str
#     color: str
#
#
# # Database functions interface (для будущей замены на реальную БД)
# def get_events_by_month(year: int, month: int):
#     return event_storage.get_events_by_month(year, month)
#
#
# def create_event(event: EventCreate):
#     return event_storage.create_event(event.model_dump())
#
#
# def delete_event(event_id: int):
#     return event_storage.delete_event(event_id)
#
#
# def get_events_by_date(event_date: date):
#     return event_storage.get_events_by_date(event_date)
#
#
# # Routes
# @app.get("/", response_class=HTMLResponse)
# async def read_calendar(request: Request):
#     today = date.today()
#     events = get_events_by_month(today.year, today.month)
#
#     # Format events for template
#     events_dict = {}
#     for event in events:
#         date_key = event["event_date"].isoformat()
#         if date_key not in events_dict:
#             events_dict[date_key] = []
#         events_dict[date_key].append({
#             'id': event["id"],
#             'title': event["title"],
#             'description': event["description"],
#             'type': event["event_type"],
#             'color': event["color"]
#         })
#
#     return templates.TemplateResponse("calendar.html", {
#         "request": request,
#         "current_year": today.year,
#         "current_month": today.month,
#         "events": events_dict
#     })
#
#
# @app.get("/api/events/{year}/{month}")
# async def get_events(year: int, month: int):
#     events = get_events_by_month(year, month)
#     return [EventResponse(**event) for event in events]
#
#
# @app.post("/api/events/", response_model=EventResponse)
# async def create_new_event(event: EventCreate):
#     created_event = create_event(event)
#     return EventResponse(**created_event)
#
#
# @app.delete("/api/events/{event_id}")
# async def delete_event_by_id(event_id: int):
#     event = delete_event(event_id)
#     if not event:
#         raise HTTPException(status_code=404, detail="Event not found")
#     return {"message": "Event deleted successfully"}
#
#
# @app.get("/api/events/date/{event_date}")
# async def get_events_by_date(event_date: date):
#     events = get_events_by_date(event_date)
#     return [EventResponse(**event) for event in events]
#
#
# # Health check
# @app.get("/health")
# async def health_check():
#     return {
#         "status": "healthy",
#         "events_count": len(event_storage.events),
#         "storage_type": "in_memory"
#     }
#
#
# if __name__ == "__main__":
#     import uvicorn
#
#     uvicorn.run(app, host="0.0.0.0", port=8000)
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict
import csv
import io
import calendar
import json

app = FastAPI(title="Booking System")
templates = Jinja2Templates(directory="templates")


# Кастомный JSON encoder для обработки объектов date
class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, date):
            return obj.isoformat()
        return super().default(obj)


# Хранилище данных (в памяти)
class DataStorage:
    def __init__(self):
        self.slots = []
        self.bookings = []
        self.admins = {"admin": "admin123"}
        self.next_slot_id = 1
        self.next_booking_id = 1
        self._initialize_sample_data()

    def _initialize_sample_data(self):
        """Демо-данные для тестирования"""
        today = date.today()

        # Создаем слоты на текущий месяц
        for day in range(1, 29):
            weekday = date(today.year, today.month, day).weekday()
            if weekday < 5:  # Понедельник-пятница
                for lesson in [1, 3, 5]:  # 1, 3, 5 пары
                    slot_data = {
                        "date": date(today.year, today.month, day),
                        "lesson_number": lesson,
                        "classroom": f"10{lesson}",
                        "building": "ГЗ",
                        "is_available": True
                    }
                    self.create_slot(slot_data)

        # Добавим немного слотов на следующий месяц для демонстрации
        next_month = today.month + 1 if today.month < 12 else 1
        next_year = today.year if today.month < 12 else today.year + 1

        for day in [1, 2, 3, 4, 5]:
            slot_data = {
                "date": date(next_year, next_month, day),
                "lesson_number": 2,
                "classroom": "201",
                "building": "УЛК",
                "is_available": True
            }
            self.create_slot(slot_data)

    def create_slot(self, slot_data: dict):
        slot = {
            "id": self.next_slot_id,
            "date": slot_data["date"],
            "lesson_number": slot_data["lesson_number"],
            "classroom": slot_data["classroom"],
            "building": slot_data["building"],
            "is_available": slot_data.get("is_available", True)
        }
        self.slots.append(slot)
        self.next_slot_id += 1
        return slot

    def get_available_slots_by_date(self, target_date: date):
        return [slot for slot in self.slots
                if slot["date"] == target_date and slot["is_available"]]

    def get_available_slots_by_week(self, start_date: date):
        end_date = start_date + timedelta(days=6)
        return [slot for slot in self.slots
                if start_date <= slot["date"] <= end_date and slot["is_available"]]

    def get_available_slots_by_month(self, year: int, month: int):
        """Получить все доступные слоты за месяц"""
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        slots = [slot for slot in self.slots
                 if start_date <= slot["date"] <= end_date and slot["is_available"]]

        # Группируем по дням для удобства
        grouped_slots = {}
        for slot in slots:
            date_str = slot["date"].isoformat()
            if date_str not in grouped_slots:
                grouped_slots[date_str] = 0
            grouped_slots[date_str] += 1

        return grouped_slots

    def create_booking(self, booking_data: dict):
        booking = {
            "id": self.next_booking_id,
            "slot_id": booking_data["slot_id"],
            "full_name": booking_data["full_name"],
            "group": booking_data["group"],
            "event_type": booking_data["event_type"],
            "previous_classroom": booking_data.get("previous_classroom"),
            "email": booking_data["email"],
            "status": "pending",
            "created_at": datetime.now()
        }

        # Помечаем слот как занятый
        slot = self.get_slot_by_id(booking_data["slot_id"])
        if slot:
            slot["is_available"] = False

        self.bookings.append(booking)
        self.next_booking_id += 1
        return booking

    def get_slot_by_id(self, slot_id: int):
        return next((slot for slot in self.slots if slot["id"] == slot_id), None)

    def confirm_booking(self, booking_id: int):
        booking = next((b for b in self.bookings if b["id"] == booking_id), None)
        if booking:
            booking["status"] = "confirmed"
            # Здесь должна быть отправка email
            print(f"Отправка email на {booking['email']}: Бронирование подтверждено")
            return booking
        return None

    def confirm_all_bookings(self):
        for booking in self.bookings:
            if booking["status"] == "pending":
                booking["status"] = "confirmed"
                print(f"Отправка email на {booking['email']}: Бронирование подтверждено")
        return True

    def delete_slot(self, slot_id: int):
        slot = self.get_slot_by_id(slot_id)
        if slot:
            # Проверяем, нет ли активных бронирований
            active_booking = next((b for b in self.bookings if b["slot_id"] == slot_id), None)
            if not active_booking:
                self.slots.remove(slot)
                return True
        return False


# Инициализация хранилища
storage = DataStorage()


# Модели Pydantic
class SlotCreate(BaseModel):
    date: date
    lesson_number: int
    classroom: str
    building: str


class BookingCreate(BaseModel):
    slot_id: int
    full_name: str
    group: str
    event_type: str
    previous_classroom: Optional[str] = None
    email: EmailStr


class AdminLogin(BaseModel):
    username: str
    password: str


# Вспомогательные функции
def get_lesson_time(lesson_number: int) -> str:
    """Возвращает время пары по номеру"""
    lessons = {
        1: "8:30-10:05",
        2: "10:15-11:50",
        3: "12:00-13:35",
        4: "13:50-15:25",
        5: "15:40-17:15",
        6: "17:25-19:00",
        7: "19:10-20:45"
    }
    return lessons.get(lesson_number, "Неизвестно")


def get_month_calendar(year: int, month: int):
    """Генерирует календарь на месяц"""
    cal = calendar.Calendar(firstweekday=0)  # Понедельник первый день недели
    month_days = cal.monthdayscalendar(year, month)

    # Преобразуем в удобный формат
    calendar_data = []
    for week in month_days:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append(None)  # Пустой день (из другого месяца)
            else:
                day_date = date(year, month, day)
                week_data.append({
                    "day": day,
                    "date": day_date.isoformat(),  # Используем строку вместо объекта date
                    "is_today": day_date == date.today(),
                    "is_past": day_date < date.today(),
                    "has_slots": False
                })
        calendar_data.append(week_data)

    return calendar_data


def get_week_dates(start_date: date):
    """Возвращает даты недели начиная с указанной даты"""
    return [start_date + timedelta(days=i) for i in range(7)]


# Вспомогательная функция для преобразования данных календаря в JSON-совместимый формат
def prepare_calendar_for_json(calendar_data):
    """Преобразует календарь в формат, который можно сериализовать в JSON"""
    prepared_calendar = []
    for week in calendar_data:
        prepared_week = []
        for day_data in week:
            if day_data:
                prepared_day = {
                    "day": day_data["day"],
                    "date": day_data["date"],  # Уже строка
                    "is_today": day_data["is_today"],
                    "is_past": day_data["is_past"],
                    "has_slots": day_data.get("has_slots", False),
                    "slots_count": day_data.get("slots_count", 0)
                }
                prepared_week.append(prepared_day)
            else:
                prepared_week.append(None)
        prepared_calendar.append(prepared_week)
    return prepared_calendar


# Роуты для преподавателя
@app.get("/", response_class=HTMLResponse)
async def teacher_calendar(request: Request):
    """Главная страница для преподавателя - календарь"""
    today = date.today()
    month_calendar = get_month_calendar(today.year, today.month)

    # Получаем количество слотов по дням
    month_slots = storage.get_available_slots_by_month(today.year, today.month)

    # Обновляем календарь с информацией о слотах
    for week in month_calendar:
        for day_data in week:
            if day_data and day_data["date"] in month_slots:
                day_data["has_slots"] = True
                day_data["slots_count"] = month_slots[day_data["date"]]

    # Подготавливаем календарь для передачи в шаблон
    prepared_calendar = prepare_calendar_for_json(month_calendar)

    return templates.TemplateResponse("teacher_calendar.html", {
        "request": request,
        "today": today.isoformat(),  # Используем строку
        "current_year": today.year,
        "current_month": today.month,
        "month_name": today.strftime("%B"),
        "calendar": prepared_calendar  # Уже подготовленный для JSON
    })


@app.get("/api/calendar/{year}/{month}")
async def get_calendar(year: int, month: int):
    """Получить календарь на месяц с информацией о слотах"""
    month_calendar = get_month_calendar(year, month)
    month_slots = storage.get_available_slots_by_month(year, month)

    # Обновляем календарь с информацией о слотах
    for week in month_calendar:
        for day_data in week:
            if day_data and day_data["date"] in month_slots:
                day_data["has_slots"] = True
                day_data["slots_count"] = month_slots[day_data["date"]]

    prepared_calendar = prepare_calendar_for_json(month_calendar)

    return {
        "calendar": prepared_calendar,
        "year": year,
        "month": month,
        "month_name": date(year, month, 1).strftime("%B")
    }


@app.get("/api/slots/month/{year}/{month}")
async def get_month_slots_summary(year: int, month: int):
    """Получить сводку по слотам за месяц"""
    slots = storage.get_available_slots_by_month(year, month)

    # Подсчитываем общее количество слотов и дней со слотами
    total_slots = sum(slots.values())
    days_with_slots = len(slots)

    return {
        "total_slots": total_slots,
        "days_with_slots": days_with_slots,
        "slots_by_day": slots
    }


@app.get("/api/slots/date/{slot_date}")
async def get_slots_by_date(slot_date: date):
    """Получить слоты на конкретную дату"""
    slots = storage.get_available_slots_by_date(slot_date)
    result = []
    for slot in slots:
        result.append({
            "id": slot["id"],
            "date": slot["date"].isoformat(),  # Преобразуем в строку
            "lesson_number": slot["lesson_number"],
            "classroom": slot["classroom"],
            "building": slot["building"],
            "lesson_time": get_lesson_time(slot["lesson_number"])
        })
    return result


@app.get("/api/slots/week/{start_date}")
async def get_slots_by_week(start_date: date):
    """Получить слоты на неделю"""
    slots = storage.get_available_slots_by_week(start_date)

    # Группируем по дням
    week_slots = {}
    for i in range(7):
        day_date = start_date + timedelta(days=i)
        day_slots = [slot for slot in slots if slot["date"] == day_date]
        week_slots[day_date.isoformat()] = [
            {
                "id": slot["id"],
                "date": slot["date"].isoformat(),
                "lesson_number": slot["lesson_number"],
                "classroom": slot["classroom"],
                "building": slot["building"],
                "lesson_time": get_lesson_time(slot["lesson_number"]),
                "date_display": day_date.strftime("%d.%m.%Y")
            }
            for slot in day_slots
        ]

    return {
        "start_date": start_date.isoformat(),
        "end_date": (start_date + timedelta(days=6)).isoformat(),
        "slots": week_slots
    }


@app.post("/api/bookings/")
async def create_booking(booking: BookingCreate):
    """Создать бронирование"""
    slot = storage.get_slot_by_id(booking.slot_id)
    if not slot or not slot["is_available"]:
        raise HTTPException(status_code=400, detail="Слот недоступен")

    created_booking = storage.create_booking(booking.dict())
    return {"message": "Бронирование создано", "booking_id": created_booking["id"]}


# Роуты для администратора
@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Страница входа для администратора"""
    return templates.TemplateResponse("admin_login.html", {"request": request})


@app.post("/admin/login")
async def admin_login(login_data: AdminLogin):
    """Аутентификация администратора"""
    if (login_data.username in storage.admins and
            storage.admins[login_data.username] == login_data.password):
        return {"message": "Успешный вход", "redirect": "/admin/dashboard"}
    raise HTTPException(status_code=401, detail="Неверные учетные данные")


@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Панель управления администратора"""
    pending_bookings = [b for b in storage.bookings if b["status"] == "pending"]
    confirmed_bookings = [b for b in storage.bookings if b["status"] == "confirmed"]

    # Добавляем информацию о слотах к бронированиям
    for booking in pending_bookings + confirmed_bookings:
        slot = storage.get_slot_by_id(booking["slot_id"])
        if slot:
            booking["slot_info"] = {
                "date": slot["date"].isoformat(),
                "lesson_time": get_lesson_time(slot["lesson_number"]),
                "classroom": slot["classroom"],
                "building": slot["building"]
            }

    # Подготавливаем слоты для отображения
    prepared_slots = []
    for slot in storage.slots:
        prepared_slots.append({
            "id": slot["id"],
            "date": slot["date"].isoformat(),
            "lesson_number": slot["lesson_number"],
            "classroom": slot["classroom"],
            "building": slot["building"],
            "is_available": slot["is_available"]
        })

    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "pending_bookings": pending_bookings,
        "confirmed_bookings": confirmed_bookings,
        "slots": prepared_slots
    })


@app.post("/admin/slots/")
async def create_slot(slot: SlotCreate):
    """Создать новый слот"""
    slot_dict = slot.dict()
    slot_dict["is_available"] = True
    created_slot = storage.create_slot(slot_dict)
    return {"message": "Слот создан", "slot_id": created_slot["id"]}


@app.post("/admin/slots/upload-csv")
async def upload_slots_csv(file: bytes = Form(...)):
    """Загрузить слоты из CSV"""
    try:
        content = file.decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))

        created_count = 0
        for row in reader:
            slot_data = {
                "date": datetime.strptime(row['date'], '%Y-%m-%d').date(),
                "lesson_number": int(row['lesson_number']),
                "classroom": row['classroom'],
                "building": row['building'],
                                "is_available": True
            }
            storage.create_slot(slot_data)
            created_count += 1

        return {"message": f"Успешно загружено {created_count} слотов"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка обработки CSV: {str(e)}")


@app.post("/admin/bookings/{booking_id}/confirm")
async def confirm_booking(booking_id: int):
    """Подтвердить бронирование"""
    booking = storage.confirm_booking(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Бронирование не найдено")
    return {"message": "Бронирование подтверждено"}


@app.post("/admin/bookings/confirm-all")
async def confirm_all_bookings():
    """Подтвердить все бронирования"""
    storage.confirm_all_bookings()
    return {"message": "Все бронирования подтверждены"}


@app.get("/admin/bookings/export-csv")
async def export_bookings_csv():
    """Экспорт подтвержденных бронирований в CSV"""
    confirmed_bookings = [b for b in storage.bookings if b["status"] == "confirmed"]

    output = io.StringIO()
    fieldnames = ['ID', 'ФИО', 'Группа', 'Мероприятие', 'Предыдущая аудитория',
                  'Email', 'Дата', 'Время', 'Аудитория', 'Корпус', 'Статус', 'Дата создания']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for booking in confirmed_bookings:
        slot = storage.get_slot_by_id(booking["slot_id"])
        if slot:
            writer.writerow({
                'ID': booking['id'],
                'ФИО': booking['full_name'],
                'Группа': booking['group'],
                'Мероприятие': booking['event_type'],
                'Предыдущая аудитория': booking.get('previous_classroom', ''),
                'Email': booking['email'],
                'Дата': slot['date'],
                'Время': get_lesson_time(slot['lesson_number']),
                'Аудитория': slot['classroom'],
                'Корпус': slot['building'],
                'Статус': booking['status'],
                'Дата создания': booking['created_at'].strftime("%Y-%m-%d %H:%M:%S") if booking['created_at'] else ""
            })

    response = JSONResponse(content={"csv": output.getvalue()})
    response.headers["Content-Disposition"] = f"attachment; filename=bookings_{date.today()}.csv"
    return response


@app.delete("/admin/slots/{slot_id}")
async def delete_slot(slot_id: int):
    """Удалить слот"""
    success = storage.delete_slot(slot_id)
    if not success:
        raise HTTPException(status_code=400, detail="Невозможно удалить слот. Возможно, есть активное бронирование.")
    return {"message": "Слот удален"}


# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "slots_count": len(storage.slots),
        "bookings_count": len(storage.bookings),
        "storage_type": "in_memory"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

from fastapi import FastAPI, HTTPException, Request, Depends, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict
import csv
import io
import calendar

app = FastAPI(title="Booking System")
templates = Jinja2Templates(directory="templates")

RUSSIAN_MONTHS = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
}


def get_russian_month_name(month_number: int) -> str:
    """Возвращает название месяца на русском"""
    return RUSSIAN_MONTHS.get(month_number, "Неизвестный месяц")


# Хранилище данных (в памяти)
class DataStorage:
    def __init__(self):
        self.slots = []
        self.bookings = []
        self.admins = {"admin": "admin123"}  # Простая аутентификация
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

        # Создаем несколько демо-бронирований
        demo_slots = [slot for slot in self.slots if slot["is_available"]][:3]
        for i, slot in enumerate(demo_slots):
            booking_data = {
                "slot_id": slot["id"],
                "full_name": f"Преподаватель {i + 1}",
                "group": f"Группа {i + 1}",
                "event_type": "Лекция",
                "previous_classroom": f"Старая аудитория {i + 1}",
                "email": f"teacher{i + 1}@university.edu"
            }
            self.create_booking(booking_data)

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
            "status": "pending",  # pending, confirmed
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
            print(f"Отправка email на {booking['email']}: Бронирование подтверждено")
            return booking
        return None

    def confirm_all_bookings(self):
        for booking in self.bookings:
            if booking["status"] == "pending":
                booking["status"] = "confirmed"
                print(f"Отправка email на {booking['email']}: Бронирование подтверждено")
        return True


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


def get_week_dates(start_date: date):
    """Возвращает даты недели начиная с указанной даты"""
    return [start_date + timedelta(days=i) for i in range(7)]


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
                    "date": day_date.isoformat(),
                    "is_today": day_date == date.today(),
                    "is_past": day_date < date.today(),
                    "has_slots": False
                })
        calendar_data.append(week_data)

    return calendar_data


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

    russian_month_name = get_russian_month_name(today.month)

    return templates.TemplateResponse("teacher_calendar1.html", {
        "request": request,
        "today": today.isoformat(),
        "current_year": today.year,
        "current_month": today.month,
        "month_name": russian_month_name,
        "calendar": month_calendar
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

    return {
        "calendar": month_calendar,
        "year": year,
        "month": month,
        "month_name": get_russian_month_name(month)
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
            "date": slot["date"].isoformat(),
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


# Роуты для администратора (из кода 1)
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
                "date": slot["date"],
                "lesson_time": get_lesson_time(slot["lesson_number"]),
                "classroom": slot["classroom"],
                "building": slot["building"]
            }

    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "pending_bookings": pending_bookings,
        "confirmed_bookings": confirmed_bookings,
        "slots": storage.slots
    })


@app.post("/admin/slots/")
async def create_slot(slot: SlotCreate):
    """Создать новый слот"""
    created_slot = storage.create_slot(slot.dict())
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
                  'Email', 'Дата', 'Время', 'Аудитория', 'Корпус']
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
                'Корпус': slot['building']
            })

    response = JSONResponse(content={"csv": output.getvalue()})
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
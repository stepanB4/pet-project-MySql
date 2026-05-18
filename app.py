from fastapi import UploadFile, File
from fastapi import FastAPI, HTTPException, Request, Depends, Form, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, EmailStr
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, extract
import csv
import io
import calendar
import secrets

from database import (
    get_db, SessionLocal,
    Classroom, Slot, Admin,
    BuildingEnum, BookingStatus,
    get_lesson_time, create_tables
)


create_tables()
app = FastAPI(title="Booking System")
templates = Jinja2Templates(directory="templates", auto_reload=True)
templates.env.cache = {}
security = HTTPBasic()

RUSSIAN_MONTHS = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
}


def get_russian_month_name(month_number: int) -> str:
    return RUSSIAN_MONTHS.get(month_number, "Неизвестный месяц")


# Модели Pydantic
class SlotCreate(BaseModel):
    date: date
    lesson_number: int
    classroom: str
    building: str


class SlotResponse(BaseModel):
    id: int
    date: date
    lesson_number: int
    classroom: str
    building: str
    is_available: bool
    lesson_time: str


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


# Функции для календаря
def get_week_dates(start_date: date):
    return [start_date + timedelta(days=i) for i in range(7)]


def get_month_calendar(year: int, month: int):
    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdayscalendar(year, month)

    calendar_data = []
    for week in month_days:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append(None)
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


# Функции для работы с БДшкой
class DatabaseService:
    @staticmethod
    def get_available_slots_by_date(db: Session, target_date: date):
        return db.query(Slot).join(Classroom).filter(
            and_(
                Slot.date == target_date,
                Slot.is_booked == False,
                Classroom.id == Slot.classroom_id  # Исправлено
            )
        ).all()

    @staticmethod
    def get_available_slots_by_week(db: Session, start_date: date):
        end_date = start_date + timedelta(days=6)
        return db.query(Slot).join(Classroom).filter(
            and_(
                Slot.date >= start_date,
                Slot.date <= end_date,
                Slot.is_booked == False,
                Classroom.id == Slot.classroom_id
            )
        ).all()

    @staticmethod
    def get_available_slots_by_month(db: Session, year: int, month: int):
        # Получаем первый и последний день месяца
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        # Получаем все свободные слоты за месяц
        slots = db.query(Slot).join(Classroom).filter(
            and_(
                Slot.date >= start_date,
                Slot.date <= end_date,
                Slot.is_booked == False
            )
        ).all()

        # Группируем по дням
        grouped_slots = {}
        for slot in slots:
            date_str = slot.date.isoformat()
            if date_str not in grouped_slots:
                grouped_slots[date_str] = 0
            grouped_slots[date_str] += 1

        return grouped_slots

    @staticmethod
    def get_slot_by_id(db: Session, slot_id: int):
        return db.query(Slot).filter(Slot.id == slot_id).first()

    @staticmethod
    def create_booking(db: Session, booking_data: dict):
        # Находим слот
        slot = db.query(Slot).filter(Slot.id == booking_data["slot_id"]).first()
        if not slot:
            return None

        if slot.is_booked:
            return None

        # Обновляем слот
        slot.is_booked = True
        slot.teacher_name = booking_data["full_name"]
        slot.group_name = booking_data["group"]
        slot.event_type = booking_data["event_type"]
        slot.previous_classroom = booking_data.get("previous_classroom")
        slot.email = booking_data["email"]
        slot.status = BookingStatus.pending
        slot.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(slot)

        return slot

    @staticmethod
    def get_pending_bookings(db: Session):
        return db.query(Slot).join(Classroom).filter(
            and_(
                Slot.is_booked == True,
                Slot.status == BookingStatus.pending
            )
        ).all()

    @staticmethod
    def get_confirmed_bookings(db: Session):
        return db.query(Slot).join(Classroom).filter(
            and_(
                Slot.is_booked == True,
                Slot.status == BookingStatus.confirmed
            )
        ).all()

    @staticmethod
    def confirm_booking(db: Session, slot_id: int):
        slot = db.query(Slot).filter(Slot.id == slot_id).first()
        if not slot:
            return None

        slot.status = BookingStatus.confirmed
        slot.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(slot)

        # Здесь можно добавить отправку email
        print(f"Отправка email на {slot.email}: Бронирование подтверждено")

        return slot

    @staticmethod
    def confirm_all_bookings(db: Session):
        pending = db.query(Slot).filter(Slot.status == BookingStatus.pending).all()

        for slot in pending:
            slot.status = BookingStatus.confirmed
            slot.updated_at = datetime.utcnow()
            print(f"Отправка email на {slot.email}: Бронирование подтверждено")

        db.commit()
        return len(pending)

    @staticmethod
    def create_slot(db: Session, slot_data: dict):
        # Находим или создаем аудиторию
        classroom = db.query(Classroom).filter(
            and_(
                Classroom.room_number == slot_data["classroom"],
                Classroom.building == BuildingEnum(slot_data["building"])
            )
        ).first()

        if not classroom:
            classroom = Classroom(
                room_number=slot_data["classroom"],
                building=BuildingEnum(slot_data["building"])
            )
            db.add(classroom)
            db.flush()  # Получаем ID аудитории

        # Проверяем, не существует ли уже такой слот
        existing = db.query(Slot).filter(
            and_(
                Slot.classroom_id == classroom.id,
                Slot.date == slot_data["date"],
                Slot.lesson_number == slot_data["lesson_number"]
            )
        ).first()

        if existing:
            print(f"Слот уже существует: {slot_data}")
            return existing

        slot = Slot(
            classroom_id=classroom.id,
            date=slot_data["date"],
            lesson_number=slot_data["lesson_number"],
            is_booked=False
        )

        db.add(slot)
        db.commit()
        db.refresh(slot)

        print(f"Создан слот ID: {slot.id} (автоинкремент)")
        return slot

    @staticmethod
    def get_all_slots(db: Session):
        return db.query(Slot).join(Classroom).order_by(Slot.date, Slot.lesson_number).all()

    @staticmethod
    def delete_slot(db: Session, slot_id: int):
        slot = db.query(Slot).filter(Slot.id == slot_id).first()
        if not slot:
            return False

        db.delete(slot)
        db.commit()
        return True

    @staticmethod
    def authenticate_admin(db: Session, username: str, password: str):
        # В реальном приложении используйте хеширование паролей!
        admin = db.query(Admin).filter(Admin.username == username).first()
        if admin and admin.password_hash == password:  # Простое сравнение для демо
            return admin
        return None


# Роуты для преподавателя
@app.get("/", response_class=HTMLResponse)
async def teacher_calendar(request: Request, db: Session = Depends(get_db)):
    today = date.today()
    month_calendar = get_month_calendar(today.year, today.month)

    # Получаем количество слотов по дням
    month_slots = DatabaseService.get_available_slots_by_month(db, today.year, today.month)

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
async def get_calendar(year: int, month: int, db: Session = Depends(get_db)):
    month_calendar = get_month_calendar(year, month)
    month_slots = DatabaseService.get_available_slots_by_month(db, year, month)

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
async def get_month_slots_summary(year: int, month: int, db: Session = Depends(get_db)):
    slots = DatabaseService.get_available_slots_by_month(db, year, month)

    total_slots = sum(slots.values())
    days_with_slots = len(slots)

    return {
        "total_slots": total_slots,
        "days_with_slots": days_with_slots,
        "slots_by_day": slots
    }


@app.get("/api/slots/date/{slot_date}")
async def get_slots_by_date(slot_date: date, db: Session = Depends(get_db)):
    slots = DatabaseService.get_available_slots_by_date(db, slot_date)
    result = []

    for slot in slots:
        classroom = db.query(Classroom).filter(Classroom.id == slot.classroom_id).first()
        if classroom:
            result.append({
                "id": slot.id,
                "date": slot.date.isoformat(),
                "lesson_number": slot.lesson_number,
                "classroom": classroom.room_number,
                "building": classroom.building.value,
                "lesson_time": get_lesson_time(slot.lesson_number)
            })

    return result


@app.get("/api/slots/week/{start_date}")
async def get_slots_by_week(start_date: date, db: Session = Depends(get_db)):
    slots = DatabaseService.get_available_slots_by_week(db, start_date)

    # Группируем по дням
    week_slots = {}
    for i in range(7):
        day_date = start_date + timedelta(days=i)
        day_slots = [slot for slot in slots if slot.date == day_date]

        week_slots[day_date.isoformat()] = []
        for slot in day_slots:
            classroom = db.query(Classroom).filter(Classroom.id == slot.classroom_id).first()
            if classroom:
                week_slots[day_date.isoformat()].append({
                    "id": slot.id,
                    "date": slot.date.isoformat(),
                    "lesson_number": slot.lesson_number,
                    "classroom": classroom.room_number,
                    "building": classroom.building.value,
                    "lesson_time": get_lesson_time(slot.lesson_number),
                    "date_display": day_date.strftime("%d.%m.%Y")
                })

    return {
        "start_date": start_date.isoformat(),
        "end_date": (start_date + timedelta(days=6)).isoformat(),
        "slots": week_slots
    }


@app.post("/api/bookings/")
async def create_booking(booking: BookingCreate, db: Session = Depends(get_db)):
    slot = DatabaseService.get_slot_by_id(db, booking.slot_id)
    if not slot or slot.is_booked:
        raise HTTPException(status_code=400, detail="Слот недоступен")

    booking_data = booking.dict()
    created_booking = DatabaseService.create_booking(db, booking_data)

    if not created_booking:
        raise HTTPException(status_code=400, detail="Ошибка создания бронирования")

    return {"message": "Бронирование создано", "booking_id": created_booking.id}


# Роуты для администратора
@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request})


@app.post("/admin/login")
async def admin_login(login_data: AdminLogin, db: Session = Depends(get_db)):
    admin = DatabaseService.authenticate_admin(db, login_data.username, login_data.password)
    if not admin:
        raise HTTPException(status_code=401, detail="Неверные учетные данные")

    return {"message": "Успешный вход", "redirect": "/admin/dashboard"}


@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    # Получаем данные из базы
    pending_bookings = DatabaseService.get_pending_bookings(db)
    confirmed_bookings = DatabaseService.get_confirmed_bookings(db)
    all_slots = DatabaseService.get_all_slots(db)

    # Подготавливаем данные для шаблона
    pending_list = []
    for slot in pending_bookings:
        classroom = db.query(Classroom).filter(Classroom.id == slot.classroom_id).first()
        pending_list.append({
            "id": slot.id,
            "full_name": slot.teacher_name,
            "group": slot.group_name,
            "event_type": slot.event_type,
            "previous_classroom": slot.previous_classroom,
            "email": slot.email,
            "slot_info": {
                "date": slot.date,
                "lesson_time": get_lesson_time(slot.lesson_number),
                "classroom": classroom.room_number if classroom else "",
                "building": classroom.building.value if classroom else ""
            }
        })

    confirmed_list = []
    for slot in confirmed_bookings:
        classroom = db.query(Classroom).filter(Classroom.id == slot.classroom_id).first()
        confirmed_list.append({
            "id": slot.id,
            "full_name": slot.teacher_name,
            "group": slot.group_name,
            "event_type": slot.event_type,
            "previous_classroom": slot.previous_classroom,
            "email": slot.email,
            "slot_info": {
                "date": slot.date,
                "lesson_time": get_lesson_time(slot.lesson_number),
                "classroom": classroom.room_number if classroom else "",
                "building": classroom.building.value if classroom else ""
            }
        })

    slots_list = []
    for slot in all_slots:
        classroom = db.query(Classroom).filter(Classroom.id == slot.classroom_id).first()
        slots_list.append({
            "id": slot.id,
            "date": slot.date,
            "lesson_number": slot.lesson_number,
            "classroom": classroom.room_number if classroom else "",
            "building": classroom.building.value if classroom else "",
            "is_available": not slot.is_booked
        })

    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "pending_bookings": pending_list,
        "confirmed_bookings": confirmed_list,
        "slots": slots_list
    })


@app.post("/admin/slots/")
async def create_slot(slot: SlotCreate, db: Session = Depends(get_db)):
    created_slot = DatabaseService.create_slot(db, slot.dict())
    return {"message": "Слот создан", "slot_id": created_slot.id}


@app.post("/admin/slots/upload-csv")
async def upload_slots_csv(
        file: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    #Чекните ошибку BOM кодировка даты !!! (Даня)
    try:
        print(f"🔍 Получен файл: {file.filename}, размер: {file.size}")
        content_bytes = await file.read()

        # BOM
        content_str = content_bytes.decode('utf-8-sig')
        content_str = content_str.strip()


        if content_str.startswith('\ufeff'):
            content_str = content_str[1:].strip()

        print(f"Содержимое:\n{content_str}")
        lines = [line.strip() for line in content_str.splitlines() if line.strip()]

        if len(lines) < 2:
            raise HTTPException(status_code=400, detail="CSV файл пуст")

        # CSV reader (Стёпа)
        csv_content = '\n'.join(lines)
        csv_file = io.StringIO(csv_content)
        reader = csv.DictReader(csv_file)

        if not reader.fieldnames:
            raise HTTPException(status_code=400, detail="CSV не содержит заголовков")

        print(f"Заголовки: {reader.fieldnames}")

        created_count = 0
        errors = []

        for row_num, row in enumerate(reader, start=1):
            print(f"Строка {row_num}: {row}")

            try:
                if not any(str(value).strip() for value in row.values()):
                    continue
                # Просто берем первые 4 колонки в порядке заголовков
                headers = list(row.keys())
                if len(headers) < 4:
                    errors.append(f"Строка {row_num}: недостаточно колонок")
                    continue

                date_str = str(row[headers[0]]).strip()
                lesson_str = str(row[headers[1]]).strip()
                classroom = str(row[headers[2]]).strip()
                building = str(row[headers[3]]).strip()

                print(
                    f"  Извлечено: дата='{date_str}', пара='{lesson_str}', аудитория='{classroom}', корпус='{building}'")

                # Парсинг даты (Кирилл)
                try:
                    if '.' in date_str:
                        day, month, year = date_str.split('.')
                        date_str = f"{year}-{month}-{day}"

                    slot_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    print(f"  Дата: {slot_date}")
                except ValueError:
                    errors.append(f"Строка {row_num}: неверный формат даты '{date_str}'")
                    continue

                # Парсинг номера пары (КИрилл)
                try:
                    lesson_num = int(lesson_str)
                    if not 1 <= lesson_num <= 8:
                        errors.append(f"Строка {row_num}: номер пары должен быть 1-8")
                        continue
                except ValueError:
                    errors.append(f"Строка {row_num}: номер пары должен быть числом")
                    continue

                building_normalized = building.upper().strip()

                try:
                    building_enum = BuildingEnum(building_normalized)
                except ValueError:
                    errors.append(f"Строка {row_num}: неверный корпус '{building}'")
                    continue

                # Проверка на дубликаты (Кирилл)
                existing = db.query(Slot).join(Classroom).filter(
                    and_(
                        Slot.date == slot_date,
                        Slot.lesson_number == lesson_num,
                        Classroom.room_number == classroom,
                        Classroom.building == building_enum
                    )
                ).first()

                if existing:
                    print(f"Слот уже существует")
                    continue

                slot_data = {
                    "date": slot_date,
                    "lesson_number": lesson_num,
                    "classroom": classroom,
                    "building": building_normalized
                }

                DatabaseService.create_slot(db, slot_data)
                created_count += 1
                print(f"  ✅ Создан слот")

            except Exception as e:
                errors.append(f"Строка {row_num}: ошибка обработки - {str(e)}")
                continue

        result = {
            "message": f"Успешно обработано {created_count} строк",
            "created": created_count
        }

        if errors:
            result["errors"] = errors

        return result

    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/slots/{slot_id}")
async def delete_slot(slot_id: int, db: Session = Depends(get_db)):
    success = DatabaseService.delete_slot(db, slot_id)
    if not success:
        raise HTTPException(status_code=404, detail="Слот не найден")
    return {"message": "Слот удален"}


@app.post("/admin/bookings/{slot_id}/confirm")
async def confirm_booking(slot_id: int, db: Session = Depends(get_db)):
    booking = DatabaseService.confirm_booking(db, slot_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Бронирование не найдено")
    return {"message": "Бронирование подтверждено"}


@app.post("/admin/bookings/confirm-all")
async def confirm_all_bookings(db: Session = Depends(get_db)):
    count = DatabaseService.confirm_all_bookings(db)
    return {"message": f"Все бронирования ({count}) подтверждены"}


@app.get("/admin/bookings/export-csv")
async def export_bookings_csv(db: Session = Depends(get_db)):
    try:
        confirmed_bookings = DatabaseService.get_confirmed_bookings(db)

        output = io.StringIO()
        # Изменено: 'Время' → 'Пара'
        fieldnames = ['ФИО', 'Группа', 'Мероприятие', 'Предыдущая аудитория',
                      'Email', 'Дата', 'Пара', 'Аудитория', 'Корпус', 'Статус']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for slot in confirmed_bookings:
            classroom = db.query(Classroom).filter(
                Classroom.id == slot.classroom_id
            ).first()

            if not classroom:
                continue

            writer.writerow({
                'ФИО': slot.teacher_name or '',
                'Группа': slot.group_name or '',
                'Мероприятие': slot.event_type or '',
                'Предыдущая аудитория': slot.previous_classroom or '',
                'Email': slot.email or '',
                'Дата': slot.date,
                'Пара': slot.lesson_number,
                'Аудитория': classroom.room_number,
                'Корпус': classroom.building.value,
                'Статус': slot.status.value
            })

        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),
            media_type="text/csv; charset=utf-8-sig",
            headers={
                "Content-Disposition": "attachment; filename=bookings.csv",
                "Content-Type": "text/csv; charset=utf-8-sig"
            }
        )

    except Exception as e:
        print(f"Ошибка при экспорте CSV: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка экспорта: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
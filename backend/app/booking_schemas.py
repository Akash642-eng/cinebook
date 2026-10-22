from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ScreenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    total_seats: int


class CinemaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    city: str
    address: str


class ShowtimeResponse(BaseModel):
    id: int
    movie_id: int
    movie_title: str
    cinema_id: int
    cinema_name: str
    city: str
    screen_id: int
    screen_name: str
    total_seats: int
    starts_at: datetime
    ticket_price_paise: int


class BookingCreate(BaseModel):
    showtime_id: int = Field(gt=0)
    seat_number: int = Field(gt=0)


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    showtime_id: int
    seat_number: int
    status: str
    booked_at: datetime


class SeatResponse(BaseModel):
    seat_number: int
    status: str


class SeatAvailabilityResponse(BaseModel):
    showtime_id: int
    total_seats: int
    available_seats: int
    booked_seats: int
    seats: list[SeatResponse]

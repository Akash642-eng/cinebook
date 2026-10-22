from pydantic import BaseModel, ConfigDict


class MovieResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    genre: str
    language: str
    duration_minutes: int
    description: str
    poster_url: str

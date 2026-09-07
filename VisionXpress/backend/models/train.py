from pydantic import BaseModel


class TrainSchedule(BaseModel):
    train_id: str
    train_type: str
    date: str

    route_id: str
    section_id: str

    start_station: str
    end_station: str

    start_time: str
    end_time: str

    direction: str
    train_priority: str
    operational_status: str
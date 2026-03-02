from gera.entities import EventEntity, NoteEntity, ProjectEntity, TaskEntity
from pydantic import BaseModel, Field


class State(BaseModel):
    events: list[EventEntity] = Field(default_factory=list)
    notes: list[NoteEntity] = Field(default_factory=list)
    projects: list[ProjectEntity] = Field(default_factory=list)
    tasks: list[TaskEntity] = Field(default_factory=list)

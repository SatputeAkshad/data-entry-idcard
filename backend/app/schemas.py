from pydantic import BaseModel, Field, ConfigDict
from typing import Literal
class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')
class FieldSpec(Strict):
    key: str = Field(pattern=r'^[a-z][a-z0-9_]*$', max_length=64)
    label: str = Field(min_length=1, max_length=100)
    type: Literal['text','date','select'] = 'text'
    required: bool = False
    repeat: bool = False
    options: list[str] = Field(default_factory=list, max_length=500)
class InstitutionIn(Strict):
    name: str = Field(min_length=1, max_length=200)
    year: str = Field(max_length=30)
    fields: list[FieldSpec] = Field(min_length=1, max_length=60)
class StudentIn(Strict):
    institution_id: str
    data: dict[str,str]
    status: Literal['draft','ready'] = 'draft'
    revision: int | None = None
class Crop(Strict):
    rotation: Literal[0,90,180,270] = 0
    left: float = Field(default=0, ge=0, lt=1)
    top: float = Field(default=0, ge=0, lt=1)
    right: float = Field(default=1, gt=0, le=1)
    bottom: float = Field(default=1, gt=0, le=1)
class JobIn(Strict):
    key: str = Field(min_length=10, max_length=100)
    template_id: str
    student_ids: list[str] = Field(min_length=1, max_length=5000)
class SheetIn(Strict):
    width: float = Field(default=210, gt=0, le=2000)
    height: float = Field(default=297, gt=0, le=2000)
    card_width: float = Field(default=85.6, gt=0)
    card_height: float = Field(default=54, gt=0)
    margin: float = Field(default=10, ge=0)
    gap: float = Field(default=5, ge=0)
    bleed: float = Field(default=0, ge=0)
    duplex: Literal['none','long-edge','short-edge'] = 'none'
    cutting_marks: bool = True

# apps/schemas.py
from pydantic import BaseModel
from datetime import datetime


class BaseSchema(BaseModel):
    class Config:
        extra = "forbid"  # 禁止额外字段
        orm_mode = True   # 允许ORM模型转换
        json_encoders = {
            datetime: lambda v: v.isoformat()  # 日期时间序列化
        }


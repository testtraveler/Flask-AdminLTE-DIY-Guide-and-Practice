# apps/schemas.py
from pydantic import BaseModel, field_validator, create_model
from datetime import datetime
from typing import Optional, Generic, TypeVar, List, Type

# 通用类型变量，用于泛型响应
T = TypeVar('T')

class BaseSchema(BaseModel):
    class Config:
        extra = "forbid"  # 禁止额外字段
        from_attributes=True  # 允许从类属性中加载字段
        arbitrary_types_allowed=True  # 允许任意类型字段
        json_encoders = {
            datetime: lambda v: v.isoformat()  # 日期时间序列化
        }

    @classmethod
    def with_fields(cls, fields: List[str]) -> Type["BaseSchema"]:
        """动态生成只包含指定字段的 Schema 子类"""
        # 1. 取出需要的字段及其“原始类型”
        valid_fields = {}
        for name in fields:
            if name not in cls.model_fields:
                continue
            field_info = cls.model_fields[name]      # FieldInfo 实例
            # 取真实注解类型（field_info.annotation 就是 int / str / ...）
            valid_fields[name] = (field_info.annotation, field_info)

        if not valid_fields:
            raise ValueError("至少需要指定一个有效字段")

        # 2. 创建动态模型
        return create_model(
            f"{cls.__name__}WithFields",
            __base__=cls,
            **valid_fields
        )

# ------------------------------
# 通用响应体Schema（封装所有接口响应）
# ------------------------------
class APIResponse(BaseModel, Generic[T]):
    code: int = 200
    message: str = "success"
    data: Optional[T] = None

# ------------------------------
# 基础模型Schema（示例）
# ------------------------------
class BaseModelCreateSchema(BaseSchema):
    """基础模型创建请求体（无ID和时间字段，由系统生成）"""
    pass

class BaseModelUpdateSchema(BaseSchema):
    """基础模型更新请求体（仅允许更新部分字段）"""
    pass

class BaseModelResponseSchema(BaseSchema):
    """基础模型响应体（包含所有字段，用于查询返回）"""
    id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

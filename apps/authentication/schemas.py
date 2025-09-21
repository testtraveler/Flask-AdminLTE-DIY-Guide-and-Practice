# apps/authentication/schemas.py
from pydantic import Field, EmailStr, field_validator, computed_field
from typing import Optional, List
from datetime import datetime
from enum import Enum

from apps.schemas import (
    BaseSchema,
    BaseModelCreateSchema,  # 导入基类创建Schema
    BaseModelUpdateSchema,  # 导入基类更新Schema
    BaseModelResponseSchema  # 导入基类响应Schema
)

from apps.authentication.utils import hash_pass

# ---------- 角色相关Schema ----------
class RoleBase(BaseSchema):
    name: str = Field(..., max_length=64, description="角色名称")
    description: Optional[str] = Field(None, description="角色描述")

# 继承基类创建Schema（无ID和时间字段）
class RoleCreate(RoleBase, BaseModelCreateSchema):
    pass

# 继承基类更新Schema（仅允许部分字段更新）
class RoleUpdate(RoleBase, BaseModelUpdateSchema):
    name: Optional[str] = Field(None, max_length=64, description="角色名称")  # 重写为可选字段

# 继承基类响应Schema（包含ID和时间字段）
class RoleOut(RoleBase, BaseModelResponseSchema):
    # 基类已包含 id, created_at, updated_at, deleted_at，无需重复定义
    pass

# ---------- 用户组相关Schema ----------
class GroupBase(BaseSchema):
    name: str = Field(..., max_length=64, description="用户组名称")
    description: Optional[str] = Field(None, description="用户组描述")

class GroupCreate(GroupBase, BaseModelCreateSchema):
    pass

class GroupUpdate(GroupBase, BaseModelUpdateSchema):
    name: Optional[str] = Field(None, max_length=64, description="用户组名称")  # 重写为可选字段

class GroupOut(GroupBase, BaseModelResponseSchema):
    pass  # 复用基类的ID和时间字段

# ---------- OAuth相关Schema ----------
class OAuthProvider(str, Enum):
    github = "github"
    google = "google"

class OAuthBase(BaseSchema):
    provider: OAuthProvider = Field(..., description="OAuth提供商")
    provider_user_id: str = Field(..., max_length=100, description="提供商用户ID")

class OAuthCreate(OAuthBase, BaseModelCreateSchema):
    user_id: int = Field(..., description="关联用户ID")

class OAuthUpdate(OAuthBase, BaseModelUpdateSchema):
    user_id: Optional[int] = Field(None, description="关联用户ID")  # 重写为可选字段

class OAuthOut(OAuthBase, BaseModelResponseSchema):
    user_id: int  # 补充关联字段
    # 基类已包含 id, created_at, updated_at, deleted_at

# ---------- 用户相关Schema ----------
class UserBase(BaseSchema):
    username: str = Field(..., min_length=3, max_length=64, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    bio: Optional[str] = Field(None, description="个人简介")

class UserCreate(UserBase, BaseModelCreateSchema):
    password: bytes = Field(..., description="密码")
    role_id: Optional[int] = Field(None, description="角色ID")
    group_id: Optional[int] = Field(None, description="用户组ID")

    # 密码加密处理
    @field_validator('password', mode='before')
    def validate_password(cls, v):
        if isinstance(v, str):
            return hash_pass(v)
        raise ValueError("密码必须是字符串")

class UserUpdate(UserBase, BaseModelUpdateSchema):
    # 重写为可选字段（更新时可部分修改）
    username: Optional[str] = Field(None, min_length=3, max_length=64, description="用户名")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    role_id: Optional[int] = Field(None, description="角色ID")
    group_id: Optional[int] = Field(None, description="用户组ID")
    password: bytes = Field(..., description="密码")
    
    # 密码加密处理
    @field_validator('password', mode='before')
    def validate_password(cls, v):
        if isinstance(v, str):
            return hash_pass(v)
        raise ValueError("密码必须是字符串")

class UserOut(UserBase, BaseModelResponseSchema):
    password: Optional[bytes] = Field(..., description="密码")
    role_id: Optional[int]
    group_id: Optional[int]
    last_login_at: Optional[datetime]  # 补充用户特有时间字段
    # 关联对象
    role: Optional[RoleOut] = None
    group: Optional[GroupOut] = None
    oauths: List[OAuthOut] = []
    
    # --- Flask-Login 虚拟字段 ---
    @computed_field
    @property
    def is_authenticated(self) -> bool:
        # 只要 JWT 能签发成功，就已经鉴权
        return True

    @computed_field
    @property
    def is_active(self) -> bool:
        # 如果业务有“禁用”字段，可换成 self.status == "active"
        return True

    @computed_field
    @property
    def is_anonymous(self) -> bool:
        # 走到这一定是登录用户
        return False

    def get_id(self) -> str:
        return str(self.id)

# 其他Schema（登录/批量操作/审计）
class UserLogin(BaseSchema):
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")

class Token(BaseSchema):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseSchema):
    username: Optional[str] = None

class BulkRoleAssign(BaseSchema):
    user_ids: List[int] = Field(..., min_items=1, description="用户ID列表")
    role_id: int = Field(..., description="分配的角色ID")

class BulkGroupAssign(BaseSchema):
    user_ids: List[int] = Field(..., min_items=1, description="用户ID列表")
    group_id: int = Field(..., description="分配的用户组ID")

class AuditStatsRequest(BaseSchema):
    days: int = Field(7, ge=1, le=365, description="统计天数范围(1-365)")

class AuditStatsResponse(BaseSchema):
    days: int
    active_user_count: int

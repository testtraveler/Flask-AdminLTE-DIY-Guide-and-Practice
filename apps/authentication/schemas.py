# apps/authentication/schemas.py
from pydantic import Field, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

from apps.schemas import BaseSchema

# ---------- 角色相关Schema ----------
class RoleBase(BaseSchema):
    name: str = Field(..., max_length=64, description="角色名称")
    description: Optional[str] = Field(None, description="角色描述")

class RoleCreate(RoleBase):
    pass

class RoleUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=64, description="角色名称")
    description: Optional[str] = Field(None, description="角色描述")

class RoleOut(RoleBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    deleted_at: Optional[datetime]

# ---------- 用户组相关Schema ----------
class GroupBase(BaseSchema):
    name: str = Field(..., max_length=64, description="用户组名称")
    description: Optional[str] = Field(None, description="用户组描述")

class GroupCreate(GroupBase):
    pass

class GroupUpdate(BaseSchema):
    name: Optional[str] = Field(None, max_length=64, description="用户组名称")
    description: Optional[str] = Field(None, description="用户组描述")

class GroupOut(GroupBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    deleted_at: Optional[datetime]

# ---------- OAuth相关Schema ----------
class OAuthProvider(str, Enum):
    github = "github"
    google = "google"

class OAuthBase(BaseSchema):
    provider: OAuthProvider = Field(..., description="OAuth提供商")
    provider_user_id: str = Field(..., max_length=100, description="提供商用户ID")

class OAuthCreate(OAuthBase):
    user_id: int = Field(..., description="关联用户ID")

class OAuthOut(OAuthBase):
    id: int
    user_id: int
    created_at: datetime

# ---------- 用户相关Schema ----------
class UserBase(BaseSchema):
    username: str = Field(..., min_length=3, max_length=64, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    bio: Optional[str] = Field(None, description="个人简介")

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, description="密码")
    role_id: Optional[int] = Field(None, description="角色ID")
    group_id: Optional[int] = Field(None, description="用户组ID")

    @field_validator('password')
    @classmethod
    def password_complexity(cls, v: str) -> str:
        """验证密码复杂度"""
        if len(v) < 6:
            raise ValueError("密码长度至少6位")
        return v

class UserUpdate(BaseSchema):
    username: Optional[str] = Field(None, min_length=3, max_length=64, description="用户名")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    bio: Optional[str] = Field(None, description="个人简介")
    role_id: Optional[int] = Field(None, description="角色ID")
    group_id: Optional[int] = Field(None, description="用户组ID")

class UserOut(UserBase):
    id: int
    role_id: Optional[int]
    group_id: Optional[int]
    last_login_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    deleted_at: Optional[datetime]
    
    # 关联对象
    role: Optional[RoleOut] = None
    group: Optional[GroupOut] = None
    oauths: List[OAuthOut] = []

# ---------- 登录/认证相关Schema ----------
class UserLogin(BaseSchema):
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")

class Token(BaseSchema):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseSchema):
    username: Optional[str] = None

# ---------- 批量操作Schema ----------
class BulkRoleAssign(BaseSchema):
    user_ids: List[int] = Field(..., min_items=1, description="用户ID列表")
    role_id: int = Field(..., description="分配的角色ID")

class BulkGroupAssign(BaseSchema):
    user_ids: List[int] = Field(..., min_items=1, description="用户ID列表")
    group_id: int = Field(..., description="分配的用户组ID")

# ---------- 审计统计Schema ----------
class AuditStatsRequest(BaseSchema):
    days: int = Field(7, ge=1, le=365, description="统计天数范围(1-365)")

class AuditStatsResponse(BaseSchema):
    days: int
    active_user_count: int

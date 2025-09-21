# -*- encoding: utf-8 -*-
"""
服务层实现 - 提供批量操作、软删除管理和查询过滤功能（类方法版）
"""
from __future__ import annotations

from typing import List, Optional, Dict, Any, Type
from datetime import datetime, timezone, timedelta
from sqlalchemy import or_

from apps.services import BaseService
from apps.authentication.models import User, Role, Group, OAuth
from apps.authentication.schemas import (
    RoleCreate, RoleUpdate, RoleOut,
    GroupCreate, GroupUpdate, GroupOut,
    OAuthCreate, OAuthUpdate, OAuthOut,
    UserCreate, UserUpdate, UserOut
)
from apps.authentication.utils import verify_pass


# region 角色服务
# -------------------------------------------------
# RoleService / GroupService / OauthService - 字段提示
# -------------------------------------------------
class RoleService(BaseService[RoleCreate, RoleUpdate, RoleOut]):
    """角色服务"""

    model_class = Role
    create_schema = RoleCreate
    update_schema = RoleUpdate
    response_schema = RoleOut

    @classmethod
    def get_users_count(cls, role_id: int) -> int:
        """获取角色下的用户数量"""
        return UserService.find_by_filter(role_id=role_id, include_deleted=False).count()
    
    @classmethod
    def find_by_name(cls, name: str, include_deleted: bool = False, fields_response: Optional[List[str]] = None) -> Optional[Role]:
        """根据角色名查角色"""
        roles = cls.find_by_filter(name=name, include_deleted=include_deleted, fields_response=fields_response)
        return roles[0] if roles else None
# endregion


# region 用户组服务
class GroupService(BaseService[GroupCreate, GroupUpdate, GroupOut]):
    """用户组服务"""

    model_class = Group
    create_schema = GroupCreate
    update_schema = GroupUpdate
    response_schema = GroupOut
    
    def get_users_count(cls, group_id: int) -> int:
        """获取用户组下的用户数量"""
        return UserService.find_by_filter(group_id=group_id, include_deleted=False).count()
    
    @classmethod
    def find_by_name(cls, name: str, include_deleted: bool = False) -> Optional[Group]:
        """根据组名查组"""
        groups = cls.find_by_filter(name=name, include_deleted=include_deleted)
        return groups[0] if groups else None
# endregion

# region OAuth 服务
class OAuthService(BaseService):
    """OAuth 服务"""
    
    model_class = OAuth
    create_schema = OAuthCreate
    update_schema = OAuthUpdate
    response_schema = OAuthOut
# endregion


# region 用户服务
# -------------------------------------------------
# UserService - 业务定制 + 字段提示
# -------------------------------------------------
class UserService(BaseService):
    """用户服务（含字段白名单与业务定制）"""

    model_class = User
    create_schema = UserCreate
    update_schema = UserUpdate
    response_schema = UserOut

    # --------------- 业务封装 ---------------
    # region 检查方法
    @classmethod
    def is_username_available(cls, username: str) -> bool:
        """检查用户名是否可用"""
        return not cls.find_by_filter(username=username, include_deleted=False).first()
    
    @classmethod
    def is_email_available(cls, email: str) -> bool:
        """检查邮箱是否可用"""
        return not cls.find_by_filter(email=email, include_deleted=False).first()
    # endregion
    
    # region 登录注册相关方法
    @classmethod
    def register(cls, username: str, email: str, password: str, **extra: Any) -> UserOut:
        """用户注册"""
        data = {"username": username, "email": email, "password": password, **extra}
        return cls.create(data)
    
    @classmethod
    def update_last_login(cls, uid: int) -> UserOut:
        """更新用户最后登录时间"""
        data = {"last_login_at": datetime.now(timezone.utc)}
        return cls.update(uid, data)

    @classmethod
    def set_password(cls, uid: int, new_password: str) -> UserOut:
        """重置密码"""
        return cls.update(uid, {"password": new_password})

    @classmethod
    def verify_password(cls, uid: int, raw: str) -> bool:
        """校验原始密码"""
        user = cls.get_by_id(uid)
        return user and verify_pass(raw, user.password)
    # endregion
    
    # region 查询方法
    @classmethod
    def find_by_username(cls, username: str, include_deleted: bool = False, fields_response: Optional[List[str]] = None) -> Optional[UserOut]:
        """根据用户名查用户"""
        users = cls.find_by_filter(username=username, include_deleted=include_deleted, fields_response=fields_response)
        return users[0] if users else None
    
    @classmethod
    def find_by_email(cls, email: str, include_deleted: bool = False, fields_response: Optional[List[str]] = None) -> Optional[UserOut]:
        """根据邮箱查用户"""
        users = cls.find_by_filter(email=email, include_deleted=include_deleted, fields_response=fields_response)
        return users[0] if users else None

    @classmethod
    def find_by_role(cls, role_id: int, include_deleted: bool = False, fields_response: Optional[List[str]] = None) -> List[UserOut]:
        """根据角色批量查用户"""
        return cls.find_by_filter(role_id=role_id, include_deleted=include_deleted, fields_response=fields_response)

    @classmethod
    def find_by_group(cls, group_id: int, include_deleted: bool = False, fields_response: Optional[List[str]] = None) -> List[UserOut]:
        """根据用户组批量查用户"""
        return cls.find_by_filter(group_id=group_id, include_deleted=include_deleted, fields_response=fields_response)
    # endregion
    
    # region 批量操作方法
    @classmethod
    def bulk_update_role(cls, user_ids: List[int], role_id: int, batch_size: int = 1000) -> None:
        """批量更新用户角色"""
        return cls.bulk_update(user_ids, {"role_id": role_id}, batch_size=batch_size)
    @classmethod
    def bulk_update_group(cls, user_ids: List[int], group_id: int, batch_size: int = 1000) -> None:
        """批量更新用户组"""
        return cls.bulk_update(user_ids, {"group_id": group_id}, batch_size=batch_size)
    # endregion
    
    @classmethod
    def soft_delete(cls, id: int, fields_response: Optional[List[str]] = None) -> UserOut:
        """软删除用户，并同步清理 OAuth 授权"""
        user = super().soft_delete(id, fields_response=fields_response)
        
        # 同步清理 OAuth 授权
        oauths = OAuthService.find_by_filter(user_id=id, include_deleted=True, fields_response=None)
        OAuthService.bulk_hard_delete([o.id for o in oauths], batch_size=1000)
        return user
# endregion

# region 审计/统计服务
# -------------------------------------------------
# AuditService - 审计/统计
# -------------------------------------------------
class AuditService:
    """常用审计统计（纯静态方法）"""

    pass
# endregion

# region Flask-Login 回调
# -------------------------------------------------
# Flask-Login 回调
# -------------------------------------------------
from apps import login_manager
@login_manager.user_loader
def user_loader(uid: int) -> Optional[UserOut]:
    return UserService.get_by_id(uid, include_deleted=False)


@login_manager.request_loader
def request_loader(request) -> Optional[UserOut]:
    username = request.form.get("username")
    if not username:
        return None
    users = UserService.find_by_filter(username=username, include_deleted=False)
    return users[0] if users else None
# endregion
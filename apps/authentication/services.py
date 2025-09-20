# -*- encoding: utf-8 -*-
"""
服务层实现 - 提供批量操作、软删除管理和查询过滤功能（类方法版）
"""
from __future__ import annotations

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy import or_, and_

from apps.services import PromptService
from apps.authentication.models import User, Role, Group, OAuth
from apps.authentication.util import verify_pass

# region 角色服务
# -------------------------------------------------
# RoleService / GroupService / OauthService - 字段提示
# -------------------------------------------------
class RoleService(PromptService):
    """角色服务"""

    model_class = Role
    writable_fields = {"name", "description"}
    searchable_fields = {"name", "description"}

    @classmethod
    def get_users_count(cls, role_id: int) -> int:
        """获取角色下的用户数量"""
        return UserService.find_by_filter(role_id=role_id, include_deleted=False).count()
    
    @classmethod
    def find_by_name(cls, name: str, include_deleted: bool = False) -> Optional[Role]:
        """根据角色名查角色"""
        roles = cls.find_by_filter(name=name, include_deleted=include_deleted)
        return roles[0] if roles else None
# endregion


# region 用户组服务
class GroupService(PromptService):
    """用户组服务"""

    model_class = Group
    writable_fields = {"name", "description"}
    searchable_fields = {"name", "description"}
    
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
class OAuthService(PromptService):
    """OAuth 服务"""
    
    model_class = OAuth
    writable_fields = {"user_id"}
    searchable_fields = {"user_id"}
# endregion


# region 用户服务
# -------------------------------------------------
# UserService - 业务定制 + 字段提示
# -------------------------------------------------
class UserService(PromptService):
    """用户服务（含字段白名单与业务定制）"""

    model_class = User
    # 允许写入的字段（IDE 会提示）
    writable_fields = {
        "username", "email", "password", "phone", "bio",
        "role_id", "group_id", "oauth_github", "oauth_google"
    }
    # 允许搜索的字段
    searchable_fields = {"username", "email", "phone", "bio"}

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
    def register(cls, username: str, email: str, password: str, **extra: Any) -> User:
        """用户注册（密码自动哈希）"""
        return cls.create(username=username, email=email, password=password, **extra)
    
    @classmethod
    def update_last_login(cls, uid: int) -> User:
        """更新用户最后登录时间"""
        return cls.update(uid, last_login_at=datetime.now(timezone.utc))

    @classmethod
    def set_password(cls, uid: int, new_password: str) -> User:
        """重置密码"""
        return cls.update(uid, password=new_password)

    @classmethod
    def verify_password(cls, uid: int, raw: str) -> bool:
        """校验原始密码"""
        user = cls.get_by_id(uid)
        return user and verify_pass(raw, user.password)
    # endregion
    
    # region 查询方法
    @classmethod
    def find_by_username(cls, username: str, include_deleted: bool = False) -> Optional[User]:
        """根据用户名查用户"""
        users = cls.find_by_filter(username=username, include_deleted=include_deleted)
        return users[0] if users else None
    
    @classmethod
    def find_by_email(cls, email: str, include_deleted: bool = False) -> Optional[User]:
        """根据邮箱查用户"""
        users = cls.find_by_filter(email=email, include_deleted=include_deleted)
        return users[0] if users else None

    @classmethod
    def find_by_role(cls, role_id: int, include_deleted: bool = False) -> List[User]:
        """根据角色批量查用户"""
        return cls.find_by_filter(role_id=role_id, include_deleted=include_deleted)

    @classmethod
    def find_by_group(cls, group_id: int, include_deleted: bool = False) -> List[User]:
        """根据用户组批量查用户"""
        return cls.find_by_filter(group_id=group_id, include_deleted=include_deleted)
    # endregion
    
    # region 批量操作方法
    @classmethod
    def bulk_update_role(cls, user_ids: List[int], role_id: int) -> Dict[str, Any]:
        """批量更新用户角色"""
        return cls.bulk_update(user_ids, {"role_id": role_id})
    @classmethod
    def bulk_update_group(cls, user_ids: List[int], group_id: int) -> Dict[str, Any]:
        """批量更新用户组"""
        return cls.bulk_update(user_ids, {"group_id": group_id})
    # endregion
    
    @classmethod
    def soft_delete(cls, id: int) -> User:
        """软删除用户，并同步清理 OAuth 授权"""
        user = super().soft_delete(id)
        
        # 同步清理 OAuth 授权
        oauths = OAuthService.find_by_filter(user_id=id, include_deleted=True)
        OAuthService.bulk_hard_delete([o.id for o in oauths])
        return user
# endregion

# region 审计/统计服务
# -------------------------------------------------
# AuditService - 审计/统计
# -------------------------------------------------
class AuditService:
    """常用审计统计（纯静态方法）"""

    @staticmethod
    def recently_registered(days: int = 7) -> List[User]:
        """最近 N 天新增用户"""
        since = datetime.now(timezone.utc) - timedelta(days=days)
        return User.query_active().filter(User.created_at >= since).all()

    @staticmethod
    def last_login_stats(days: int = 30) -> Dict[str, Any]:
        """最近 N 天有过登录的用户数"""
        since = datetime.now(timezone.utc) - timedelta(days=days)
        cnt = User.query_active().filter(User.last_login_at >= since).count()
        return {"days": days, "active_user_count": cnt}
# endregion

# region Flask-Login 回调
# -------------------------------------------------
# Flask-Login 回调
# -------------------------------------------------
from apps import login_manager
@login_manager.user_loader
def user_loader(uid: int) -> Optional[User]:
    return UserService.get_by_id(uid, include_deleted=False)


@login_manager.request_loader
def request_loader(request) -> Optional[User]:
    username = request.form.get("username")
    if not username:
        return None
    users = UserService.find_by_filter(username=username, include_deleted=False)
    return users[0] if users else None
# endregion
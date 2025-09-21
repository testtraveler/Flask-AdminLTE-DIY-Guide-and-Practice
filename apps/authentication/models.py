# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

from flask_login import UserMixin
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from sqlalchemy import ForeignKey, String, Text, LargeBinary, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

from apps.models import BaseModel
from apps import db
from apps.authentication.utils import hash_pass


class Role(BaseModel, db.Model):
    """角色模型"""
    __tablename__ = 'roles'
    
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="角色名")
    description: Mapped[str] = mapped_column(Text, nullable=True, comment="描述")
    
    # 与用户的关系
    users: Mapped[list["User"]] = relationship("User", back_populates="role")
    
    def __repr__(self):
        return f'<Role {self.name}>'


class Group(BaseModel, db.Model):
    """用户组模型"""
    __tablename__ = 'groups'
    
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, comment="组名")
    description: Mapped[str] = mapped_column(Text, nullable=True, comment="描述")
    
    # 与用户的关系
    users: Mapped[list["User"]] = relationship("User", back_populates="group")
    
    def __repr__(self):
        return f'<Group {self.name}>'


class User(BaseModel, UserMixin, db.Model):
    """用户模型"""
    __tablename__ = 'users'

    username: Mapped[str] = mapped_column(String(64), unique=True, comment="用户名")
    email: Mapped[str] = mapped_column(String(64), unique=True, comment="邮箱")
    password: Mapped[bytes] = mapped_column(LargeBinary, comment="密码")
    phone: Mapped[str] = mapped_column(String(20), nullable=True, comment="手机号")
    bio: Mapped[str] = mapped_column(Text(), nullable=True, comment="个人简介")
    
    # 新增字段
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=True, comment="角色ID")
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=True, comment="用户组ID")
    last_login_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, comment="上次登录时间")
    
    # OAuth字段
    oauth_github: Mapped[str] = mapped_column(String(100), nullable=True, comment="GitHub OAuth ID")
    oauth_google: Mapped[str] = mapped_column(String(100), nullable=True, comment="Google OAuth ID")

    # 关系
    role: Mapped["Role"] = relationship("Role", back_populates="users")
    group: Mapped["Group"] = relationship("Group", back_populates="users")

    def __repr__(self):
        return str(self.username)

class OAuth(OAuthConsumerMixin, BaseModel, db.Model):
    __tablename__ = 'oauth'
    
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="cascade"), nullable=False)
    user: Mapped["User"] = relationship(User)
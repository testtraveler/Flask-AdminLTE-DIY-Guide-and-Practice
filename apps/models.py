# -*- encoding: utf-8 -*-
"""
模型基类定义
"""

from datetime import datetime, timezone
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime, func

from apps import db


class BaseModel():
    """所有模型的基类，包含公共字段和方法"""
    
    # 定义类型注解映射，确保所有模型使用相同的类型
    type_annotation_map = {
        datetime: DateTime(timezone=True)
    }
    
    # 公共字段
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        comment="更新时间"
    )
    deleted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=True,
        comment="软删除时间"
    )  # 软删除时间
    
    # 公共方法
    def save(self) -> None:
        """保存对象到数据库"""
        try:
            db.session.add(self)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            error = str(e.orig)
            raise IntegrityError(error, 422)
    
    def delete(self) -> None:
        """软删除：设置删除时间而不是真正删除记录"""
        try:
            self.deleted_at = datetime.now(timezone.utc)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            error = str(e.orig)
            raise IntegrityError(error, 422)
        
    def restore(self) -> None:
        """恢复软删除记录"""
        try:
            self.deleted_at = None
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            error = str(e.orig)
            raise IntegrityError(error, 422)
    
    def hard_delete(self) -> None:
        """硬删除：从数据库彻底删除记录"""
        try:
            db.session.delete(self)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            error = str(e.orig)
            raise IntegrityError(error, 422)
    
    @classmethod
    def query_active(cls):
        """返回未删除的记录查询"""
        return db.session.query(cls).filter(cls.deleted_at.is_(None))
    
    @classmethod
    def query_all(cls, include_deleted=False):
        """返回所有记录的查询，可选择是否包含已删除的记录"""
        query = db.session.query(cls)
        if not include_deleted:
            query = query.filter(cls.deleted_at.is_(None))
        return query
"""
服务层，提供业务逻辑，全部用类方法实现。
包含数据库操作的基础实现。
"""
from typing import List, Optional, Dict, Any, ClassVar, Set, Type
from datetime import datetime, timezone
from sqlalchemy.exc import (
    SQLAlchemyError,
    IntegrityError,
    DataError,
    OperationalError,
    ProgrammingError,
    NoResultFound,
    MultipleResultsFound
)
from sqlalchemy import or_
from apps import db
from apps.models import BaseModel
from apps.utils.logger import logger

# region 基础服务类
class BaseService:
    """
    基础服务类，提供通用的 CRUD（含批量）操作，全部用类方法实现。
    子类必须指定 model_class 属性。
    所有数据库操作都通过服务层方法完成，不直接暴露模型保存方法。
    """

    model_class: Type[BaseModel] = None

    # region 内部工具
    @classmethod
    def _check_model(cls):
        if cls.model_class is None:
            raise AttributeError("子类必须指定 model_class 属性")
        
    @classmethod
    def _save_object(cls, obj: BaseModel) -> BaseModel:
        """内部方法：保存对象到数据库"""
        try:
            db.session.add(obj)
            db.session.commit()
            return obj
        except IntegrityError as e:
            db.session.rollback()
            logger.exception("保存 %s 失败 - 完整性错误", cls.model_class.__name__)
            raise IntegrityError(f"保存 {cls.model_class.__name__} 失败: 数据完整性错误") from e
        except (DataError, OperationalError, ProgrammingError) as e:
            db.session.rollback()
            logger.exception("保存 %s 失败 - 数据库操作错误", cls.model_class.__name__)
            raise SQLAlchemyError(f"保存 {cls.model_class.__name__} 失败: 数据库操作错误") from e
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception("保存 %s 失败 - 数据库错误", cls.model_class.__name__)
            raise SQLAlchemyError(f"保存 {cls.model_class.__name__} 失败: 数据库错误") from e
        except Exception as e:
            db.session.rollback()
            logger.exception("保存 %s 失败 - 系统错误", cls.model_class.__name__)
            raise RuntimeError(f"保存 {cls.model_class.__name__} 失败: 系统错误") from e
        
    @classmethod
    def _delete_object(cls, obj: BaseModel) -> None:
        """内部方法：删除对象"""
        try:
            db.session.delete(obj)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            logger.exception("删除 %s 失败 - 完整性错误", cls.model_class.__name__)
            raise IntegrityError(f"删除 {cls.model_class.__name__} 失败: 数据完整性错误") from e
        except (DataError, OperationalError, ProgrammingError) as e:
            db.session.rollback()
            logger.exception("删除 %s 失败 - 数据库操作错误", cls.model_class.__name__)
            raise SQLAlchemyError(f"删除 {cls.model_class.__name__} 失败: 数据库操作错误") from e
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception("删除 %s 失败 - 数据库错误", cls.model_class.__name__)
            raise SQLAlchemyError(f"删除 {cls.model_class.__name__} 失败: 数据库错误") from e
        except Exception as e:
            db.session.rollback()
            logger.exception("删除 %s 失败 - 系统错误", cls.model_class.__name__)
            raise RuntimeError(f"删除 {cls.model_class.__name__} 失败: 系统错误") from e
    # endregion

    # region 查询
    @classmethod
    def get_all(cls, include_deleted: bool = False) -> List[BaseModel]:
        cls._check_model()
        try:
            return cls.model_class.query_all(include_deleted).all()
        except SQLAlchemyError as e:
            logger.exception("获取 %s 全部记录失败 - 数据库错误", cls.model_class.__name__)
            raise SQLAlchemyError(f"获取全部记录失败：数据库错误") from e
        except Exception as e:
            logger.exception("获取 %s 全部记录失败 - 系统错误", cls.model_class.__name__)
            raise RuntimeError(f"获取全部记录失败：系统错误") from e

    @classmethod
    def get_by_id(cls, id: int, include_deleted: bool = False) -> Optional[BaseModel]:
        cls._check_model()
        try:
            result = cls.model_class.query_all(include_deleted).filter_by(id=id).one_or_none()
            if result is None and not include_deleted:
                raise NoResultFound(f"{cls.model_class.__name__} ID={id} 不存在")
            return result
        except MultipleResultsFound as e:
            logger.exception("按 ID=%s 查询 %s 返回多个结果", id, cls.model_class.__name__)
            raise MultipleResultsFound(f"按 ID={id} 查询返回多个结果") from e
        except SQLAlchemyError as e:
            logger.exception("按 ID=%s 查询 %s 失败 - 数据库错误", id, cls.model_class.__name__)
            raise SQLAlchemyError(f"按 ID={id} 查询失败：数据库错误") from e
        except Exception as e:
            logger.exception("按 ID=%s 查询 %s 失败 - 系统错误", id, cls.model_class.__name__)
            raise RuntimeError(f"按 ID={id} 查询失败：系统错误") from e

    @classmethod
    def get_by_ids(cls, ids: List[int], include_deleted: bool = False) -> List[BaseModel]:
        cls._check_model()
        try:
            query = cls.model_class.query_all(include_deleted)
            return query.filter(cls.model_class.id.in_(ids)).all()
        except SQLAlchemyError as e:
            logger.exception("按 IDs=%s 查询 %s 失败 - 数据库错误", ids, cls.model_class.__name__)
            raise SQLAlchemyError(f"按 IDs={ids} 查询失败：数据库错误") from e
        except Exception as e:
            logger.exception("按 IDs=%s 查询 %s 失败 - 系统错误", ids, cls.model_class.__name__)
            raise RuntimeError(f"按 IDs={ids} 查询失败：系统错误") from e

    @classmethod
    def find_by_filter(cls, include_deleted: bool = False, **kwargs: Any) -> List[BaseModel]:
        cls._check_model()
        try:
            query = cls.model_class.query_all(include_deleted)
            for field, value in kwargs.items():
                if not hasattr(cls.model_class, field):
                    raise AttributeError(f"{cls.model_class.__name__} 没有字段 {field}")
                query = query.filter(getattr(cls.model_class, field) == value)
            return query.all()
        except AttributeError as e:
            logger.exception("字段不存在 %s，kwargs=%s", cls.model_class.__name__, kwargs)
            raise AttributeError(f"字段不存在：{str(e)}") from e
        except SQLAlchemyError as e:
            logger.exception("条件查询 %s 失败 - 数据库错误，kwargs=%s", cls.model_class.__name__, kwargs)
            raise SQLAlchemyError(f"条件查询失败：数据库错误") from e
        except Exception as e:
            logger.exception("条件查询 %s 失败 - 系统错误，kwargs=%s", cls.model_class.__name__, kwargs)
            raise RuntimeError(f"条件查询失败：系统错误") from e

    @classmethod
    def search(cls, search_term: str, fields: List[str], include_deleted: bool = False) -> List[BaseModel]:
        cls._check_model()
        try:
            query = cls.model_class.query_all(include_deleted)
            conditions = []
            for field in fields:
                if hasattr(cls.model_class, field):
                    conditions.append(getattr(cls.model_class, field).ilike(f'%{search_term}%'))
            if conditions:
                query = query.filter(or_(*conditions))
            return query.all()
        except SQLAlchemyError as e:
            logger.exception("搜索 %s 失败 - 数据库错误，term=%s，fields=%s", 
                          cls.model_class.__name__, search_term, fields)
            raise SQLAlchemyError(f"搜索失败：数据库错误") from e
        except Exception as e:
            logger.exception("搜索 %s 失败 - 系统错误，term=%s，fields=%s", 
                          cls.model_class.__name__, search_term, fields)
            raise RuntimeError(f"搜索失败：系统错误") from e
    # endregion
    
    # region 单条写操作
    @classmethod
    def create(cls, **kwargs: Any) -> BaseModel:
        """创建新记录"""
        cls._check_model()
        try:
            item = cls.model_class(**kwargs)
            return cls._save_object(item)
        except SQLAlchemyError as e:
            logger.exception("创建 %s 失败 - 数据库错误，data=%s", 
                          cls.model_class.__name__, kwargs)
            raise SQLAlchemyError(f"创建 {cls.model_class.__name__} 记录失败：数据库错误") from e
        except Exception as e:
            logger.exception("创建 %s 失败 - 系统错误，data=%s", 
                          cls.model_class.__name__, kwargs)
            raise RuntimeError(f"创建 {cls.model_class.__name__} 记录失败：系统错误") from e

    @classmethod
    def update(cls, id: int, **kwargs: Any) -> BaseModel:
        """更新记录"""
        cls._check_model()
        try:
            item = cls.get_by_id(id, include_deleted=True)
            if item is None:
                raise NoResultFound(f"{cls.model_class.__name__} ID={id} 不存在")

            for key, value in kwargs.items():
                if hasattr(item, key) and (not hasattr(item, 'readonly_fields') or key not in item.readonly_fields):
                    setattr(item, key, value)
                    
            return cls._save_object(item)
        except NoResultFound as e:
            raise NoResultFound(str(e)) from e
        except SQLAlchemyError as e:
            logger.exception("更新 %s ID=%s 失败 - 数据库错误，data=%s", 
                          cls.model_class.__name__, id, kwargs)
            raise SQLAlchemyError(f"更新 {cls.model_class.__name__} ID={id} 失败：数据库错误") from e
        except Exception as e:
            logger.exception("更新 %s ID=%s 失败 - 系统错误，data=%s", 
                          cls.model_class.__name__, id, kwargs)
            raise RuntimeError(f"更新 {cls.model_class.__name__} ID={id} 失败：系统错误") from e

    @classmethod
    def soft_delete(cls, id: int) -> BaseModel:
        """软删除记录"""
        cls._check_model()
        try:
            item = cls.get_by_id(id)
            if item is None:
                raise NoResultFound(f"{cls.model_class.__name__} ID={id} 不存在或已删除")

            item.deleted_at = datetime.now(timezone.utc)
            return cls._save_object(item)
        except NoResultFound as e:
            raise NoResultFound(str(e)) from e
        except SQLAlchemyError as e:
            logger.exception("软删除 %s ID=%s 失败 - 数据库错误", 
                          cls.model_class.__name__, id)
            raise SQLAlchemyError(f"软删除 {cls.model_class.__name__} ID={id} 失败：数据库错误") from e
        except Exception as e:
            logger.exception("软删除 %s ID=%s 失败 - 系统错误", 
                          cls.model_class.__name__, id)
            raise RuntimeError(f"软删除 {cls.model_class.__name__} ID={id} 失败：系统错误") from e

    @classmethod
    def hard_delete(cls, id: int) -> None:
        """硬删除记录"""
        cls._check_model()
        try:
            item = cls.get_by_id(id, include_deleted=True)
            if item is None:
                raise NoResultFound(f"{cls.model_class.__name__} ID={id} 不存在")

            cls._delete_object(item)
        except NoResultFound as e:
            raise NoResultFound(str(e)) from e
        except SQLAlchemyError as e:
            logger.exception("硬删除 %s ID=%s 失败 - 数据库错误", 
                          cls.model_class.__name__, id)
            raise SQLAlchemyError(f"硬删除 {cls.model_class.__name__} ID={id} 失败：数据库错误") from e
        except Exception as e:
            logger.exception("硬删除 %s ID=%s 失败 - 系统错误", 
                          cls.model_class.__name__, id)
            raise RuntimeError(f"硬删除 {cls.model_class.__name__} ID={id} 失败：系统错误") from e

    @classmethod
    def restore(cls, id: int) -> BaseModel:
        """恢复软删除的记录"""
        cls._check_model()
        try:
            item = cls.get_by_id(id, include_deleted=True)
            if item is None:
                raise NoResultFound(f"{cls.model_class.__name__} ID={id} 不存在")
            if item.deleted_at is None:
                raise ValueError(f"{cls.model_class.__name__} ID={id} 未被删除")

            item.deleted_at = None
            return cls._save_object(item)
        except (NoResultFound, ValueError) as e:
            raise type(e)(str(e)) from e
        except SQLAlchemyError as e:
            logger.exception("恢复 %s ID=%s 失败 - 数据库错误", 
                          cls.model_class.__name__, id)
            raise SQLAlchemyError(f"恢复 {cls.model_class.__name__} ID={id} 失败：数据库错误") from e
        except Exception as e:
            logger.exception("恢复 %s ID=%s 失败 - 系统错误", 
                          cls.model_class.__name__, id)
            raise RuntimeError(f"恢复 {cls.model_class.__name__} ID={id} 失败：系统错误") from e
    # endregion
    
    # region 批量写操作
    @classmethod
    def bulk_create(cls, items_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量创建记录"""
        cls._check_model()
        results = {'success': [], 'errors': []}
        
        for data in items_data:
            try:
                item = cls.model_class(**data)
                saved_item = cls._save_object(item)
                results['success'].append(saved_item)
            except IntegrityError as e:
                logger.warning("批量创建 %s 单条失败 - 完整性错误，data=%s", 
                            cls.model_class.__name__, data)
                results['errors'].append({
                    'data': data, 
                    'error': '数据完整性错误: ' + str(e)
                })
            except SQLAlchemyError as e:
                logger.warning("批量创建 %s 单条失败 - 数据库错误，data=%s", 
                            cls.model_class.__name__, data)
                results['errors'].append({
                    'data': data, 
                    'error': '数据库错误: ' + str(e)
                })
            except Exception as e:
                logger.warning("批量创建 %s 单条失败 - 系统错误，data=%s", 
                            cls.model_class.__name__, data)
                results['errors'].append({
                    'data': data, 
                    'error': '系统错误: ' + str(e)
                })
        
        logger.info("批量创建 %s 完成，成功 %s 条，失败 %s 条",
                  cls.model_class.__name__, len(results['success']), len(results['errors']))
        return results

    @classmethod
    def bulk_update(cls, ids: List[int], update_data: Dict[str, Any]) -> Dict[str, Any]:
        """批量更新记录"""
        cls._check_model()
        results = {'success': [], 'errors': []}
        
        try:
            items = cls.get_by_ids(ids, include_deleted=True)
            for item in items:
                try:
                    for key, value in update_data.items():
                        if hasattr(item, key) and (not hasattr(item, 'readonly_fields') or key not in item.readonly_fields):
                            setattr(item, key, value)
                    saved_item = cls._save_object(item)
                    results['success'].append(saved_item)
                except SQLAlchemyError as e:
                    logger.warning("批量更新 %s ID=%s 失败 - 数据库错误", 
                                cls.model_class.__name__, item.id)
                    results['errors'].append({
                        'id': item.id, 
                        'error': '数据库错误: ' + str(e)
                    })
                except Exception as e:
                    logger.warning("批量更新 %s ID=%s 失败 - 系统错误", 
                                cls.model_class.__name__, item.id)
                    results['errors'].append({
                        'id': item.id, 
                        'error': '系统错误: ' + str(e)
                    })
        except SQLAlchemyError as e:
            logger.exception("批量更新 %s 获取记录失败 - 数据库错误", 
                          cls.model_class.__name__)
            raise SQLAlchemyError(f"批量更新失败：获取记录时数据库错误") from e
        except Exception as e:
            logger.exception("批量更新 %s 获取记录失败 - 系统错误", 
                          cls.model_class.__name__)
            raise RuntimeError(f"批量更新失败：获取记录时系统错误") from e
        
        logger.info("批量更新 %s 完成，成功 %s 条，失败 %s 条",
                  cls.model_class.__name__, len(results['success']), len(results['errors']))
        return results

    @classmethod
    def bulk_soft_delete(cls, ids: List[int]) -> Dict[str, Any]:
        """批量软删除记录"""
        cls._check_model()
        results = {'success': [], 'errors': []}
        
        try:
            items = cls.get_by_ids(ids)
            exist_ids = {item.id for item in items}
            missing = set(ids) - exist_ids
            if missing:
                logger.warning("批量软删除 %s 时以下 ID 不存在或已删除：%s", 
                            cls.model_class.__name__, missing)

            for item in items:
                try:
                    item.deleted_at = datetime.now(timezone.utc)
                    saved_item = cls._save_object(item)
                    results['success'].append(saved_item.id)
                except SQLAlchemyError as e:
                    logger.warning("批量软删除 %s ID=%s 失败 - 数据库错误", 
                                cls.model_class.__name__, item.id)
                    results['errors'].append({
                        'id': item.id, 
                        'error': '数据库错误: ' + str(e)
                    })
                except Exception as e:
                    logger.warning("批量软删除 %s ID=%s 失败 - 系统错误", 
                                cls.model_class.__name__, item.id)
                    results['errors'].append({
                        'id': item.id, 
                        'error': '系统错误: ' + str(e)
                    })
        except SQLAlchemyError as e:
            logger.exception("批量软删除 %s 获取记录失败 - 数据库错误", 
                          cls.model_class.__name__)
            raise SQLAlchemyError(f"批量软删除失败：获取记录时数据库错误") from e
        except Exception as e:
            logger.exception("批量软删除 %s 获取记录失败 - 系统错误", 
                          cls.model_class.__name__)
            raise RuntimeError(f"批量软删除失败：获取记录时系统错误") from e
        
        logger.info("批量软删除 %s 完成，成功 %s 条，失败 %s 条",
                  cls.model_class.__name__, len(results['success']), len(results['errors']))
        return results

    @classmethod
    def bulk_hard_delete(cls, ids: List[int]) -> Dict[str, Any]:
        """批量硬删除记录"""
        cls._check_model()
        results = {'success': [], 'errors': []}
        
        try:
            items = cls.get_by_ids(ids, include_deleted=True)
            for item in items:
                try:
                    cls._delete_object(item)
                    results['success'].append(item.id)
                except SQLAlchemyError as e:
                    logger.warning("批量硬删除 %s ID=%s 失败 - 数据库错误", 
                                cls.model_class.__name__, item.id)
                    results['errors'].append({
                        'id': item.id, 
                        'error': '数据库错误: ' + str(e)
                    })
                except Exception as e:
                    logger.warning("批量硬删除 %s ID=%s 失败 - 系统错误", 
                                cls.model_class.__name__, item.id)
                    results['errors'].append({
                        'id': item.id, 
                        'error': '系统错误: ' + str(e)
                    })
        except SQLAlchemyError as e:
            logger.exception("批量硬删除 %s 获取记录失败 - 数据库错误", 
                          cls.model_class.__name__)
            raise SQLAlchemyError(f"批量硬删除失败：获取记录时数据库错误") from e
        except Exception as e:
            logger.exception("批量硬删除 %s 获取记录失败 - 系统错误", 
                          cls.model_class.__name__)
            raise RuntimeError(f"批量硬删除失败：获取记录时系统错误") from e
        
        logger.info("批量硬删除 %s 完成，成功 %s 条，失败 %s 条",
                  cls.model_class.__name__, len(results['success']), len(results['errors']))
        return results

    @classmethod
    def bulk_restore(cls, ids: List[int]) -> Dict[str, Any]:
        """批量恢复记录"""
        cls._check_model()
        results = {'success': [], 'errors': []}
        
        try:
            items = cls.get_by_ids(ids, include_deleted=True)
            for item in items:
                try:
                    if item.deleted_at is not None:
                        item.deleted_at = None
                        saved_item = cls._save_object(item)
                        results['success'].append(saved_item.id)
                except SQLAlchemyError as e:
                    logger.warning("批量恢复 %s ID=%s 失败 - 数据库错误", 
                                cls.model_class.__name__, item.id)
                    results['errors'].append({
                        'id': item.id, 
                        'error': '数据库错误: ' + str(e)
                    })
                except Exception as e:
                    logger.warning("批量恢复 %s ID=%s 失败 - 系统错误", 
                                cls.model_class.__name__, item.id)
                    results['errors'].append({
                        'id': item.id, 
                        'error': '系统错误: ' + str(e)
                    })
        except SQLAlchemyError as e:
            logger.exception("批量恢复 %s 获取记录失败 - 数据库错误", 
                          cls.model_class.__name__)
            raise SQLAlchemyError(f"批量恢复失败：获取记录时数据库错误") from e
        except Exception as e:
            logger.exception("批量恢复 %s 获取记录失败 - 系统错误", 
                          cls.model_class.__name__)
            raise RuntimeError(f"批量恢复失败：获取记录时系统错误") from e
        
        logger.info("批量恢复 %s 完成，成功 %s 条，失败 %s 条",
                  cls.model_class.__name__, len(results['success']), len(results['errors']))
        return results
    # endregion

# endregion

# region 白名单服务基类
class PromptService(BaseService):
    """
    在子类中声明：
        writable_fields: 允许 create / update 的字段
        searchable_fields: 允许 search 的字段
    基类自动完成校验 + 日志
    """
    writable_fields: ClassVar[Set[str]] = set()
    searchable_fields: ClassVar[Set[str]] = set()
    
    # ---------- 覆写基类方法 ----------
    @classmethod
    def create(cls, **kwargs: Any) -> BaseModel:
        """创建记录（字段白名单验证）"""
        cls._assert_fields_allowed(kwargs, cls.writable_fields, "create")
        return super().create(**kwargs)
    
    @classmethod
    def update(cls, id: int, **kwargs: Any) -> BaseModel:
        """更新记录（字段白名单验证）"""
        cls._assert_fields_allowed(kwargs, cls.writable_fields, "update")
        return super().update(id, **kwargs)
    
    @classmethod
    def search(cls, search_term: str, fields: List[str], include_deleted: bool = False) -> List[BaseModel]:
        """搜索记录（字段白名单验证）"""
        illegal = set(fields) - cls.searchable_fields
        if illegal:
            raise ValueError(f"{cls.model_class.__name__} 不允许搜索字段: {illegal}")
        return super().search(search_term, fields, include_deleted)
    
    # ---------- 内部工具 ----------
    @classmethod
    def _assert_fields_allowed(cls, kwargs: Dict[str, Any], allowed: Set[str], action: str) -> None:
        """字段白名单验证"""
        illegal = set(kwargs) - allowed
        if illegal:
            raise AttributeError(f"{cls.model_class.__name__} 不允许{action}字段: {illegal}")
# endregion

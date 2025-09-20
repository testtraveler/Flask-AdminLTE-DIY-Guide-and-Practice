"""
服务层，提供业务逻辑，全部用类方法实现。
"""
from typing import List, Optional, Dict, Any, ClassVar, Set, Type
from sqlalchemy import or_
from apps.models import BaseModel
from apps.exceptions.service_exception import *
from apps.utils.logger import logger


# region 基础服务类
class BaseService:
    """
    基础服务类，提供通用的 CRUD（含批量）操作，全部用类方法实现。
    子类必须指定 model_class 属性。
    """

    model_class: Type[BaseModel] = None

    # region 内部工具
    @classmethod
    def _check_model(cls):
        if cls.model_class is None:
            raise ModelNotSetException("子类必须指定 model_class 属性")

    # endregion

    # region 查询
    @classmethod
    def get_all(cls, include_deleted: bool = False) -> List[BaseModel]:
        cls._check_model()
        try:
            return cls.model_class.query_all(include_deleted).all()
        except Exception as e:
            logger.exception("获取 %s 全部记录失败", cls.model_class.__name__)
            raise BaseServiceException(f"获取全部记录失败：{e}")

    @classmethod
    def get_by_id(cls, id: int, include_deleted: bool = False) -> Optional[BaseModel]:
        cls._check_model()
        try:
            return cls.model_class.query_all(include_deleted).filter_by(id=id).first()
        except Exception as e:
            logger.exception("按 ID=%s 查询 %s 失败", id, cls.model_class.__name__)
            raise BaseServiceException(f"按 ID={id} 查询失败：{e}")

    @classmethod
    def get_by_ids(cls, ids: List[int], include_deleted: bool = False) -> List[BaseModel]:
        cls._check_model()
        try:
            query = cls.model_class.query_all(include_deleted)
            return query.filter(cls.model_class.id.in_(ids)).all()
        except Exception as e:
            logger.exception("按 IDs=%s 查询 %s 失败", ids, cls.model_class.__name__)
            raise BaseServiceException(f"按 IDs={ids} 查询失败：{e}")

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
        except AttributeError:
            # 字段不存在属于开发期错误，直接抛
            logger.exception("字段不存在 %s，kwargs=%s", cls.model_class.__name__, kwargs)
            raise
        except Exception as e:
            logger.exception("条件查询 %s 失败，kwargs=%s", cls.model_class.__name__, kwargs)
            raise BaseServiceException(f"条件查询失败：{e}")

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
        except Exception as e:
            logger.exception("搜索 %s 失败，term=%s，fields=%s", cls.model_class.__name__, search_term, fields)
            raise BaseServiceException(f"搜索失败：{e}")

    # endregion

    # region 单条写
    @classmethod
    def create(cls, **kwargs: Any) -> BaseModel:
        cls._check_model()
        try:
            item = cls.model_class(**kwargs)
            item.save()
            logger.info("创建 %s 成功，ID=%s", cls.model_class.__name__, item.id)
            return item
        except Exception as e:
            logger.exception("创建 %s 失败，data=%s", cls.model_class.__name__, kwargs)
            raise CreateFailedException(f"创建 {cls.model_class.__name__} 记录失败：{e}")

    @classmethod
    def update(cls, id: int, **kwargs: Any) -> BaseModel:
        cls._check_model()
        item = cls.get_by_id(id, include_deleted=True)
        if not item:
            raise RecordNotFoundException(f"{cls.model_class.__name__} ID={id} 不存在")

        try:
            for key, value in kwargs.items():
                if hasattr(item, key) and (not hasattr(item, 'readonly_fields') or key not in item.readonly_fields):
                    setattr(item, key, value)
            item.save()
            logger.info("更新 %s 成功，ID=%s", cls.model_class.__name__, id)
            return item
        except Exception as e:
            logger.exception("更新 %s ID=%s 失败，data=%s", cls.model_class.__name__, id, kwargs)
            raise UpdateFailedException(f"更新 {cls.model_class.__name__} ID={id} 失败：{e}")

    @classmethod
    def soft_delete(cls, id: int) -> BaseModel:
        cls._check_model()
        item = cls.get_by_id(id)  # 默认不带已删除
        if not item:
            raise RecordNotFoundException(f"{cls.model_class.__name__} ID={id} 不存在或已删除")
        try:
            item.delete()
            logger.info("软删除 %s 成功，ID=%s", cls.model_class.__name__, id)
            return item
        except Exception as e:
            logger.exception("软删除 %s ID=%s 失败", cls.model_class.__name__, id)
            raise DeleteFailedException(f"软删除 {cls.model_class.__name__} ID={id} 失败：{e}")

    @classmethod
    def hard_delete(cls, id: int) -> BaseModel:
        cls._check_model()
        item = cls.get_by_id(id, include_deleted=True)
        if not item:
            raise RecordNotFoundException(f"{cls.model_class.__name__} ID={id} 不存在")
        try:
            item.hard_delete()
            logger.info("硬删除 %s 成功，ID=%s", cls.model_class.__name__, id)
            return item
        except Exception as e:
            logger.exception("硬删除 %s ID=%s 失败", cls.model_class.__name__, id)
            raise DeleteFailedException(f"硬删除 {cls.model_class.__name__} ID={id} 失败：{e}")

    @classmethod
    def restore(cls, id: int) -> BaseModel:
        cls._check_model()
        item = cls.get_by_id(id, include_deleted=True)
        if not item:
            raise RecordNotFoundException(f"{cls.model_class.__name__} ID={id} 不存在")
        if item.deleted_at is None:
            raise RecordNotDeletedException(f"{cls.model_class.__name__} ID={id} 未被删除")
        try:
            item.restore()
            logger.info("恢复 %s 成功，ID=%s", cls.model_class.__name__, id)
            return item
        except Exception as e:
            logger.exception("恢复 %s ID=%s 失败", cls.model_class.__name__, id)
            raise RestoreFailedException(f"恢复 {cls.model_class.__name__} ID={id} 失败：{e}")

    # endregion

    # region 批量写
    @classmethod
    def bulk_create(cls, items_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        cls._check_model()
        results = {'success': [], 'errors': []}
        for data in items_data:
            try:
                item = cls.model_class(**data)
                item.save()
                results['success'].append(item)
            except Exception as e:
                logger.warning("批量创建 %s 单条失败，data=%s，error=%s", cls.model_class.__name__, data, e)
                results['errors'].append({'data': data, 'error': str(e)})
        logger.info("批量创建 %s 完成，成功 %s 条，失败 %s 条",
                    cls.model_class.__name__, len(results['success']), len(results['errors']))
        return results

    @classmethod
    def bulk_update(cls, ids: List[int], update_data: Dict[str, Any]) -> Dict[str, Any]:
        cls._check_model()
        results = {'success': [], 'errors': []}
        items = cls.get_by_ids(ids, include_deleted=True)
        for item in items:
            try:
                for key, value in update_data.items():
                    if hasattr(item, key) and (not hasattr(item, 'readonly_fields') or key not in item.readonly_fields):
                        setattr(item, key, value)
                item.save()
                results['success'].append(item)
            except Exception as e:
                logger.warning("批量更新 %s ID=%s 失败：%s", cls.model_class.__name__, item.id, e)
                results['errors'].append({'id': item.id, 'error': str(e)})
        logger.info("批量更新 %s 完成，成功 %s 条，失败 %s 条",
                    cls.model_class.__name__, len(results['success']), len(results['errors']))
        return results

    @classmethod
    def bulk_soft_delete(cls, ids: List[int]) -> Dict[str, Any]:
        cls._check_model()
        results = {'success': [], 'errors': []}
        items = cls.get_by_ids(ids)  # 不带已删除
        exist_ids = {item.id for item in items}
        missing = set(ids) - exist_ids
        if missing:
            logger.warning("批量软删除 %s 时以下 ID 不存在或已删除：%s", cls.model_class.__name__, missing)

        for item in items:
            try:
                item.delete()
                results['success'].append(item.id)
            except Exception as e:
                logger.warning("批量软删除 %s ID=%s 失败：%s", cls.model_class.__name__, item.id, e)
                results['errors'].append({'id': item.id, 'error': str(e)})
        logger.info("批量软删除 %s 完成，成功 %s 条，失败 %s 条",
                    cls.model_class.__name__, len(results['success']), len(results['errors']))
        return results

    @classmethod
    def bulk_hard_delete(cls, ids: List[int]) -> Dict[str, Any]:
        cls._check_model()
        results = {'success': [], 'errors': []}
        items = cls.get_by_ids(ids, include_deleted=True)
        for item in items:
            try:
                item.hard_delete()
                results['success'].append(item.id)
            except Exception as e:
                logger.warning("批量硬删除 %s ID=%s 失败：%s", cls.model_class.__name__, item.id, e)
                results['errors'].append({'id': item.id, 'error': str(e)})
        logger.info("批量硬删除 %s 完成，成功 %s 条，失败 %s 条",
                    cls.model_class.__name__, len(results['success']), len(results['errors']))
        return results

    @classmethod
    def bulk_restore(cls, ids: List[int]) -> Dict[str, Any]:
        cls._check_model()
        results = {'success': [], 'errors': []}
        items = cls.get_by_ids(ids, include_deleted=True)
        for item in items:
            try:
                if item.deleted_at is not None:
                    item.restore()
                    results['success'].append(item.id)
            except Exception as e:
                logger.warning("批量恢复 %s ID=%s 失败：%s", cls.model_class.__name__, item.id, e)
                results['errors'].append({'id': item.id, 'error': str(e)})
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

    # ---------- 覆写基类四个关键入口 ----------
    @classmethod
    def create(cls, **kwargs: Any) -> BaseModel:
        cls._assert_fields_allowed(kwargs, cls.writable_fields, "create")
        return super().create(**kwargs)

    @classmethod
    def update(cls, id: int, **kwargs: Any) -> BaseModel:
        cls._assert_fields_allowed(kwargs, cls.writable_fields, "update")
        return super().update(id, **kwargs)

    @classmethod
    def search(cls, search_term: str, fields: List[str], include_deleted: bool = False) -> List[BaseModel]:
        # 只允许在白名单里搜索
        illegal = set(fields) - cls.searchable_fields
        if illegal:
            raise ValueError(f"{cls.model_class.__name__} 不允许搜索字段: {illegal}")
        return super().search(search_term, fields, include_deleted)

    # ---------- 内部工具 ----------
    @classmethod
    def _assert_fields_allowed(cls, kwargs: Dict[str, Any], allowed: Set[str], action: str) -> None:
        illegal = set(kwargs) - allowed
        if illegal:
            raise AttributeError(f"{cls.model_class.__name__} 不允许{action}字段: {illegal}")
# endregion
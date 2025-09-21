"""
服务层，提供业务逻辑，全部用类方法实现。
包含数据库操作的基础实现。
"""
from typing import List, Optional, Dict, Any, ClassVar, Set, Type, Generic, TypeVar
from pydantic import BaseModel as PydanticBaseModel  # 区分SQLAlchemy和Pydantic的BaseModel
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
from sqlalchemy.orm import load_only, Query
from apps import db
from apps.models import BaseModel
from apps.globals import logger
print('logger is', logger)

# 定义Schema类型变量
CreateSchemaT = TypeVar('CreateSchemaT', bound=PydanticBaseModel)
UpdateSchemaT = TypeVar('UpdateSchemaT', bound=PydanticBaseModel)
ResponseSchemaT = TypeVar('ResponseSchemaT', bound=PydanticBaseModel)

# region 基础服务类
class BaseService(Generic[CreateSchemaT, UpdateSchemaT, ResponseSchemaT]):
    """
    基础服务类，提供通用的 CRUD（含批量）操作，全部用类方法实现。
    子类必须指定 model_class、create_schema、update_schema、response_schema 属性。
    所有数据库操作都通过服务层方法完成，不直接暴露模型保存方法。
    通过Schema实现输入数据校验和输出数据格式化。
    """
    model_class: Type[BaseModel] = None
    create_schema: Type[CreateSchemaT] = None  # 子类需指定创建Schema
    update_schema: Type[UpdateSchemaT] = None  # 子类需指定更新Schema
    response_schema: Type[ResponseSchemaT] = None  # 子类需指定响应Schema
    
    # region 内部工具
    @classmethod
    def _check_model(cls):
        if cls.model_class is None:
            raise AttributeError("子类必须指定 model_class 属性")
        
    @classmethod
    def _check_schema(cls):
        """检查Schema是否已正确指定"""
        if not all([cls.create_schema, cls.update_schema, cls.response_schema]):
            raise AttributeError("子类必须指定 create_schema、update_schema、response_schema 属性")
        
    @classmethod
    def _convert_to_response(
        cls, 
        obj: BaseModel, 
        fields_response: Optional[List[str]] = None
    ) -> ResponseSchemaT:
        """将模型对象转换为响应Schema，支持动态子类"""
        cls._check_schema()
        if fields_response:
            DynamicSchema = cls.response_schema.with_fields(fields_response)
            return DynamicSchema.model_validate(obj)
        return cls.response_schema.model_validate(obj)

    @classmethod
    def _convert_to_response_list(
        cls, 
        objs: List[BaseModel], 
        fields_response: Optional[List[str]] = None
    ) -> List[ResponseSchemaT]:
        """将模型对象列表转换为响应Schema列表，支持动态子类"""
        cls._check_schema()
        if fields_response:
            DynamicSchema = cls.response_schema.with_fields(fields_response)
            return [DynamicSchema.model_validate(obj) for obj in objs]
        return [cls.response_schema.model_validate(obj) for obj in objs]
    
    # endregion
    # region 内部数据库单条操作封装
    @classmethod
    def _create_object(cls, data: Dict ,fields_response: Optional[List[str]] = ['id']) -> ResponseSchemaT:
        """内部方法：创建新对象并保存到数据库"""
        cls._check_model()
        cls._check_schema()
        try:
            schema_obj = cls.create_schema.model_validate(data)
            orm_obj = cls.model_class(**schema_obj.model_dump(exclude_unset=True))
            db.session.add(orm_obj)
            db.session.commit()
            logger.info("创建 %s id=%s 成功", cls.model_class.__name__, orm_obj.id)
            return cls._convert_to_response(orm_obj, fields_response)
        except IntegrityError as e:
            db.session.rollback()
            logger.exception("创建 %s 失败 - 完整性错误", cls.model_class.__name__)
            raise IntegrityError(f"创建 {cls.model_class.__name__} 失败: 数据完整性错误") from e
        except (DataError, OperationalError, ProgrammingError) as e:
            db.session.rollback()
            logger.exception("创建 %s 失败 - 数据库操作错误", cls.model_class.__name__)
            raise SQLAlchemyError(f"创建 {cls.model_class.__name__} 失败: 数据库操作错误") from e
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception("创建 %s 失败 - 数据库错误", cls.model_class.__name__)
            raise SQLAlchemyError(f"创建 {cls.model_class.__name__} 失败: 数据库错误") from e
        except Exception as e:
            db.session.rollback()
            logger.exception("创建 %s 失败 - 系统错误", cls.model_class.__name__)
            
    @classmethod
    def _delete_object(cls, id: int, fields_response: Optional[List[str]] = ['id']) -> ResponseSchemaT:
        """内部方法：删除对象"""
        cls._check_model()
        cls._check_schema()
        try:
            obj = db.session.query(cls.model_class).filter_by(id=id).one_or_none()
            if obj is None:
                raise NoResultFound(f"{cls.model_class.__name__} id={id} 不存在")
            db.session.delete(obj)
            db.session.commit()
            logger.info("删除 %s id=%s 成功", cls.model_class.__name__, obj.id)
            return cls._convert_to_response(obj, fields_response)
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
        
    @classmethod
    def _update_object(cls, id: int, data: Dict[str, Any], fields_response: Optional[List[str]] = ['id']) -> ResponseSchemaT:
        """内部方法：更新对象并保存到数据库"""
        cls._check_model()
        cls._check_schema()
        try:
            obj = db.session.query(cls.model_class).filter_by(id=id).one_or_none()
            if obj is None:
                raise NoResultFound(f"{cls.model_class.__name__} id={id} 不存在")
            update_data = cls.update_schema.model_validate(data)
            for k, v in update_data.items():
                setattr(obj, k, v)
            db.session.merge(obj, load=False)  # 不考虑先查最新再合并，因为事先保证传入的obj一定是存在且最新的
            db.session.commit()
            logger.info("更新 %s id=%s 成功", cls.model_class.__name__, obj.id)
            return cls._convert_to_response(obj, fields_response)
        except IntegrityError as e:
            db.session.rollback()
            logger.exception("更新 %s 失败 - 完整性错误", cls.model_class.__name__)
            raise IntegrityError(f"更新 {cls.model_class.__name__} 失败: 数据完整性错误") from e
        except (DataError, OperationalError, ProgrammingError) as e:
            db.session.rollback()
            logger.exception("更新 %s 失败 - 数据库操作错误", cls.model_class.__name__)
            raise SQLAlchemyError(f"更新 {cls.model_class.__name__} 失败: 数据库操作错误") from e
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception("更新 %s 失败 - 数据库错误", cls.model_class.__name__)
            raise SQLAlchemyError(f"更新 {cls.model_class.__name__} 失败: 数据库错误") from e
        except Exception as e:
            db.session.rollback()
            logger.exception("更新 %s 失败 - 系统错误", cls.model_class.__name__)
            raise RuntimeError(f"更新 {cls.model_class.__name__} 失败: 系统错误") from e
        
    @classmethod
    def _save_object(cls, obj: BaseModel, fields_response: Optional[List[str]] = ['id']) -> ResponseSchemaT:
        """内部方法：仅保存修改后的已有对象到数据库"""
        cls._check_model()
        cls._check_schema()
        try:
            db.session.merge(obj, load=False)
            db.session.commit()
            logger.info("保存 %s id=%s 成功", cls.model_class.__name__, obj.id)
            return cls._convert_to_response(obj, fields_response)
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
    # endregion
    # region 内部数据库批量操作封装
    @classmethod
    def _create_objects(cls, data: List[Dict[str, Any]], batch_size: int = 1000) -> None:
        """内部方法：批量创建新对象并保存到数据库"""
        cls._check_model()
        cls._check_schema()
        def _batch_create(data, batch_size=1000):
            for i in range(0, len(data), batch_size):
                try:
                    schema_objs = [cls.create_schema.model_validate(d) for d in data[i:i+batch_size]]
                    orm_objs = [cls.model_class(**schema_obj.model_dump(exclude_unset=True)) for schema_obj in schema_objs]
                    db.session.add_all(orm_objs)
                    db.session.commit()
                    logger.info("[%s 到 %s] 批量创建 %s 成功", i, i+batch_size, cls.model_class.__name__)
                except IntegrityError as e:
                    db.session.rollback()
                    logger.exception("[%s 到 %s] 批量创建 %s 失败 - 完整性错误", i, i+batch_size, cls.model_class.__name__)
                    raise IntegrityError(f"批量创建 {cls.model_class.__name__} 失败: 数据完整性错误") from e
                except (DataError, OperationalError, ProgrammingError) as e:
                    db.session.rollback()
                    logger.exception("[%s 到 %s] 批量创建 %s 失败 - 数据库操作错误", i, i+batch_size, cls.model_class.__name__)
                    raise SQLAlchemyError(f"批量创建 {cls.model_class.__name__} 失败: 数据库操作错误") from e
                except SQLAlchemyError as e:
                    db.session.rollback()
                    logger.exception("[%s 到 %s] 批量创建 %s 失败 - 数据库错误", i, i+batch_size, cls.model_class.__name__)
                    raise SQLAlchemyError(f"批量创建 {cls.model_class.__name__} 失败: 数据库错误") from e
                except Exception as e:
                    db.session.rollback()
                    logger.exception("[%s 到 %s] 批量创建 %s 失败 - 系统错误", i, i+batch_size, cls.model_class.__name__)
                    raise RuntimeError(f"批量创建 {cls.model_class.__name__} 失败: 系统错误") from e
        try:
            _batch_create(data, batch_size)
            logger.info("批量创建 %s 成功", cls.model_class.__name__)
        except Exception as e:
            logger.exception("批量创建 %s 失败 - 系统错误", cls.model_class.__name__)
            raise RuntimeError(f"批量创建 {cls.model_class.__name__} 失败: 系统错误") from e
    
    @classmethod
    def _delete_objects(cls, ids: List[int], batch_size: int = 1000) -> None:
        """内部方法：批量删除对象"""
        cls._check_model()
        cls._check_schema()
        def _batch_delete(ids, batch_size=1000):
            for i in range(0, len(ids), batch_size):
                try:
                    db.session.query(cls.model_class).filter(cls.model_class.id.in_(ids[i:i+batch_size])).delete()
                    db.session.commit()
                    logger.info("[%s 到 %s] 批量删除 %s 成功", i, i+batch_size, cls.model_class.__name__)
                except IntegrityError as e:
                    db.session.rollback()
                    logger.exception("[%s 到 %s] 批量删除 %s 失败 - 完整性错误", i, i+batch_size, cls.model_class.__name__)
                    raise IntegrityError(f"批量删除 {cls.model_class.__name__} 失败: 数据完整性错误") from e
                except (DataError, OperationalError, ProgrammingError) as e:
                    db.session.rollback()
                    logger.exception("[%s 到 %s] 批量删除 %s 失败 - 数据库操作错误", i, i+batch_size, cls.model_class.__name__)
                    raise SQLAlchemyError(f"批量删除 {cls.model_class.__name__} 失败: 数据库操作错误") from e
                except SQLAlchemyError as e:
                    db.session.rollback()
                    logger.exception("[%s 到 %s] 批量删除 %s 失败 - 数据库错误", i, i+batch_size, cls.model_class.__name__)
                    raise SQLAlchemyError(f"批量删除 {cls.model_class.__name__} 失败: 数据库错误") from e
                except Exception as e:
                    db.session.rollback()
                    logger.exception("[%s 到 %s] 批量删除 %s 失败 - 系统错误", i, i+batch_size, cls.model_class.__name__)
                    raise RuntimeError(f"批量删除 {cls.model_class.__name__} 失败: 系统错误") from e
        try:
            _batch_delete(ids, batch_size)
            logger.info("批量删除 %s 成功", cls.model_class.__name__)
        except Exception as e:
            logger.exception("批量删除 %s 失败 - 系统错误", cls.model_class.__name__)
            raise RuntimeError(f"批量删除 {cls.model_class.__name__} 失败: 系统错误") from e
    
    @classmethod
    def _update_objects(cls, ids: List[int], data: List[Dict[str, Any]], batch_size: int = 1000) -> None:
        """内部方法：批量更新对象并保存到数据库"""
        cls._check_model()
        cls._check_schema()
        def _batch_update(ids, data, batch_size=1000):
            for i in range(0, len(data), batch_size):
                try:
                    objs = db.session.query(cls.model_class).filter(cls.model_class.id.in_(ids[i:i+batch_size])).all()
                    update_data = [cls.update_schema.model_validate(d) for d in data[i:i+batch_size]]
                    for obj, update_d in zip(objs, update_data):
                        for k, v in update_d.items():
                            setattr(obj, k, v)
                    db.session.bulk_save_objects(objs)
                    db.session.commit()
                    logger.info("[%s 到 %s] 批量更新 %s 成功", i, i+batch_size, cls.model_class.__name__)
                except IntegrityError as e:
                    db.session.rollback()
                    logger.exception("[%s 到 %s] 批量更新 %s 失败 - 完整性错误", i, i+batch_size, cls.model_class.__name__)
                    raise IntegrityError(f"批量更新 {cls.model_class.__name__} 失败: 数据完整性错误") from e
                except (DataError, OperationalError, ProgrammingError) as e:
                    db.session.rollback()
                    logger.exception("[%s 到 %s] 批量更新 %s 失败 - 数据库操作错误", i, i+batch_size, cls.model_class.__name__)
                    raise SQLAlchemyError(f"批量更新 {cls.model_class.__name__} 失败: 数据库操作错误") from e
                except SQLAlchemyError as e:
                    db.session.rollback()
                    logger.exception("[%s 到 %s] 批量更新 %s 失败 - 数据库错误", i, i+batch_size, cls.model_class.__name__)
                    raise SQLAlchemyError(f"批量更新 {cls.model_class.__name__} 失败: 数据库错误") from e
                except Exception as e:
                    db.session.rollback()
                    logger.exception("[%s 到 %s] 批量更新 %s 失败 - 系统错误", i, i+batch_size, cls.model_class.__name__)
                    raise RuntimeError(f"批量更新 {cls.model_class.__name__} 失败: 系统错误") from e
        try:
            _batch_update(ids, data, batch_size)
            logger.info("批量更新 %s 成功", cls.model_class.__name__)
        except Exception as e:
            logger.exception("批量更新 %s 失败 - 系统错误", cls.model_class.__name__)
            raise RuntimeError(f"批量更新 {cls.model_class.__name__} 失败: 系统错误") from e
    
    @classmethod
    def _save_objects(cls, objs: List[BaseModel], batch_size: int = 1000) -> None:
        """内部方法：仅批量保存最新的对象到数据库"""
        cls._check_model()
        cls._check_schema()
        def _batch_save(objs, batch_size=1000):
            for i in range(0, len(objs), batch_size):
                try:
                    db.session.bulk_save_objects(objs[i:i+batch_size])
                    db.session.commit()
                    logger.info("[%s 到 %s] 批量保存 %s 成功", i, i+batch_size, cls.model_class.__name__)
                except IntegrityError as e:
                    db.session.rollback()
                    logger.exception("[%s 到 %s] 批量保存 %s 失败 - 完整性错误", i, i+batch_size, cls.model_class.__name__)
                    raise IntegrityError(f"批量保存 {cls.model_class.__name__} 失败: 数据完整性错误") from e
                except (DataError, OperationalError, ProgrammingError) as e:
                    db.session.rollback()
                    logger.exception("[%s 到 %s] 批量保存 %s 失败 - 数据库操作错误", i, i+batch_size, cls.model_class.__name__)
                    raise SQLAlchemyError(f"批量保存 {cls.model_class.__name__} 失败: 数据库操作错误") from e
                except SQLAlchemyError as e:
                    db.session.rollback()
                    logger.exception("[%s 到 %s] 批量保存 %s 失败 - 数据库错误", i, i+batch_size, cls.model_class.__name__)
                    raise SQLAlchemyError(f"批量保存 {cls.model_class.__name__} 失败: 数据库错误") from e
                except Exception as e:
                    db.session.rollback()
                    logger.exception("[%s 到 %s] 批量保存 %s 失败 - 系统错误", i, i+batch_size, cls.model_class.__name__)
                    raise RuntimeError(f"批量保存 {cls.model_class.__name__} 失败: 系统错误") from e
        try:
            _batch_save(objs, batch_size)
            logger.info("批量保存 %s 成功", cls.model_class.__name__)
        except Exception as e:
            logger.exception("批量保存 %s 失败 - 系统错误", cls.model_class.__name__)
            raise RuntimeError(f"批量保存 {cls.model_class.__name__} 失败: 系统错误") from e
    # endregion
    # region 内部数据库查询方法封装
    @classmethod
    def _query_active(cls, fields_response: Optional[List[str]] = None) -> Query:
        """返回未删除的记录查询"""
        cls._check_model()
        cls._check_schema()
        return db.session.query(cls.model_class).filter(cls.model_class.deleted_at.is_(None)).options(load_only(*fields_response))

    @classmethod
    def _query_all(cls, include_deleted: bool = False, fields_response: Optional[List[str]] = None) -> Query:
        """返回所有记录的查询，可选择是否包含已删除的记录"""
        cls._check_model()
        cls._check_schema()
        if fields_response is None:
            query = db.session.query(cls.model_class)
            if not include_deleted:
                query = db.session.query(cls.model_class).filter(cls.model_class.deleted_at.is_(None))
        else:
            query = db.session.query(cls.model_class).options(load_only(*fields_response))
            if not include_deleted:
                query = db.session.query(cls.model_class).filter(cls.model_class.deleted_at.is_(None)).options(load_only(*fields_response))
        return query
    # endregion

    # region 查询
    @classmethod
    def get_all(cls, include_deleted: bool = False, fields_response: Optional[List[str]] = None) -> List[ResponseSchemaT]:
        """获取全部记录"""
        try:
            items = cls._query_all(include_deleted, fields_response).all()
            return cls._convert_to_response_list(items, fields_response)
        except SQLAlchemyError as e:
            logger.exception("获取 %s 全部记录失败 - 数据库错误", cls.model_class.__name__)
            raise SQLAlchemyError(f"获取全部记录失败：数据库错误") from e
        except Exception as e:
            logger.exception("获取 %s 全部记录失败 - 系统错误", cls.model_class.__name__)
            raise RuntimeError(f"获取全部记录失败：系统错误") from e

    @classmethod
    def get_by_id(cls, id: int, include_deleted: bool = False, fields_response: Optional[List[str]] = None) -> Optional[ResponseSchemaT]:
        """按 ID 查询记录"""
        try:
            result = cls._query_all(include_deleted, fields_response).filter(cls.model_class.id == id).one_or_none()
            if result is None and not include_deleted:
                raise NoResultFound(f"{cls.model_class.__name__} ID={id} 不存在")
            return cls._convert_to_response(result, fields_response) if result else None
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
    def get_by_ids(cls, ids: List[int], include_deleted: bool = False, fields_response: Optional[List[str]] = None) -> List[ResponseSchemaT]:
        """按 IDs 查询记录"""
        try:
            query = cls._query_all(include_deleted, fields_response)
            items = query.filter(cls.model_class.id.in_(ids)).all()
            return cls._convert_to_response_list(items, fields_response)
        except SQLAlchemyError as e:
            logger.exception("按 IDs=%s 查询 %s 失败 - 数据库错误", ids, cls.model_class.__name__)
            raise SQLAlchemyError(f"按 IDs={ids} 查询失败：数据库错误") from e
        except Exception as e:
            logger.exception("按 IDs=%s 查询 %s 失败 - 系统错误", ids, cls.model_class.__name__)
            raise RuntimeError(f"按 IDs={ids} 查询失败：系统错误") from e

    @classmethod
    def find_by_filter(cls, include_deleted: bool = False, fields_response: Optional[List[str]] = None, **kwargs: Any) -> List[ResponseSchemaT]:
        """按条件查询记录"""
        try:
            query = cls._query_all(include_deleted, fields_response)
            for field, value in kwargs.items():
                if not hasattr(cls.model_class, field):
                    raise AttributeError(f"{cls.model_class.__name__} 没有字段 {field}")
                query = query.filter(getattr(cls.model_class, field) == value)
            items = query.all()
            return cls._convert_to_response_list(items, fields_response)
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
    def search(cls, search_term: str, fields_searched: List[str], fields_response: Optional[List[str]] = None, include_deleted: bool = False) -> List[ResponseSchemaT]:
        """搜索记录"""
        try:
            query = cls._query_all(include_deleted, fields_response)
            conditions = []
            for field in fields_searched:
                if hasattr(cls.model_class, field):
                    conditions.append(getattr(cls.model_class, field).ilike(f'%{search_term}%'))
            if conditions:
                query = query.filter(or_(*conditions))
            items = query.all()
            return cls._convert_to_response_list(items, fields_response)
        except SQLAlchemyError as e:
            logger.exception("搜索 %s 失败 - 数据库错误，term=%s，fields_searched=%s， fields_response=%s", 
                          cls.model_class.__name__, search_term, fields_searched, fields_response)
            raise SQLAlchemyError(f"搜索失败：数据库错误") from e
        except Exception as e:
            logger.exception("搜索 %s 失败 - 系统错误，term=%s，fields_searched=%s， fields_response=%s", 
                          cls.model_class.__name__, search_term, fields_searched, fields_response)
            raise RuntimeError(f"搜索失败：系统错误") from e
    # endregion
    
    # region 单条写操作
    @classmethod
    def create(cls, data: Dict[str, Any], fields_response: Optional[List[str]] = ['id']) -> ResponseSchemaT:
        """创建新记录（通过Schema验证输入）"""
        try:
            return cls._create_object(data, fields_response)
        except SQLAlchemyError as e:
            logger.exception("创建 %s 失败 - 数据库错误，data=%s", 
                          cls.model_class.__name__, data)
            raise SQLAlchemyError(f"创建 {cls.model_class.__name__} 记录失败：数据库错误") from e
        except Exception as e:
            logger.exception("创建 %s 失败 - 系统错误，data=%s", 
                          cls.model_class.__name__, data)
            raise RuntimeError(f"创建 {cls.model_class.__name__} 记录失败：系统错误") from e

    @classmethod
    def update(cls, id: int, data: Dict[str, Any], fields_response: Optional[List[str]] = ['id']) -> ResponseSchemaT:
        """更新记录（通过Schema验证输入）"""
        try:
            return cls._update_object(id, data, fields_response)
        except NoResultFound as e:
            raise NoResultFound(str(e)) from e
        except SQLAlchemyError as e:
            logger.exception("更新 %s ID=%s 失败 - 数据库错误，data=%s", 
                          cls.model_class.__name__, id, data)
            raise SQLAlchemyError(f"更新 {cls.model_class.__name__} ID={id} 失败：数据库错误") from e
        except Exception as e:
            logger.exception("更新 %s ID=%s 失败 - 系统错误，data=%s", 
                          cls.model_class.__name__, id, data)
            raise RuntimeError(f"更新 {cls.model_class.__name__} ID={id} 失败：系统错误") from e

    @classmethod
    def soft_delete(cls, id: int, fields_response: Optional[List[str]] = ['id']) -> ResponseSchemaT:
        """软删除记录"""
        try:
            item = cls.get_by_id(id)
            item.deleted_at = datetime.now(timezone.utc)
            return cls._save_object(item, fields_response)
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
    def hard_delete(cls, id: int, fields_response: Optional[List[str]] = ['id']) -> ResponseSchemaT:
        """硬删除记录"""
        try:
            item = cls.get_by_id(id)
            return cls._delete_object(item, fields_response)
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
    def restore(cls, id: int, fields_response: Optional[List[str]] = ['id']) -> ResponseSchemaT:
        """恢复软删除的记录"""
        try:
            item = cls.get_by_id(id)

            if item.deleted_at is None:
                raise ValueError(f"{cls.model_class.__name__} ID={id} 未被删除")

            item.deleted_at = None
            return cls._save_object(item, fields_response)
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
    def bulk_create(cls, data: List[Dict[str, Any]], batch_size: int = 1000) -> None:
        """批量创建记录（通过Schema验证输入）"""
        cls._create_objects(data, batch_size)

    @classmethod
    def bulk_update(cls, ids: List[int], data: List[Dict[str, Any]], batch_size: int = 1000) -> None:
        """批量更新记录（通过Schema验证输入）"""
        cls._update_objects(ids, data, batch_size)

    @classmethod
    def bulk_soft_delete(cls, ids: List[int], batch_size: int = 1000) -> None:
        """批量软删除记录"""
        try:
            # 获取原始模型对象列表
            items = cls._query_all(include_deleted=False).filter(cls.model_class.id.in_(ids)).all()
            exist_ids = {item.id for item in items}
            missing = set(ids) - exist_ids
            if missing:
                logger.warning("批量软删除 %s 时以下 ID 不存在或已删除：%s", 
                            cls.model_class.__name__, missing)
            for item in items:
                try:
                    item.deleted_at = datetime.now(timezone.utc)
                    cls._save_object(item)
                except SQLAlchemyError as e:
                    logger.warning("批量软删除 %s ID=%s 失败 - 数据库错误", 
                                cls.model_class.__name__, item.id)
                except Exception as e:
                    logger.warning("批量软删除 %s ID=%s 失败 - 系统错误", 
                                cls.model_class.__name__, item.id)
            logger.info("批量软删除 %s 完成", cls.model_class.__name__)
        except SQLAlchemyError as e:
            logger.exception("批量软删除 %s 获取记录失败 - 数据库错误", 
                          cls.model_class.__name__)
            raise SQLAlchemyError(f"批量软删除失败：获取记录时数据库错误") from e
        except Exception as e:
            logger.exception("批量软删除 %s 获取记录失败 - 系统错误", 
                          cls.model_class.__name__)
            raise RuntimeError(f"批量软删除失败：获取记录时系统错误") from e
        
    @classmethod
    def bulk_hard_delete(cls, ids: List[int], batch_size: int = 1000) -> None:
        """批量硬删除记录"""
        cls._delete_objects(ids, batch_size)

    @classmethod
    def bulk_restore(cls, ids: List[int]) -> None:
        """批量恢复记录"""
        try:
            items = cls.get_by_ids(ids, include_deleted=True)
            for item in items:
                try:
                    if item.deleted_at is not None:
                        item.deleted_at = None
                        saved_item = cls._save_object(item)
                except SQLAlchemyError as e:
                    logger.warning("批量恢复 %s ID=%s 失败 - 数据库错误", 
                                cls.model_class.__name__, item.id)
                except Exception as e:
                    logger.warning("批量恢复 %s ID=%s 失败 - 系统错误", 
                                cls.model_class.__name__, item.id)
            logger.info("批量恢复 %s 完成", cls.model_class.__name__)
        except SQLAlchemyError as e:
            logger.exception("批量恢复 %s 获取记录失败 - 数据库错误", 
                          cls.model_class.__name__)
            raise SQLAlchemyError(f"批量恢复失败：获取记录时数据库错误") from e
        except Exception as e:
            logger.exception("批量恢复 %s 获取记录失败 - 系统错误", 
                          cls.model_class.__name__)
            raise RuntimeError(f"批量恢复失败：获取记录时系统错误") from e
    # endregion

# endregion

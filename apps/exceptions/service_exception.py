
class BaseServiceException(Exception):
    """BaseService 抛出的所有业务异常的基类，方便统一捕获。"""


class ModelNotSetException(BaseServiceException):
    """子类未指定 model_class 时抛出。"""


class RecordNotFoundException(BaseServiceException):
    """按主键查不到记录时抛出。"""


class RecordAlreadyDeletedException(BaseServiceException):
    """试图软删除 / 恢复一条已经处于删除状态的记录时抛出。"""


class RecordNotDeletedException(BaseServiceException):
    """试图恢复一条未被删除的记录时抛出。"""


class CreateFailedException(BaseServiceException):
    """创建失败。"""


class UpdateFailedException(BaseServiceException):
    """更新失败。"""


class DeleteFailedException(BaseServiceException):
    """删除失败（含软 / 硬）。"""


class RestoreFailedException(BaseServiceException):
    """恢复失败。"""
    

__all__ = [
    'BaseServiceException', 'ModelNotSetException', 'RecordNotFoundException',
    'RecordAlreadyDeletedException', 'RecordNotDeletedException',
    'CreateFailedException', 'UpdateFailedException', 'DeleteFailedException',
    'RestoreFailedException',
]
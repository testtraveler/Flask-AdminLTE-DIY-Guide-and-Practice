"""数据库初始化模块（适配类方法服务）"""

def init_default_admin():
    """初始化默认管理员账号（调用类方法服务）"""
    from apps.authentication.services import UserService, RoleService  # 导入类服务

    # 1. 检查并创建管理员角色（调用RoleService类方法）
    admin_role = RoleService.find_by_name('admin')
    if not admin_role:
        # 创建管理员角色并保存到数据库
        admin_role = RoleService.create(name='admin', description='管理员角色')

    # 2. 检查并创建管理员用户
    admin_user = UserService.find_by_username('admin')  # 类方法过滤用户
    if not admin_user:
        # 创建管理员用户并保存到数据库
        admin_user = UserService.register(
            username='admin',
            email='admin@localhost',
            password='admin123',
            role_id=admin_role.id
        )

def init_app():
    """注册初始化函数（无变更）"""
    init_default_admin()

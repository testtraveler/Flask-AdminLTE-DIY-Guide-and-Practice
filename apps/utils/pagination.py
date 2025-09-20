# apps/utils/pagination.py
from flask import request, url_for
from apps.authentication.models import User, Role, Group   # 引入真实模型

MODEL_MAP = {
    'User' : User, 
    'Role' : Role, 
    'Group' : Group,
}

DEFAULT_PER_PAGE = 5         # 默认每页条数
ALLOW_PER_PAGE   = [5, 10, 20, 50]   # 允许用户选择的行数

class PaginationHelper:
    @staticmethod
    def _get_model(model_name: str):
        """根据名字拿到模型类，忽略大小写"""
        return MODEL_MAP.get(model_name.lower())

    @staticmethod
    def get_per_page(model_name: str) -> int:
        """优先取用户本次选择，其次取上次 cookie，最后默认"""
        try:
            # 先看本次 url 参数
            pp = int(request.args.get('per_page', 0))
            if pp in ALLOW_PER_PAGE:
                return pp
        except (ValueError, TypeError):
            pass
        # 再看 cookie
        ck = request.cookies.get(f'per_page_{model_name.lower()}')
        if ck and int(ck) in ALLOW_PER_PAGE:
            return int(ck)
        return DEFAULT_PER_PAGE

    @staticmethod
    def paginate(query, model_name: str):
        """统一生成分页对象"""
        per_page = PaginationHelper.get_per_page(model_name)
        page = request.args.get('page', 1, type=int)
        return query.paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def render_pagination(pagination, model_name: str):
        """渲染风格分页条：行数选择 + 当前页/总页 + 上/下页 + 回到简页"""
        if pagination.pages <= 1:
            return ''

        # 当前 url 参数（不含 page / per_page）
        args = request.args.copy()
        args.pop('page', None)
        base_url = url_for(request.endpoint, **args)

        # 每页行数下拉
        pp_sel = f'<select id="ppSel" onchange="changePerPage(this.value)">'
        for v in ALLOW_PER_PAGE:
            selected = 'selected' if v == pagination.per_page else ''
            pp_sel += f'<option value="{v}" {selected}>{v}</option>'
        pp_sel += '</select>'

        # 上一/下一页链接
        prev_dis = '' if pagination.has_prev else 'disabled'
        next_dis = '' if pagination.has_next else 'disabled'
        prev_url = f'{base_url}&page={pagination.prev_num}&per_page={pagination.per_page}'
        next_url = f'{base_url}&page={pagination.next_num}&per_page={pagination.per_page}'

        # 回到简页（直接返回第一页）
        home_url = f'{base_url}&page=1&per_page={pagination.per_page}'

        html = f'''
        <div class="row align-items-center" style="font-size:0.9rem;">
          <div class="col-auto">每行数 {pp_sel}</div>
          <div class="col-auto">当前页 {pagination.page}/{pagination.pages}</div>
          <div class="col-auto">
            <button class="btn btn-sm btn-outline-primary {prev_dis}" onclick="location.href='{prev_url}'">上一页</button>
            <button class="btn btn-sm btn-outline-primary {next_dis}" onclick="location.href='{next_url}'">下一页</button>
            <button class="btn btn-sm btn-outline-secondary" onclick="location.href='{home_url}'">回到简页</button>
          </div>
        </div>
        <script>
          function changePerPage(val){{
            location.href="{base_url}&page=1&per_page=" + val;
          }}
        </script>
        '''
        return html
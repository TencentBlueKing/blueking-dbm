# -*- coding: utf-8 -*-
"""
自定义 WhiteNoise 中间件，解决子路径部署模式下静态文件 404 的问题。

问题根因：
- STATIC_URL = "/bkdbm/static/"（让 {% static %} 标签生成带子路径前缀的 URL）
- FORCE_SCRIPT_NAME = "/bkdbm"（Django 自动将 PATH_INFO 中的 /bkdbm 前缀剥离）
- WhiteNoise 默认用 STATIC_URL（"/bkdbm/static/"）匹配 PATH_INFO（"/static/..."），匹配失败

解决方式：
- 覆盖 WhiteNoise 的 static_prefix 为 "/static/"，使其能正确匹配 PATH_INFO
"""

from django.conf import settings
from whitenoise.middleware import WhiteNoiseMiddleware as _WhiteNoiseMiddleware


class WhiteNoiseMiddleware(_WhiteNoiseMiddleware):
    """自定义 WhiteNoise 中间件，支持子路径部署模式"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 当配置了 FORCE_SCRIPT_NAME 时，WSGI 层会将子路径前缀从 PATH_INFO 中剥离，
        # 因此 WhiteNoise 匹配时应使用不含子路径前缀的路径。
        # 例如：STATIC_URL="/bkdbm/static/"，实际 PATH_INFO="/static/xxx"
        # 需要用 "/static/" 而非 "/bkdbm/static/" 来匹配
        force_script_name = getattr(settings, "FORCE_SCRIPT_NAME", None)
        if force_script_name and self.static_prefix.startswith(force_script_name):
            self.static_prefix = self.static_prefix[len(force_script_name) :]

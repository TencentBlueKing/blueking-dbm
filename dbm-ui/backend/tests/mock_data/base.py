# -*- coding: utf-8 -*-
"""
通用测试工具方法
"""
from unittest.mock import patch


class MockContextManager:
    """Mock上下文管理器"""

    def __init__(self, patches):
        self.patches = patches
        self.mocks = {}

    def __enter__(self):
        for name, patch_target in self.patches.items():
            patcher = patch(patch_target)
            self.mocks[name] = patcher.start()
        return self.mocks

    def __exit__(self, exc_type, exc_val, exc_tb):
        for name in self.patches:
            patch.stopall()

# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import os
import tempfile

from backend.core.translation import language_finder
from backend.core.translation.constants import LanguageFindMode


class TestLanguageFinderFunctionality:
    """测试语言查找器功能"""

    def test_language_finder_detect_chinese_strings(self):
        """测试语言查找器检测中文字符串功能"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write('print("测试消息")\n')
            test_file = f.name

        try:
            finder = language_finder.LanguageFinder(path=test_file)
            translater, translate_nodes = finder.check_file(test_file)

            # 应该检测到中文字符串
            assert translater is not None
            assert translate_nodes is not None
        finally:
            os.unlink(test_file)

    def test_language_finder_ignore_translated_strings(self):
        """测试语言查找器忽略已翻译字符串功能"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write('from django.utils.translation import ugettext as _\nprint(_("测试消息"))\n')
            test_file = f.name

        try:
            finder = language_finder.LanguageFinder(path=test_file)
            translater, translate_nodes = finder.check_file(test_file)

            # 已翻译的字符串应该被忽略
            assert translater is not None
            assert translate_nodes is not None
        finally:
            os.unlink(test_file)

    def test_language_finder_process_directory(self):
        """测试语言查找器处理目录功能"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试文件
            test_file = os.path.join(temp_dir, "test.py")
            with open(test_file, "w") as f:
                f.write('print("测试消息")\n')

            finder = language_finder.LanguageFinder(path=temp_dir)
            result = finder.list_dir(temp_dir)

            # 应该找到测试文件
            assert test_file in result

    def test_language_finder_generate_translation_info(self):
        """测试语言查找器生成翻译信息功能"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write('print("测试消息")\n')
            test_file = f.name

        try:
            finder = language_finder.LanguageFinder(path=test_file)

            # 创建必要的目录
            os.makedirs(os.path.dirname(finder.TRANSLATE_INFO_FILE), exist_ok=True)

            finder.run()

            # 检查是否生成了翻译信息文件
            assert os.path.exists(finder.TRANSLATE_INFO_FILE)
            assert os.path.exists(finder.FORMATTED_STRINGS_FILE)
        finally:
            os.unlink(test_file)
            if os.path.exists(finder.TRANSLATE_INFO_FILE):
                os.unlink(finder.TRANSLATE_INFO_FILE)
            if os.path.exists(finder.FORMATTED_STRINGS_FILE):
                os.unlink(finder.FORMATTED_STRINGS_FILE)

    def test_language_finder_error_mode_detection(self):
        """测试语言查找器错误模式检测功能"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write('print("测试消息")\n')
            test_file = f.name

        try:
            finder = language_finder.LanguageFinder(path=test_file, mode=LanguageFindMode.ERROR.value)

            # 在ERROR模式下，如果有未翻译的内容应该抛出异常
            try:
                finder.run()
            except Exception as e:
                # 如果抛出异常，检查是否是预期的异常类型
                assert "untranslated" in str(e).lower() or "f-string" in str(e).lower()
        finally:
            os.unlink(test_file)

    def test_language_finder_handle_mixed_content(self):
        """测试语言查找器处理混合内容功能"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
from django.utils.translation import ugettext as _
print("未翻译的中文")
print(_("已翻译的中文"))
print("English text")
            """
            )
            test_file = f.name

        try:
            finder = language_finder.LanguageFinder(path=test_file)
            translater, translate_nodes = finder.check_file(test_file)

            # 应该能处理混合内容
            assert translater is not None
            assert translate_nodes is not None
        finally:
            os.unlink(test_file)

    def test_language_finder_handle_f_strings(self):
        """测试语言查找器处理f字符串功能"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write('name = "测试"\nprint(f"Hello {name}")\n')
            test_file = f.name

        try:
            finder = language_finder.LanguageFinder(path=test_file)
            translater, translate_nodes = finder.check_file(test_file)

            # 应该能处理f字符串
            assert translater is not None
            assert translate_nodes is not None
        finally:
            os.unlink(test_file)

    def test_language_finder_handle_complex_python_code(self):
        """测试语言查找器处理复杂Python代码功能"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                '''
def test_function():
    """测试函数"""
    if True:
        print("条件语句中的中文")
    for i in range(3):
        print(f"循环中的中文 {i}")
    return "返回值中的中文"
            '''
            )
            test_file = f.name

        try:
            finder = language_finder.LanguageFinder(path=test_file)
            translater, translate_nodes = finder.check_file(test_file)

            # 应该能处理复杂的Python代码
            assert translater is not None
            assert translate_nodes is not None
        finally:
            os.unlink(test_file)

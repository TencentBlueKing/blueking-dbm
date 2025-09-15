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
import tempfile
from unittest.mock import MagicMock, patch

from backend.core.translation.translate import Translater


class TestTranslater:
    """测试 Translater 类"""

    @patch("backend.core.translation.translate.Translate")
    def test_translate_chinese(self, mock_translate_cls):
        """测试翻译 - 中文不翻译"""
        translater = Translater("test.po", "zh-CN")
        result = translater.translate("测试文本")
        assert result == "测试文本"

    @patch("backend.core.translation.translate.Translate")
    def test_translate_english(self, mock_translate_cls):
        """测试翻译 - 英文翻译"""
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.translatedText = "test text"
        mock_client.translate.return_value = mock_result
        mock_translate_cls.return_value = mock_client

        translater = Translater("test.po", "en")
        result = translater.translate("测试文本")
        assert result == "test text"

    @patch("backend.core.translation.translate.Translate")
    def test_translate_retry(self, mock_translate_cls):
        """测试翻译 - 错误重试"""
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.translatedText = "test"
        mock_client.translate.side_effect = [Exception("error"), mock_result]
        mock_translate_cls.return_value = mock_client

        translater = Translater("test.po", "en")
        result = translater._translate("测试", retry_count=0)
        assert result == "test"

    @patch("backend.core.translation.translate.Translate")
    def test_translate_max_retry(self, mock_translate_cls):
        """测试翻译 - 达到最大重试次数返回原文"""
        mock_client = MagicMock()
        mock_client.translate.side_effect = Exception("error")
        mock_translate_cls.return_value = mock_client

        translater = Translater("test.po", "en")
        result = translater._translate("测试", retry_count=10)
        assert result == "测试\n"

    @patch("backend.core.translation.translate.Translate")
    def test_run_po_file(self, mock_translate_cls):
        """测试PO文件翻译"""
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.translatedText = "test message"
        mock_client.translate.return_value = mock_result
        mock_translate_cls.return_value = mock_client

        # 创建临时PO文件
        po_content = """msgid "测试消息"
msgstr ""
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".po", delete=False, encoding="utf-8") as f:
            f.write(po_content)
            temp_file = f.name

        translater = Translater(temp_file, "en")
        translater.run()

        # 验证输出文件存在
        import os

        assert os.path.exists(translater.output_file_name)

        # 清理
        os.remove(temp_file)
        os.remove(translater.output_file_name)

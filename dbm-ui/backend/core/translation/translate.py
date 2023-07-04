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

import logging
import time
from typing import List

from pygtrans import Translate

logger = logging.getLogger("root")


class Translater:
    """翻译主体类"""

    MAX_RETRY_COUNT: int = 5

    def __init__(self, file_path: str, language: str):
        self.client = Translate()
        self.file_path = file_path
        self.language = language
        # 默认语言是中文，即不翻译
        self.default_language = "zh-CN"
        # 默认输出为xxx_tmp.po文件
        self.output_file_name = f"{file_path.split('.')[0]}_tmp.po"
        # 翻译的限流阈值
        self.translate_count = 0
        self.translate_limit = 100

    def _translate(self, string: str, retry_count: int = 0):
        # 如果超过最大重试次数，则不翻译，返回原字符
        if retry_count > self.MAX_RETRY_COUNT:
            return f"{string}\n"

        try:
            if self.language != self.default_language:
                result = self.client.translate(string, target=self.language)
                return result.translatedText.replace("&quot;", '"')
            return string
        except Exception:  # pylint: disable=broad-except:
            # 如果为空，则再等待0.1s
            time.sleep(0.1)
            return self._translate(string, retry_count + 1)

    def translate(self, string: str) -> str:
        """
        对line执行翻译
        :param string: 待翻译字符串
        """
        self.translate_count += 1

        # 达到限流阈值，重新实例化Client
        if not (self.translate_count % self.translate_limit):
            self.client = Translate()

        return self._translate(string)

    def run(self):
        def _format_quote(string, flag) -> str:
            """flag为0，去掉引号；flag为1添加引号"""
            if flag:
                return f'"{string}"\n'
            else:
                if string.endswith("\n"):
                    return string[1:-2]
                return string[1:-1]

        def _format_quote_list(string_list, flag) -> List[str]:
            return [_format_quote(string, flag) for string in string_list]

        def _find_sentence_block(file_lines, index, start_block, end_block) -> (List[str], int):
            sentences = [_format_quote(file_lines[index].split(f"{start_block} ")[1], 0)]
            while index < len(file_lines):
                index += 1
                if index >= len(file_lines) or file_lines[index].startswith(end_block):
                    return sentences, index

                sentences.append(_format_quote(file_lines[index], 0))

        with open(self.file_path, "r+", encoding="utf-8") as f:
            file_lines = f.readlines()

        new_file_lines: List[str] = []
        line_index: int = 0
        is_fuzzy = False
        while line_index < len(file_lines):
            logger.info(f"translation-progress: {round(line_index * 100 / len(file_lines), 2)}%")

            line_str = file_lines[line_index]

            # 寻找msgid块和msgstr块
            if line_str.startswith("msgid"):
                untranslated_sts, msgid_end_index = _find_sentence_block(file_lines, line_index, "msgid", "msgstr")
                translated_sts, msgstr_end_index = _find_sentence_block(file_lines, msgid_end_index, "msgstr", "\n")

                new_file_lines.extend(
                    [f"msgid {_format_quote(untranslated_sts[0], 1)}", *_format_quote_list(untranslated_sts[1:], 1)]
                )

                # 如果已经翻译过文本，则跳过翻译步骤
                if (translated_sts[0] or len(translated_sts) > 1) and not is_fuzzy:
                    new_file_lines.extend(
                        [f"msgstr {_format_quote(translated_sts[0], 1)}", *_format_quote_list(translated_sts[1:], 1)]
                    )
                # 翻译文本
                else:
                    translated_string = self.translate("".join(untranslated_sts))
                    logger.info(f"translate [{untranslated_sts}] to [{translated_string}]")
                    new_file_lines.append(f"msgstr {_format_quote(translated_string, 1)}")

                line_index = msgstr_end_index
            else:
                # 处理 fuzzy 文本， fuzzy 会导致不翻译
                if line_str.startswith("#:"):
                    is_fuzzy = False
                if line_str.startswith("#, fuzzy") or line_str.startswith("#|"):
                    is_fuzzy = True
                    line_index += 1
                    continue
                new_file_lines.append(line_str)
                line_index += 1

        # 输出到临时文件
        translated_po = "".join(new_file_lines)
        with open(self.output_file_name, "w+", encoding="utf-8") as f:
            f.write(translated_po)

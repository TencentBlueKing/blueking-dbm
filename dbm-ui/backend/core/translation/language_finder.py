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

import ast
import json
import logging
import os
import re
from typing import List

import astunparse

from backend.core.translation.constants import (
    ALL_EXCLUDE_DIRS,
    EXCLUDE_LANGUAGES_IN_FILE,
    IGNORED_METHOD_LIST,
    LANGUAGE_REGEX_MAP,
    Language,
    LanguageFindMode,
)
from backend.core.translation.exceptions import LanguageSpecificFStringException, UnTranslatedFileExistException

logger = logging.getLogger("root")


def check_special_language(ignored_string, file_path, string_regex, string):
    """检查是否存在特定语言片段"""

    # 考虑去掉引号
    if (string.startswith("'") and string.endswith("'")) or (string.startswith('"') and string.endswith('"')):
        check_string = string[1:-1]
    else:
        check_string = string

    if check_string in ignored_string or check_string in EXCLUDE_LANGUAGES_IN_FILE.get(file_path, []):
        return False

    if not re.findall(string_regex, string):
        return False

    return True


class NodeTranslateInit(ast.NodeVisitor):
    """
    获取当前文件导入的翻译函数，并检查文件中的format字符
    """

    ImportPath = "django.utils.translation"

    def __init__(self, ignored_string, string_regex, file_path, *args, **kwargs):
        super(NodeTranslateInit, self).__init__(*args, **kwargs)
        self.file_path = file_path
        self.ignored_string = ignored_string
        self.string_regex = string_regex
        self.trans_func_names = []
        self.formatted_strings = []

    @classmethod
    def get_node_module(cls, node):
        while not isinstance(node, ast.Module):
            node = node.parent

        return node

    def _check_special_language(self, string):
        return check_special_language(self.ignored_string, self.file_path, self.string_regex, string)

    def visit_ImportFrom(self, node):
        """游走到import，缓存翻译函数"""

        if node.module != self.ImportPath:
            return

        for name in node.names:
            self.trans_func_names.append(name.asname or name.name)

    def visit_Str(self, node):
        """游走到str，如果当前str是待翻译语言，则标记module"""

        if not self._check_special_language(node.s):
            return

        # 标记Module，后续可能添加import函数
        module_node = self.get_node_module(node)
        for import_from in module_node.body:
            if isinstance(import_from, ast.ImportFrom) and import_from.module == self.ImportPath:
                return

        module_node.language_flag = True

    def visit_JoinedStr(self, node):
        """游走到format string"""

        flag = False
        format_string_list = []
        for str_node in node.values:
            if isinstance(str_node, ast.Str):
                format_string_list.append(str_node.s)
                flag = flag | self._check_special_language(str_node.s)
            elif isinstance(str_node, ast.FormattedValue):
                format_string_list.append(f"{{{getattr(str_node.value, 'id', '{}')}}}")

        # 如果没寻找到特定的format字符串，则忽略
        if not flag:
            return

        self.formatted_strings.append(
            {"key": "".join(format_string_list), "line": node.lineno, "col": node.col_offset}
        )


class NodeTranslateMixin:
    def __init__(
        self,
        file_path: str,
        string_regex: str,
        trans_func_names: List[str],
        ignored_string: List[str],
        *args,
        **kwargs,
    ):
        """
        :param trans_func_names: 该文件的翻译方法名
        :param file_path: 文件路径
        :param ignored_chinese: 不需要检查的中文名
        :param string_regex: 待匹配语言的正则表达式，默认为中文
        """
        super().__init__(*args, **kwargs)
        self.trans_func_names = trans_func_names
        self.file_path = file_path
        self.ignored_string = ignored_string if ignored_string else []
        self.ignored_method_list = IGNORED_METHOD_LIST
        self.string_regex = string_regex

        # 缓存翻译的语句信息
        self.sentences_to_be_translated = []

    def get_near_func(self, node):
        """查找当前node最近函数父节点"""

        while not issubclass(type(node.parent), ast.Assign):
            if isinstance(node.parent, ast.Call):
                return node
            node = node.parent
        return node

    def _check_special_language(self, string):
        return check_special_language(self.ignored_string, self.file_path, self.string_regex, string)

    def check_parent_func(self, node):
        """检查父函数是否为翻译函数or忽略函数"""

        if "func" in node.parent.__dict__:
            func_id = getattr(node.parent.func, "id", None) or node.parent.func.attr
            if func_id == "format":
                # 如果父节点是format函数，则查看其上一层是否是翻译函数
                return self.check_parent_func(node.parent)
            if func_id in [*self.trans_func_names, *self.ignored_method_list]:
                return True
        return False

    def visit_Str(self, node):
        """游走到Str节点"""

        # 如果该字符串是表达式或者比较式，则不做处理
        if isinstance(node.parent, ast.Expr) or isinstance(node.parent, ast.Compare):
            return

        string = node.s
        if not self._check_special_language(string):
            return

        try:
            parent_node = self.get_near_func(node)
        except Exception:  # pylint: disable=broad-except
            parent_node = node

        # 如果父节点是翻译函数，则不做处理
        if self.check_parent_func(parent_node):
            return None

        # 写入待翻译代码片段的信息
        try:
            sentence_info = {"key": string, "line": node.lineno, "col": node.col_offset}
        except Exception:  # pylint: disable=broad-except
            sentence_info = {"key": string, "line": node.parent.lineno, "col": node.parent.col_offset}
        self.sentences_to_be_translated.append(sentence_info)

        return node


class TranslateChecker(NodeTranslateMixin, ast.NodeVisitor):
    """
    对字符串进行翻译检查
    """

    def visit_Str(self, node):
        super().visit_Str(node)


class TranslateAdder(NodeTranslateMixin, ast.NodeTransformer):
    """
    对未翻译的字符串添加翻译函数
    """

    def visit_Module(self, node):
        """游走到Module"""

        # 存在子节点需要generic_visit先遍历子节点
        self.generic_visit(node)

        if not getattr(node, "language_flag", False):
            return node

        # 对于已经标记的module，说明存在未导入翻译函数
        node.body.insert(
            0,
            ast.ImportFrom(
                module=NodeTranslateInit.ImportPath, names=[ast.alias(name="ugettext", asname="_")], level=0
            ),
        )
        return node

    def visit_Str(self, node):
        """游走到str, 将str替换为_()str"""
        alter_node = super().visit_Str(node)

        if alter_node:
            return ast.Call(func=ast.Name(id="_", ctx=ast.Load()), args=[ast.Str(s=node.s)], keywords=[])
        else:
            return node


class LanguageFinder:
    """
    查找语言翻译主程序
    """

    # 写入待翻译信息的文件名
    TRANSLATE_INFO_FILE: str = "backend/locale/translate_info.json"
    FORMATTED_STRINGS_FILE: str = "backend/locale/formatted_string_info.json"

    def __init__(
        self,
        path: str,
        suffix: str = "",
        translate_language: str = Language.ZH_CN.value,
        exclude_dir_or_file_list: List[str] = None,
        ignored_string: List[str] = None,
        mode: str = LanguageFindMode.VISIT.value,
    ):
        """
        :param path: 查找文件路径
        :param suffix: 查找文件后缀名（默认查找全部）
        :param exclude_dir_or_file_list: 排除的文件或文件夹列表
        :param ignored_string: 忽略的语言
        """
        _exclude_dir_or_file_list = {
            # 默认忽略的公共目录
            "migrations",
            "tests",
            "fake",
            "venv",
            "webpack",
            "translate",
            "conf",
            "config",
        }
        if exclude_dir_or_file_list:
            _exclude_dir_or_file_list.update(set(exclude_dir_or_file_list))
        # 因为在项目中过滤的文件可能过多，因此支持在文件外直接写入对应的忽略文件名或文件夹名
        _exclude_dir_or_file_list.update(ALL_EXCLUDE_DIRS)

        self.path = path
        self.suffix = suffix
        self.exclude_dir_or_file_list = _exclude_dir_or_file_list
        self.ignored_string = ignored_string if ignored_string else []
        self.translate_language = translate_language
        self.mode = mode

        # 缓存翻译的语句信息
        self.sentences_to_be_translated = {}
        # 缓存format的字符串
        self.formatted_strings = {}

    def check_file(self, file_path):
        """
        检查当前文件中的所有中文是否国际化
        """
        with open(file_path, "r") as f:
            nodes = ast.parse(f.read())

        # 添加父节点
        for node in ast.walk(nodes):
            for child in ast.iter_child_nodes(node):
                child.parent = node

        # 获取该文件导入的翻译函数
        tree = NodeTranslateInit(
            file_path=self.path,
            ignored_string=self.ignored_string,
            string_regex=LANGUAGE_REGEX_MAP[self.translate_language],
        )
        tree.visit(nodes)
        # 缓存当前文件的format语句
        if tree.formatted_strings:
            self.formatted_strings[file_path] = tree.formatted_strings

        # 检查翻译
        if self.mode == LanguageFindMode.VISIT.value:
            translate_handler_class = TranslateChecker
        else:
            translate_handler_class = TranslateAdder

        translate_handler = translate_handler_class(
            trans_func_names=tree.trans_func_names,
            file_path=file_path,
            ignored_string=self.ignored_string,
            string_regex=LANGUAGE_REGEX_MAP[self.translate_language],
        )
        translate_nodes = translate_handler.visit(nodes)

        # 缓存当前文件的待翻译语句
        if translate_handler.sentences_to_be_translated:
            self.sentences_to_be_translated[file_path] = translate_handler.sentences_to_be_translated

        return translate_handler, translate_nodes or nodes

    def list_dir(self, dir_path):
        """
        找到路径下的所有待检测文件
        """
        ret = []
        file_dirs = os.listdir(dir_path)
        for file_dir in file_dirs:
            if file_dir.startswith(".") or file_dir.startswith("~") or file_dir in self.exclude_dir_or_file_list:
                continue

            abs_path = os.path.join(dir_path, file_dir)
            if abs_path in self.exclude_dir_or_file_list:
                continue

            if file_dir.endswith(self.suffix):
                ret.append(abs_path)
            elif os.path.isdir(abs_path):
                ret += self.list_dir(abs_path)
        return ret

    def run(self):
        if os.path.isdir(self.path):
            file_lists = self.list_dir(self.path)
        else:
            file_lists = [self.path]

        # 对每个文件进行检查翻译
        for each_file in file_lists:
            try:
                translater, translate_nodes = self.check_file(each_file)
                # 如果没有待翻译的文件，则提前返回
                if not translater.sentences_to_be_translated:
                    continue

                if self.mode == LanguageFindMode.AST_ALTER.value:
                    # 当前是ast_alter模式，将修改后的源码写入原文件
                    altered_code = astunparse.unparse(translate_nodes)
                    with open(each_file, "w") as f:
                        f.write(altered_code)
                elif self.mode == LanguageFindMode.SIMPLE_ALTER:
                    # 当前是simple_alter模式，进行字符串替换，添加翻译函数
                    with open(each_file, "r") as f:
                        file_lines = f.readlines()

                    for sentence in translater.sentences_to_be_translated:
                        raw_line_str = file_lines[sentence["line"] - 1]
                        quote = '"' if raw_line_str.find(f'"{sentence["key"]}"') != -1 else "'"
                        file_lines[sentence["line"] - 1] = raw_line_str.replace(
                            f'{quote}{sentence["key"]}{quote}', f'_({quote}{sentence["key"]}{quote})'
                        )

                    # 导入翻译函数包, 默认为ugettext, TODO: 做成一个参数传递?
                    if getattr(translate_nodes, "language_flag", False):
                        file_lines.insert(1, f"from {NodeTranslateInit.ImportPath} import ugettext as _\n")

                    with open(each_file, "w") as f:
                        f.write("".join(file_lines))
            except Exception as e:  # pylint: disable=broad-except
                logger.info(f"Checking file：{each_file}, Error: {e}")

        if self.mode == LanguageFindMode.ERROR.value:
            # 当前是error模式，如果存在未翻译片段 or f-string，则抛出错误
            if self.sentences_to_be_translated:
                raise UnTranslatedFileExistException(
                    f"There are untranslated files/code snippets in the project: "
                    f"{json.dumps(self.sentences_to_be_translated, ensure_ascii=False, indent=4)}"
                )

            if self.formatted_strings:
                raise LanguageSpecificFStringException(
                    f"There are f-strings containing the specific translation language in the project:"
                    f"{json.dumps(self.formatted_strings, ensure_ascii=False, indent=4)}"
                )
        else:
            # 写入未翻译信息
            with open(self.TRANSLATE_INFO_FILE, "w+") as f:
                f.write(json.dumps(self.sentences_to_be_translated, ensure_ascii=False, indent=4))

            # 写入format字符串信息
            with open(self.FORMATTED_STRINGS_FILE, "w+") as f:
                f.write(json.dumps(self.formatted_strings, ensure_ascii=False, indent=4))

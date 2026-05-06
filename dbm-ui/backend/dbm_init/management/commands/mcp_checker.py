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
import json
from collections import defaultdict
from typing import Dict, List, Set

import networkx as nx
import yaml

from backend.dbm_aiagent.mcp_tools import urls  # noqa
from backend.dbm_aiagent.mcp_tools.constants import DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import MCP_TOOLS_REGISTRY


class SimpleMCPDependencyGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.operations: Dict[str, Dict] = {}  # 操作信息
        self.field_to_mcps: Dict[str, Set[str]] = defaultdict(set)  # 字段到MCP的映射

    def load_from_file(self, filepath: str, mcp_servers: List[DBMMcpTools] = None):
        """加载OpenAPI文件"""
        with open(filepath, "r", encoding="utf-8") as f:
            if filepath.endswith((".yaml", ".yml")):
                spec = yaml.safe_load(f)
            else:
                spec = json.load(f)

        self._parse_mcp_spec(spec, mcp_servers)
        self._build_simple_dependency_graph()

    def _parse_mcp_spec(self, spec: Dict, mcp_servers: List[DBMMcpTools] = None):
        """解析MCP规范"""
        # 收集所有schema定义
        schemas = spec.get("components", {}).get("schemas", {})

        # 解析所有POST操作（假设MCP都是POST）
        for path, path_item in spec.get("paths", {}).items():
            post_op = path_item.get("post")
            if post_op:
                self._parse_post_operation(path, post_op, schemas, mcp_servers)

    def _parse_post_operation(self, path: str, operation: Dict, schemas: Dict, mcp_servers: List[DBMMcpTools] = None):
        """解析单个POST操作"""
        mcp_name = operation.get("operationId", path.split("/")[-1])

        if mcp_servers:
            found = False
            for ms in mcp_servers:
                ms_register_tools = MCP_TOOLS_REGISTRY[ms]
                if mcp_name in ms_register_tools:
                    found = True
                    break

            if not found:
                return

                # 提取输入字段
        input_fields = self._extract_fields(operation, "requestBody", schemas)

        # 提取输出字段
        output_fields = self._extract_fields(operation, "responses", schemas)

        # 存储操作信息
        self.operations[mcp_name] = {"path": path, "inputs": input_fields, "outputs": output_fields}

        # 建立字段到MCP的映射
        for field in input_fields:
            self.field_to_mcps[field].add(f"mcp_consumes:{mcp_name}")
        for field in output_fields:
            self.field_to_mcps[field].add(f"mcp_produces:{mcp_name}")

        # 添加节点
        self.graph.add_node(mcp_name, inputs=input_fields, outputs=output_fields, path=path)

    def _extract_fields(self, operation: Dict, section: str, schemas: Dict) -> Set[str]:
        """提取字段集合"""
        fields = set()

        if section == "requestBody":
            # 提取请求字段
            request_body = operation.get("requestBody", {})
            if "content" in request_body:
                for content_type, media_type in request_body["content"].items():
                    if "schema" in media_type:
                        fields.update(self._get_all_properties(media_type["schema"], schemas))

        elif section == "responses":
            # 提取响应字段（取200响应）
            responses = operation.get("responses", {})
            success_response = responses.get("200") or responses.get("201")
            if success_response and "content" in success_response:
                for content_type, media_type in success_response["content"].items():
                    if "schema" in media_type:
                        fields.update(self._get_all_properties(media_type["schema"], schemas))

        return fields

    def _get_all_properties(self, schema: Dict, schemas: Dict, prefix: str = "") -> Set[str]:
        """递归获取所有属性字段"""
        fields = set()

        # 处理$ref引用
        if "$ref" in schema:
            ref_path = schema["$ref"]
            if "#/components/schemas/" in ref_path:
                schema_name = ref_path.split("/")[-1]
                ref_schema = schemas.get(schema_name, {})
                return self._get_all_properties(ref_schema, schemas, prefix)

        # 处理properties
        if "properties" in schema:
            for prop_name, prop_schema in schema["properties"].items():
                field_name = f"{prefix}.{prop_name}" if prefix else prop_name

                # 递归处理嵌套对象
                if (
                    "properties" in prop_schema
                    or "$ref" in prop_schema
                    or (prop_schema.get("type") == "array" and "items" in prop_schema)
                ):
                    fields.update(self._get_all_properties(prop_schema, schemas, field_name))
                else:
                    fields.add(field_name)

        # 处理数组
        if schema.get("type") == "array" and "items" in schema:
            # fields.update(self._get_all_properties(schema['items'], schemas, f'{prefix}[]'))
            fields.update(self._get_all_properties(schema["items"], schemas))

        return fields

    def _build_simple_dependency_graph(self):
        """构建简单的依赖图：MCP A的输出能作为MCP B的输入"""
        mcp_names = list(self.operations.keys())

        for i, source_mcp in enumerate(mcp_names):
            for target_mcp in mcp_names[i + 1 :]:
                # 检查依赖关系
                source_outputs = self.operations[source_mcp]["outputs"]
                target_inputs = self.operations[target_mcp]["inputs"]

                # 找出匹配的字段
                matching_fields = source_outputs & target_inputs

                if matching_fields:
                    # 添加依赖边
                    self.graph.add_edge(
                        source_mcp, target_mcp, fields=list(matching_fields), weight=len(matching_fields)
                    )

                # 检查反向依赖
                source_inputs = self.operations[source_mcp]["inputs"]
                target_outputs = self.operations[target_mcp]["outputs"]
                reverse_matching = target_outputs & source_inputs

                if reverse_matching:
                    self.graph.add_edge(
                        target_mcp, source_mcp, fields=list(reverse_matching), weight=len(reverse_matching)
                    )

    def find_cycles(self) -> List[List[str]]:
        """查找循环依赖"""
        try:
            res = list(nx.simple_cycles(self.graph))
            return res
        except Exception:  # noqa
            return []

    def find_mcp_by_field(self, field_name: str) -> Dict[str, List[str]]:
        """根据字段查找能生成或需要该字段的MCP"""
        result = {"produces": [], "consumes": []}  # 能生成该字段的MCP  # 需要该字段的MCP

        for mcp_name, info in self.operations.items():
            if field_name in info["outputs"]:
                result["produces"].append(mcp_name)
            if field_name in info["inputs"]:
                result["consumes"].append(mcp_name)

        return result

    def get_completion_paths(self, start_fields: Set[str], target_fields: Set[str]) -> List[List[str]]:
        """获取从起始字段到目标字段的补全路径"""

        # 找到能生成目标字段的MCP
        target_mcps = []
        for field in target_fields:
            for mcp_name, info in self.operations.items():
                if field in info["outputs"]:
                    target_mcps.append(mcp_name)

        if not target_mcps:
            return []

        # 简单的BFS搜索
        paths = []
        for target_mcp in set(target_mcps):
            # 检查这个MCP需要什么输入
            required_inputs = self.operations[target_mcp]["inputs"]

            # 已有哪些字段
            available_fields = set(start_fields)

            # 还需要哪些字段
            needed_fields = required_inputs - available_fields

            if not needed_fields:
                # 可以直接调用
                paths.append([target_mcp])
            else:
                # 需要先补全其他字段
                for field in needed_fields:
                    # 查找能生成这个字段的MCP
                    producers = self.find_mcp_by_field(field)["produces"]
                    for producer in producers:
                        paths.append([producer, target_mcp])

        return paths

    def export_for_llm(self, output_file="mcp-knowledge.md"):
        """导出为LLM可用的知识文档"""
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# MCP工具知识库\n\n")

            # 1. 所有MCP工具列表
            f.write("## 可用MCP工具\n")
            for mcp_name, info in self.operations.items():
                f.write(f"### {mcp_name}\n")
                f.write(f"- 路径: `{info['path']}`\n")
                f.write(f"- 需要输入: {', '.join(sorted(info['inputs'])) or '无'}\n")
                f.write(f"- 产生输出: {', '.join(sorted(info['outputs'])) or '无'}\n\n")

            # 2. 环路检测报告
            f.write("## 环路检测报告\n")
            cycles = self.find_cycles()
            if cycles:
                f.write(f"⚠️ 发现 {len(cycles)} 循环依赖\n")
                for idx in range(len(cycles)):
                    cycle = cycles[idx]
                    f.write(f"### 环路 {idx + 1}\n")
                    f.write("```mermaid\ngraph TD\n")

                    # 添加节点
                    for node in cycle:
                        f.write(f"    {node.replace('-', '_')}[\"{node}\"]\n")

                    for i in range(len(cycle)):
                        u = cycle[i].replace("-", "_")
                        v = cycle[(i + 1) % len(cycle)].replace("-", "_")
                        edge_data = self.graph.get_edge_data(u, v, default={}).copy()
                        fields = edge_data.get("fields", [])
                        fields_str = ", ".join(fields)
                        f.write(f"    {u} -->|{fields_str}| {v}\n")

                    f.write("```\n\n")
            else:
                f.write("✅ 无循环依赖\n")

            # 3. 字段查找表
            f.write("## 字段查找表\n")
            f.write("| 字段名 | 能生成的MCP | 需要该字段的MCP |\n")
            f.write("|--------|-------------|----------------|\n")

            # 收集所有字段
            all_fields = set()
            for info in self.operations.values():
                all_fields.update(info["inputs"])
                all_fields.update(info["outputs"])

            for field in sorted(all_fields):
                producers = self.find_mcp_by_field(field)["produces"]
                consumers = self.find_mcp_by_field(field)["consumes"]
                f.write(f"| `{field}` | {', '.join(producers) or '无'} | {', '.join(consumers) or '无'} |\n")

        print(f"已导出LLM知识文档到: {output_file}")

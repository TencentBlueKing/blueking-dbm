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
import logging
import re
from dataclasses import asdict, is_dataclass
from typing import Any, Dict

from django.conf import settings
from django.utils.translation import gettext as _
from jinja2.sandbox import SandboxedEnvironment as Environment
from pipeline.component_framework.component import Component

from backend import env
from backend.components import JobApi
from backend.flow.consts import WINDOW_SYSTEM_JOB_USER
from backend.flow.models import FlowNode
from backend.flow.plugins.components.collections.common.base_service import BkJobService
from backend.flow.utils.script_template import sqlserver_actuator_template
from backend.flow.utils.sqlserver.encrypt import encrypt_login_password
from backend.flow.utils.sqlserver.sqlserver_act_payload import SqlserverActPayload
from backend.utils.string import base64_encode

logger = logging.getLogger("json")
cpl = re.compile("<ctx>(?P<context>.+?)</ctx>")  # 非贪婪模式，只匹配第一次出现的自定义tag


class SqlserverActuatorScriptService(BkJobService):
    """
    根据db-actuator组件，绑定fast_execute_script api接口访问。
    目前只能兼容传入一个ip执行，如果传入多ip列表模块，会有可能影响payload的拼接情况
    同时支持跨云管理，根据传入的 kwargs["bk_cloud_id"]来执行
    """

    def _execute(self, data, parent_data) -> bool:
        """
        执行fast_execute_script脚本
        global_data 单据全局变量，格式字典
        trans_data  单据上下文
        kwargs 字典传入格式：
        {
           root_id:  db-actuator任务必须参数，做录入日志平台的条件
           node_id:  db-actuator任务必须参数，做录入日志平台的条件
           node_name: db-actuator任务必须参数，做录入日志平台的条件
           get_mssql_payload_func : 表示获取执行 mssql的db-actuator 参数方法名称，对应MssqlActPayload类
           exec_ips: 表示执行的ip节点列表, 列表元素: {ip:xxx, bk_cloud_id:xxx}
           cluster: 操作的集群名称

        }
        """
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")
        kwargs = data.get_one_of_inputs("kwargs")

        root_id = kwargs["root_id"]
        node_name = kwargs["node_name"]
        node_id = kwargs["node_id"]

        exec_ips = kwargs["exec_ips"]
        if not exec_ips:
            self.log_error(_("该节点获取到执行ip信息为空，请联系系统管理员{}").format(exec_ips))
            return False

        # 获取sqlserver actuator 组件所需要执行的参数
        mssql_act_payload = SqlserverActPayload(global_data=global_data)
        if is_dataclass(trans_data):
            trans_data = asdict(trans_data)

        self.log_info(_("个性化参数体component_kwargs:{}").format(kwargs.get("component_kwargs", {})))

        db_act_template = getattr(mssql_act_payload, kwargs["get_payload_func"])(
            ips=exec_ips,
            trans_data=trans_data,
            custom_params=kwargs.get("custom_params", {}),  # todo 后续废弃
            **kwargs.get("component_kwargs", {}),
        )

        db_act_template.root_id = root_id
        db_act_template.node_id = node_id
        db_act_template.version_id = self._runtime_attrs.get("version")
        db_act_template.uid = global_data["uid"]

        # 转换兼容新版本参数传
        db_act_template.extend_payload = base64_encode(json.dumps({"extend": db_act_template.payload.extend}))

        # ------------------------------------------------------------------
        # general 段加密下发（AES-256-GCM，key_seed=node_id）
        # ------------------------------------------------------------------
        # 背景：general.runtime_account 内含 sa_pwd / drs_pwd / dbha_pwd / exporter_pwd 等
        # 敏感字段；虽然 Job 平台 script_param 已通过 is_param_sensitive=1 走加密传输，
        # 但落到目标机上会以明文进程参数展开，与"应用层加密"是正交的两层防护。
        # 加密策略：整段 runtime_account (dict) 序列化后一次性加密，密文**原地覆盖回写**
        #          general.runtime_account 字段本身——即该字段的运行时类型从 dict 变为
        #          base64 密文 string。不引入新字段，不做"置空 dict"之类的双通道兜底，
        #          Go 端按"runtime_account 为 string 则解密"的约定处理（见 dbactuator 的
        #          decryptRuntimeAccountIfNeeded），双端严格对齐、无歧义。
        # key_seed：db_act_template.node_id —— pipeline 每节点唯一，等价一次一密；
        #          Go 端 dbactuator 已经天然持有 node_id，可直接用于派生解密 key。
        # 开关：env.ENABLE_SQLSERVER_RUNTIME_ACCOUNT_ENCRYPT，当前默认 True（Go 端 26 个 action
        #      的 decryptRuntimeAccountIfNeeded 已全量落地并验证）。保留开关是为了极端应急场景下
        #      可通过环境变量快速回退到明文下发；未开启时 general.runtime_account 保持原明文 dict
        #      结构不变。注意：由于是原地覆盖，若下游存在未接入解密的 action，则该 action 会把密文
        #      string 当成 dict 反序列化直接失败——因此该开关不可在 Go 端未全量覆盖前打开。
        general_payload: Dict[str, Any] = {"general": db_act_template.payload.general}
        if env.ENABLE_SQLSERVER_RUNTIME_ACCOUNT_ENCRYPT:
            # 双端一致性 fail-fast：Go 端 decryptRuntimeAccountIfNeeded 对 nodeID == "" 已做 fail-fast，
            # Python 侧必须对称校验；否则 Python 侧会用空 seed 派生 key 加密，而 Go 端因 NodeId 非空
            # 用不同 key 解密 → GCM authentication failed，故障现象极难定位（会误导排查 SALT/编码问题）。
            if not node_id:
                raise Exception(
                    _(
                        "runtime_account 加密下发要求 node_id 非空，但当前 kwargs['node_id'] 为空/None。"
                        "请检查上游 pipeline 引擎注入是否遗漏，或临时通过 ENABLE_SQLSERVER_RUNTIME_ACCOUNT_ENCRYPT=false 回退。"
                    )
                )
            runtime_account: Dict[str, Any] = general_payload["general"].get("runtime_account") or {}
            # 加密载荷是 runtime_account dict 的 JSON 序列化字符串。JSON 契约要求（与 Go 端严格对齐）：
            #   1) 字段大小写必须与 Go 端 RuntimeAccountParam 的 json tag 完全一致（sa_pwd/drs_pwd/... 由
            #      SqlserverActPayload 统一约束，不要在此处随意 rename）；
            #   2) json.dumps 默认 ensure_ascii=True 会把非 ASCII 字符转义为 \uXXXX，Go 的 encoding/json
            #      原生兼容该转义序列，无需额外处理。
            runtime_account_encrypted: str = encrypt_login_password(
                key_seed=node_id, plain_pwd=json.dumps(runtime_account)
            )
            # 原地覆盖：runtime_account 字段类型由 dict 变为密文 string；Go 端按类型分流处理
            general_payload["general"]["runtime_account"] = runtime_account_encrypted

        general_payload_base_string = base64_encode(json.dumps(general_payload))

        # 更新节点信息
        FlowNode.objects.filter(root_id=root_id, node_id=node_id).update(hosts=exec_ips)

        # 脚本内容
        jinja_env = Environment()
        template = jinja_env.from_string(sqlserver_actuator_template)

        body = {
            "bk_scope_type": "biz_set",
            "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
            "timeout": kwargs.get("job_timeout", 3600),
            "account_alias": WINDOW_SYSTEM_JOB_USER,
            "is_param_sensitive": 1,
            "task_name": f"DBM_{node_name}_{node_id}",
            "script_content": base64_encode(template.render(asdict(db_act_template))),
            "script_language": 5,
            "target_server": {"ip_list": exec_ips},
            "script_param": base64_encode(general_payload_base_string),
        }

        if settings.DEBUG:
            # debug模式下打开
            body["is_param_sensitive"] = 0

        resp = JobApi.fast_execute_script(body, raw=True)
        self.log_debug(f"{node_name} fast execute script response: {resp}")
        self.log_info(f"job url: {self.__url__(resp['data']['job_instance_id'])}")

        # 传入调用结果，并单调监听任务状态
        data.outputs.ext_result = resp
        data.outputs.exec_ips = exec_ips
        return True


class SqlserverActuatorScriptComponent(Component):
    name = __name__
    code = "sqlserver_db_actuator_execute"
    bound_service = SqlserverActuatorScriptService

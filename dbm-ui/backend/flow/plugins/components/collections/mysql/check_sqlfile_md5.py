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
from typing import List

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend import env
from backend.components import JobApi
from backend.core.storages.storage import get_storage
from backend.flow.consts import DBA_ROOT_USER, SUCCESS_LIST
from backend.flow.models import FlowNode
from backend.flow.plugins.components.collections.common.base_service import BkJobService
from backend.flow.utils.mysql.sqlfile_md5_check import (
    MISSING_DIGEST,
    ParseFailure,
    Proceed,
    build_md5sum_script,
    compare_sqlfile_md5,
    decide_md5_check,
    parse_md5_hex,
    parse_md5_lines,
    parse_safe_filename,
)
from backend.flow.utils.redis.redis_script_template import redis_fast_execute_script_common_kwargs
from backend.utils.string import base64_encode

logger = logging.getLogger("flow")


def build_md5_check_acts(sql_files_md5, ticket_type, sql_path, targets_by_cloud, repo_path) -> List[dict]:
    decision = decide_md5_check(sql_files_md5, ticket_type)
    if not isinstance(decision, Proceed):
        logger.info(_("跳过SQL文件MD5校验: reason={}, ticket_type={}").format(decision.reason, ticket_type))
        return []

    acts = []
    for bk_cloud_id in sorted(targets_by_cloud):
        exec_targets = [{"ip": ip, "bk_cloud_id": bk_cloud_id} for ip in targets_by_cloud[bk_cloud_id]]
        acts.append(
            {
                "act_name": _("校验SQL文件MD5[云区域ID:{}]").format(bk_cloud_id),
                "act_component_code": CheckSqlFileMd5Component.code,
                "kwargs": {
                    "bk_cloud_id": bk_cloud_id,
                    "sql_path": sql_path,
                    "repo_path": repo_path,
                    "exec_targets": exec_targets,
                    "sql_files_md5": decision.sql_files_md5,
                },
                "skippable": True,
                "retryable": True,
                "error_ignorable": False,
            }
        )
    return acts


class CheckSqlFileMd5Service(BkJobService):
    def _log_invalid_expected(self, exec_targets, bk_cloud_id, sql_path, filename, expected, reason):
        targets = exec_targets or [{"ip": None}]
        for target in targets:
            self.log_error(
                _("SQL文件MD5校验失败: ip={}, bk_cloud_id={}, sql_path={}, filename={}, " "expected={}, 原因={}").format(
                    target.get("ip"), bk_cloud_id, sql_path, filename, expected, reason
                )
            )

    def _validated_expected(self, kwargs):
        exec_targets = kwargs.get("exec_targets") or []
        bk_cloud_id = kwargs.get("bk_cloud_id")
        sql_path = kwargs.get("sql_path", "")
        expected = kwargs.get("sql_files_md5") or {}
        validated = {}
        has_error = False
        for raw_filename, raw_digest in expected.items():
            filename = parse_safe_filename(raw_filename)
            if filename is None:
                self._log_invalid_expected(
                    exec_targets, bk_cloud_id, sql_path, raw_filename, raw_digest, "illegal_filename"
                )
                has_error = True
                continue
            digest = parse_md5_hex(raw_digest)
            if digest is None:
                self._log_invalid_expected(exec_targets, bk_cloud_id, sql_path, filename, raw_digest, "illegal_md5")
                has_error = True
                continue
            validated[filename] = digest
        return None if has_error else validated

    def _repo_md5_matches(self, repo_path, expected) -> bool:
        if not repo_path:
            self.log_error(_("SQL文件MD5校验失败: filename={}, 原因=repo_path_missing").format(""))
            return False

        storage = get_storage()
        actual = {}
        query_failed = False
        for filename in expected:
            repo_key = "{}/{}".format(str(repo_path).rstrip("/"), filename)
            try:
                repo_digest = parse_md5_hex(storage.get_file_md5(repo_key))
            except FileExistsError:
                actual[filename] = MISSING_DIGEST
                continue
            except Exception as err:
                query_failed = True
                self.log_error(
                    _("SQL文件MD5校验失败: filename={}, repo_path={}, 原因=repo_query_failed, 错误={}").format(
                        filename, repo_path, err
                    )
                )
                continue
            actual[filename] = repo_digest or MISSING_DIGEST

        if query_failed:
            return False

        failures = compare_sqlfile_md5(expected, actual)
        for failure in failures:
            if failure.kind == "mismatch":
                self.log_error(
                    _(
                        "SQL文件MD5校验失败: filename={}, repo_path={}, 原因=repo_mismatch, "
                        "期望MD5={}，制品库MD5={}。"
                        "SQL文件内容与提交时发生了变化，请DBA核对一遍制品库文件和提单内容。"
                        "确认没有问题后再跳过本节点"
                    ).format(failure.filename, repo_path, failure.expected, failure.actual)
                )
            else:
                self.log_error(
                    _("SQL文件MD5校验失败: filename={}, repo_path={}, 原因=repo_missing, 期望MD5={}").format(
                        failure.filename, repo_path, failure.expected
                    )
                )
        if failures:
            return False

        self.log_info(_("制品库SQL文件MD5与单据一致: repo_path={}, 文件数={}").format(repo_path, len(expected)))
        return True

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        root_id = kwargs["root_id"]
        node_name = kwargs["node_name"]
        node_id = kwargs["node_id"]
        exec_targets = kwargs.get("exec_targets") or []
        bk_cloud_id = kwargs.get("bk_cloud_id")
        sql_path = kwargs.get("sql_path", "")

        if not exec_targets:
            self.log_error(
                _("SQL文件MD5校验失败: ip={}, bk_cloud_id={}, sql_path={}, filename={}, 原因={}").format(
                    None, bk_cloud_id, sql_path, "", "empty_targets"
                )
            )
            return False

        expected = self._validated_expected(kwargs)
        if expected is None:
            return False
        if not self._repo_md5_matches(kwargs.get("repo_path", ""), expected):
            return False

        shell_script = build_md5sum_script(sql_path, list(expected))
        target_ip_info = [{"bk_cloud_id": target["bk_cloud_id"], "ip": target["ip"]} for target in exec_targets]
        exec_ips = [{"ip": target["ip"], "bk_cloud_id": target["bk_cloud_id"]} for target in exec_targets]
        FlowNode.objects.filter(root_id=root_id, node_id=node_id).update(
            hosts=[target["ip"] for target in exec_targets]
        )
        body = {
            "bk_scope_type": "biz_set",
            "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": f"DBM_{node_name}_{node_id}",
            "script_content": base64_encode(shell_script),
            "script_language": 1,
            "target_server": {"ip_list": target_ip_info},
            "account_alias": DBA_ROOT_USER,
        }
        self.log_info(_("[{}] 执行SQL文件MD5校验，目标: {}").format(node_name, target_ip_info))
        resp = JobApi.fast_execute_script({**redis_fast_execute_script_common_kwargs, **body}, raw=True)
        data.outputs.ext_result = resp
        data.outputs.exec_ips = exec_ips
        return True

    def _log_job_failure(self, job_instance_id, step_instance_id, exec_ips, node_name):
        self.log_info(_("[{}] 任务调度失败").format(node_name))
        for ip_dict in exec_ips:
            log_resp = self.__log__(job_instance_id, step_instance_id, ip_dict)
            if log_resp.get("result"):
                self.log_error("{}:{}".format(ip_dict, log_resp["data"].get("log_content", "")))

    def _log_parse_failure(self, ip_dict, bk_cloud_id, sql_path, parse_failure):
        raw_lines = parse_failure.raw_lines or ("",)
        for raw_line in raw_lines:
            self.log_error(
                _(
                    "SQL文件MD5校验失败: ip={}, bk_cloud_id={}, sql_path={}, filename={}, "
                    "原因=unparsable_output, raw_line={}"
                ).format(ip_dict["ip"], bk_cloud_id, sql_path, "", raw_line[:500])
            )

    def _verify_ip(self, job_instance_id, step_instance_id, ip_dict, expected, sql_path):
        log_resp = self.__log__(job_instance_id, step_instance_id, ip_dict)
        if not log_resp.get("result"):
            self._log_parse_failure(ip_dict, ip_dict["bk_cloud_id"], sql_path, ParseFailure(raw_lines=("",)))
            return False

        parsed = parse_md5_lines(log_resp.get("data", {}).get("log_content", ""))
        if isinstance(parsed, ParseFailure):
            self._log_parse_failure(ip_dict, ip_dict["bk_cloud_id"], sql_path, parsed)
            return False

        failures = compare_sqlfile_md5(expected, parsed)
        for failure in failures:
            if failure.kind == "mismatch":
                self.log_error(
                    _(
                        "SQL文件MD5校验失败: ip={}, bk_cloud_id={}, sql_path={}, filename={}, "
                        "原因=mismatch, 期望MD5={}，实际MD5={}。"
                        "SQL文件内容与提交时发生了变化，请DBA核对该机器上的文件内容。"
                        "确认没有问题后再跳过本节点"
                    ).format(
                        ip_dict["ip"],
                        ip_dict["bk_cloud_id"],
                        sql_path,
                        failure.filename,
                        failure.expected,
                        failure.actual,
                    )
                )
            else:
                self.log_error(
                    _("SQL文件MD5校验失败: ip={}, bk_cloud_id={}, sql_path={}, filename={}, " "原因=missing_file").format(
                        ip_dict["ip"], ip_dict["bk_cloud_id"], sql_path, failure.filename
                    )
                )
        if failures:
            return False

        filenames = sorted(expected)
        self.log_info(
            _("SQL文件MD5校验成功: ip={}, bk_cloud_id={}, 文件数={}, 文件={}").format(
                ip_dict["ip"], ip_dict["bk_cloud_id"], len(filenames), filenames
            )
        )
        return True

    def _verify_all_ips(self, job_instance_id, step_instance_id, exec_ips, kwargs):
        expected = {filename: parse_md5_hex(digest) for filename, digest in kwargs["sql_files_md5"].items()}
        results = [
            self._verify_ip(job_instance_id, step_instance_id, ip_dict, expected, kwargs["sql_path"])
            for ip_dict in exec_ips
        ]
        return all(results)

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        ext_result = data.get_one_of_outputs("ext_result")
        exec_ips = data.get_one_of_outputs("exec_ips") or []
        kwargs = data.get_one_of_inputs("kwargs")
        node_name = kwargs["node_name"]

        if isinstance(ext_result, bool):
            self.finish_schedule()
            return ext_result
        if not ext_result.get("result") or not ext_result.get("data"):
            self.log_error(_("[{}] 作业启动失败: {}").format(node_name, ext_result.get("error")))
            return False

        job_instance_id = ext_result["data"]["job_instance_id"]
        status_resp = self.__status__(job_instance_id)
        if not (status_resp.get("result") and status_resp.get("data", {}).get("finished")):
            return True

        status_data = status_resp["data"]
        step_instance_id = status_data["step_instance_list"][0]["step_instance_id"]
        if status_data["job_instance"]["status"] not in SUCCESS_LIST:
            self._log_job_failure(job_instance_id, step_instance_id, exec_ips, node_name)
            data.outputs.job_execute = False
            data.outputs.job_execute_info = {
                "job_instance_id": job_instance_id,
                "step_instance_id": step_instance_id,
            }
            self.finish_schedule()
            return False

        verified = self._verify_all_ips(job_instance_id, step_instance_id, exec_ips, kwargs)
        data.outputs.job_execute = verified
        self.finish_schedule()
        return verified

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    def outputs_format(self) -> List:
        return [Service.OutputItem(name="exec_ips", key="exec_ips", type="list")]


class CheckSqlFileMd5Component(Component):
    name = __name__
    code = "mysql_check_sqlfile_md5"
    bound_service = CheckSqlFileMd5Service

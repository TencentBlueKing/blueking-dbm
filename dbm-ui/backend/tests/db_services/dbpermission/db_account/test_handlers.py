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

from unittest.mock import MagicMock

import pytest

from backend.db_services.dbpermission.constants import AccountType, RuleActionType
from backend.db_services.dbpermission.db_account.dataclass import (
    AccountMeta,
    AccountPrivMeta,
    AccountRuleMeta,
    AccountUserMeta,
)
from backend.db_services.dbpermission.db_account.handlers import AccountHandler
from backend.db_services.mysql.permission.exceptions import DBPermissionBaseException


@pytest.fixture
def account_handler():
    return AccountHandler(bk_biz_id=1, account_type=AccountType.MYSQL.value, operator="tester")


def test_create_account_triggers_signal(monkeypatch, account_handler):
    account = AccountMeta(user="foo", password="bar")
    create_resp = {"message": "created"}
    account_payload = {"results": [{"user": "foo", "password": "bar"}]}

    create_mock = MagicMock(return_value=create_resp)
    get_mock = MagicMock(return_value=account_payload)
    signal_mock = MagicMock()

    monkeypatch.setattr(
        "backend.db_services.dbpermission.db_account.handlers.DBPrivManagerApi.create_account", create_mock
    )
    monkeypatch.setattr("backend.db_services.dbpermission.db_account.handlers.DBPrivManagerApi.get_account", get_mock)

    resp = account_handler.create_account(account)

    assert resp == create_resp
    create_mock.assert_called_once_with(
        {
            "cluster_type": AccountType.MYSQL.value,
            "bk_biz_id": 1,
            "operator": "tester",
            "user": "foo",
            "psw": "bar",
        }
    )
    get_mock.assert_called_once_with(
        params={"bk_biz_id": 1, "cluster_type": AccountType.MYSQL.value, "user_like": "foo"}
    )
    assert signal_mock.send.call_args.kwargs["account"]["user"] == "foo"


def test_list_account_rules_formats_response(monkeypatch, account_handler):
    ticket = MagicMock()
    ticket.details = {"rule_id": 201, "action": RuleActionType.CHANGE.value}
    ticket.id = 99

    ticket_manager = MagicMock()
    ticket_manager.objects.filter.return_value = [ticket]
    monkeypatch.setattr("backend.db_services.dbpermission.db_account.handlers.Ticket", ticket_manager)

    api_response = {
        "count": 2,
        "items": [
            {
                "account": {"id": 101, "user": "foo"},
                "rules": [
                    {"id": 201, "dbname": "db1", "priv": "select", "account_id": 31},
                    {"id": 202, "dbname": "db2", "priv": "update", "account_id": 31},
                ],
            },
            {"account": {"id": 102, "user": "bar"}, "rules": None},
        ],
    }

    list_mock = MagicMock(return_value=api_response)
    monkeypatch.setattr(
        "backend.db_services.dbpermission.db_account.handlers.DBPrivManagerApi.list_account_rules", list_mock
    )

    result = account_handler.list_account_rules(AccountRuleMeta(user="foo"))

    list_mock.assert_called_once()
    passed_params = list_mock.call_args.args[0]
    assert passed_params == {"user": "foo", "no_rule_user": True, "bk_biz_id": 1}
    assert result["count"] == 2
    first_account = result["results"][0]
    assert first_account["account"]["account_id"] == 101
    first_rule, second_rule = first_account["rules"]
    assert first_rule["priv_ticket"] == {"action": RuleActionType.CHANGE.value, "ticket_id": 99}
    assert first_rule["access_db"] == "db1"
    assert second_rule["priv_ticket"] == {}
    assert result["results"][1]["rules"] == []


def test_query_account_rules_filters_access_db(monkeypatch, account_handler):
    ticket_manager = MagicMock()
    ticket_manager.objects.filter.return_value = []
    monkeypatch.setattr("backend.db_services.dbpermission.db_account.handlers.Ticket", ticket_manager)

    api_response = {
        "count": 1,
        "items": [
            {
                "account": {"id": 101, "user": "foo"},
                "rules": [
                    {"id": 201, "dbname": "db1", "priv": "select", "account_id": 31},
                    {"id": 202, "dbname": "db2", "priv": "update", "account_id": 31},
                ],
            }
        ],
    }

    list_mock = MagicMock(return_value=api_response)
    monkeypatch.setattr(
        "backend.db_services.dbpermission.db_account.handlers.DBPrivManagerApi.list_account_rules", list_mock
    )

    meta = AccountRuleMeta(user="foo", access_dbs=["db1"])
    result = account_handler.query_account_rules(meta)

    assert result["count"] == 1
    rules = result["results"][0]["rules"]
    assert len(rules) == 1
    assert rules[0]["access_db"] == "db1"


def test_query_account_rules_when_no_items(monkeypatch, account_handler):
    list_mock = MagicMock(return_value={"items": []})
    monkeypatch.setattr(
        "backend.db_services.dbpermission.db_account.handlers.DBPrivManagerApi.list_account_rules", list_mock
    )

    result = account_handler.query_account_rules(AccountRuleMeta(user="foo"))
    assert result == {"count": 0, "results": []}


def test_list_account_rules_when_no_items(monkeypatch, account_handler):
    list_mock = MagicMock(return_value={"items": []})
    monkeypatch.setattr(
        "backend.db_services.dbpermission.db_account.handlers.DBPrivManagerApi.list_account_rules", list_mock
    )

    result = account_handler.list_account_rules(AccountRuleMeta(user="foo"))
    assert result == {"count": 0, "results": []}


def test_delete_account_rule_referenced(monkeypatch, account_handler):
    config_instance = MagicMock()
    config_instance.exists.return_value = True
    config_instance.first.return_value.config_name = "template"

    config_manager = MagicMock()
    config_manager.objects.filter.return_value = config_instance
    monkeypatch.setattr("backend.db_services.dbpermission.db_account.handlers.TendbOpenAreaConfig", config_manager)

    with pytest.raises(DBPermissionBaseException):
        account_handler.delete_account_rule(AccountRuleMeta(rule_id=1, account_id=2))


def test_delete_account_rule_success(monkeypatch, account_handler):
    config_instance = MagicMock()
    config_instance.exists.return_value = False

    config_manager = MagicMock()
    config_manager.objects.filter.return_value = config_instance
    monkeypatch.setattr("backend.db_services.dbpermission.db_account.handlers.TendbOpenAreaConfig", config_manager)

    delete_mock = MagicMock(return_value="ok")
    monkeypatch.setattr(
        "backend.db_services.dbpermission.db_account.handlers.DBPrivManagerApi.delete_account_rule", delete_mock
    )

    log_mock = MagicMock()
    monkeypatch.setattr("backend.db_services.dbpermission.db_account.handlers.DBRuleActionLog", log_mock)

    resp = account_handler.delete_account_rule(AccountRuleMeta(rule_id=1, account_id=2))
    assert resp == "ok"
    delete_mock.assert_called_once_with(
        {
            "bk_biz_id": 1,
            "operator": "tester",
            "cluster_type": AccountType.MYSQL.value,
            "id": [1],
        }
    )
    log_mock.create_log.assert_called_once_with(2, 1, "tester", action=RuleActionType.DELETE)


def test_get_account_privs_with_pagination(monkeypatch, account_handler):
    privs_response = {
        "privs_for_ip": [
            {
                "ip": "1.1.1.1",
                "dbs": [
                    {
                        "db": "db1",
                        "domains": [
                            {
                                "immute_domain": "d1",
                                "users": [
                                    {"user": "user1", "match_ips": ["1.1.1.1", "1.1.1.2"]},
                                    {"user": "user2", "match_ips": ["1.1.1.3"]},
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
        "download": [],
    }

    priv_mock = MagicMock(return_value=privs_response)
    monkeypatch.setattr("backend.db_services.dbpermission.db_account.handlers.DBPrivManagerApi.get_priv", priv_mock)

    meta = AccountPrivMeta(format_type="ip", offset=0, limit=2)
    result = account_handler.get_account_privs(meta)

    assert result["match_ips_count"] == 3
    privs = result["results"]["privs_for_ip"][0]["dbs"][0]["domains"][0]["users"][0]["match_ips"]
    assert privs == ["1.1.1.1", "1.1.1.2"]


def test_get_account_privs_when_empty(monkeypatch, account_handler):
    priv_mock = MagicMock(return_value={"privs_for_ip": [], "download": []})
    monkeypatch.setattr("backend.db_services.dbpermission.db_account.handlers.DBPrivManagerApi.get_priv", priv_mock)

    meta = AccountPrivMeta(format_type="ip", offset=0, limit=10)
    result = account_handler.get_account_privs(meta)
    assert result == {"match_ips_count": 0, "results": {"privs_for_ip": [], "download": []}}


def test_get_download_privs(monkeypatch, account_handler):
    download_data = {
        "download": [
            {
                "ip": "1.1.1.1",
                "immute_domain": "d1",
                "user": "user1",
                "match_ip": "1.1.1.1",
                "privs": [
                    {"match_db": "db1", "priv": "select"},
                    {"match_db": "db2", "priv": "update"},
                ],
            }
        ]
    }

    priv_mock = MagicMock(return_value=download_data)
    serialize_mock = MagicMock(return_value="workbook")
    response_mock = MagicMock(return_value="response")

    monkeypatch.setattr("backend.db_services.dbpermission.db_account.handlers.DBPrivManagerApi.get_priv", priv_mock)
    monkeypatch.setattr("backend.db_services.dbpermission.db_account.handlers.ExcelHandler.serialize", serialize_mock)
    monkeypatch.setattr("backend.db_services.dbpermission.db_account.handlers.ExcelHandler.response", response_mock)

    resp = account_handler.get_download_privs(AccountPrivMeta(format_type="ip"))

    flattened = serialize_mock.call_args.args[0]
    assert flattened == [
        {
            "ip": "1.1.1.1",
            "immute_domain": "d1",
            "user": "user1",
            "match_ip": "1.1.1.1",
            "match_db": "db1",
            "priv": "select",
        },
        {
            "ip": "1.1.1.1",
            "immute_domain": "d1",
            "user": "user1",
            "match_ip": "1.1.1.1",
            "match_db": "db2",
            "priv": "update",
        },
    ]
    assert serialize_mock.call_count == 1
    assert serialize_mock.call_args.kwargs["match_header"] is False
    response_mock.assert_called_once_with("workbook", "privs.xlsx")
    assert resp == "response"


def test_get_account_users(monkeypatch, account_handler):
    user_list = {"count": 1, "items": [{"user": "foo"}]}
    user_mock = MagicMock(return_value=user_list)
    monkeypatch.setattr(
        "backend.db_services.dbpermission.db_account.handlers.DBPrivManagerApi.get_user_list", user_mock
    )

    meta = AccountUserMeta(ips=["1.1.1.1"], immute_domains=["d1"], cluster_type="mysql")
    result = account_handler.get_account_users(meta)

    assert result == {"count": 1, "results": [{"user": "foo"}]}


def test_aggregate_user_db_rules(monkeypatch):
    api_response = {
        "items": [
            {
                "account": {"user": "foo"},
                "rules": [
                    {"dbname": "db1", "priv": "select"},
                    {"dbname": "db2", "priv": "update"},
                ],
            }
        ]
    }

    list_mock = MagicMock(return_value=api_response)
    monkeypatch.setattr(
        "backend.db_services.dbpermission.db_account.handlers.DBPrivManagerApi.list_account_rules", list_mock
    )

    result = AccountHandler.aggregate_user_db_rules(1, AccountType.MYSQL.value)

    assert result == {"foo": {"db1": "select", "db2": "update"}}
    list_mock.assert_called_once_with({"bk_biz_id": 1, "cluster_type": AccountType.MYSQL.value})

# -*- coding: utf-8 -*-
from unittest.mock import patch

from backend.flow.plugins.components.collections.mongodb.delete_domain_from_dns import ExecDeleteDomainFromDnsOperation
from backend.flow.plugins.components.collections.mongodb.delete_password_from_db import (
    ExecDeletePasswordFromDBOperation,
)


class FakeData:
    def __init__(self, inputs):
        self.inputs = inputs

    def get_one_of_inputs(self, key):
        return self.inputs[key]


def test_delete_domain_logs_plan_and_result():
    service = ExecDeleteDomainFromDnsOperation()
    kwargs = {
        "bk_biz_id": 3,
        "bk_cloud_id": 0,
        "del_domains": [
            {
                "domain": "m1.cyc30rs1.dba.db",
                "del_instance_list": ["127.0.0.1#27001"],
            }
        ],
    }

    with patch(
        "backend.flow.plugins.components.collections.mongodb.delete_domain_from_dns.dns_manage.DnsManage"
    ) as mock_dns:
        mock_dns.return_value.remove_domain_ip.return_value = True
        with patch.object(service, "log_info") as mock_log_info:
            assert service._execute(FakeData({"kwargs": kwargs}), None) is True

    logs = [call.args[0] for call in mock_log_info.call_args_list]
    assert any("[mongo deinstall dns] bk_biz_id=3" in line for line in logs)
    assert any("domain=m1.cyc30rs1.dba.db" in line for line in logs)
    assert any("[mongo deinstall dns] removed domain=m1.cyc30rs1.dba.db" in line for line in logs)
    assert any("[mongo deinstall dns] done, domains=1" in line for line in logs)


def test_delete_password_logs_plan_and_result():
    service = ExecDeletePasswordFromDBOperation()
    kwargs = {
        "instances": [{"ip": "127.0.0.1", "port": 27001, "bk_cloud_id": 0}],
        "usernames": ["dba"],
    }

    with patch(
        "backend.flow.plugins.components.collections.mongodb.delete_password_from_db.MongoDBPassword"
    ) as mock_pwd:
        mock_pwd.return_value.delete_password_from_db.return_value = None
        with patch.object(service, "log_info") as mock_log_info:
            assert service._execute(FakeData({"kwargs": kwargs}), None) is True

    logs = [call.args[0] for call in mock_log_info.call_args_list]
    assert any("[mongo deinstall password] usernames=[dba]" in line for line in logs)
    assert any("127.0.0.1:27001" in line for line in logs)
    assert any("[mongo deinstall password] done usernames=[dba] instances=1" in line for line in logs)

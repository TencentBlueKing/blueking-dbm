from unittest.mock import Mock, patch

import pytest
from rest_framework.exceptions import ValidationError

from backend.db_package.filters import PackageListFilter
from backend.db_package.models import Package
from backend.db_package.views import DBPackageViewSet
from backend.db_services.risk_memo.filters import RiskOpRecordListFilter
from backend.db_services.risk_memo.models.risk_memo import RiskMemo, RiskOperateRecord
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.ticket import TicketListPermission
from backend.ticket.filters import TicketListFilter
from backend.ticket.models import Ticket


@pytest.mark.parametrize("db_type", [None, "", "   "])
def test_package_list_requires_db_type(db_type):
    request = Mock(query_params={} if db_type is None else {"db_type": db_type})
    with pytest.raises(ValidationError):
        DBPackageViewSet.instance_getter(request, Mock(action="list"))


def test_package_list_checks_manage_permission_for_db_type():
    view = DBPackageViewSet()
    view.action = "list"
    assert all("list" not in actions for actions in view.get_action_permission_map())
    permission = view.get_default_permission_class()[0]
    assert permission.actions == [ActionEnum.PACKAGE_MANAGE]
    assert permission.instance_ids_getter(Mock(query_params={"db_type": "mysql"}), view) == ["mysql"]
    with patch("backend.iam_app.handlers.drf_perm.base.Permission") as iam:
        request = Mock(query_params={"db_type": "mysql"})
        request.user.is_superuser = False
        request.method = "GET"
        view.kwargs = {}
        with patch("backend.iam_app.handlers.drf_perm.base.env.BK_IAM_SKIP", False):
            assert permission.has_permission(request, view)
        iam.return_value.is_allowed.assert_called_once_with(
            action=ActionEnum.PACKAGE_MANAGE, resources=permission.resources[0], is_raise_exception=True
        )


@pytest.mark.parametrize("filter_class,model", [(RiskOpRecordListFilter, RiskOperateRecord)])
@pytest.mark.parametrize(
    "data,valid", [({}, False), ({"bk_biz_id": ""}, False), ({"bk_biz_id": "abc"}, False), ({"bk_biz_id": "2"}, True)]
)
def test_business_id_required(filter_class, model, data, valid):
    query_filter = filter_class(data=data, queryset=model.objects.none())
    assert query_filter.is_valid() is valid


@pytest.mark.parametrize("platform_manage", [True, False])
@pytest.mark.parametrize(
    "data", [{}, {"bk_biz_ids": "2,3"}, {"bk_biz_id": ""}, {"bk_biz_id": "abc"}, {"bk_biz_id": "2"}]
)
def test_ticket_business_id_permission(platform_manage, data):
    request = Mock(query_params=data)
    request.user.username = "admin"
    with patch("backend.iam_app.handlers.drf_perm.ticket.Permission") as permission:
        permission.return_value.is_allowed.return_value = platform_manage
        assert TicketListPermission().has_permission(request, Mock()) is ("bk_biz_id" in data or platform_manage)
        query_filter = TicketListFilter(data=data, queryset=Ticket.objects.none(), request=request)
        assert query_filter.is_valid() is ("bk_biz_id" not in data or data.get("bk_biz_id") == "2")
        if "bk_biz_id" not in data:
            permission.return_value.is_allowed.assert_called_once_with(action=ActionEnum.PLATFORM_MANAGE, resources=[])
        else:
            permission.assert_not_called()


@pytest.mark.parametrize("status", ["APPROVE", "TODO", "RESOURCE_REPLENISH", "FAILED", "INNER_TODO", "TIMER"])
@pytest.mark.parametrize("is_assist", [None, "false", "true"])
@pytest.mark.parametrize("business_id", [None, "", "abc", "2.5", "2"])
def test_personal_todo_business_id_optional(status, is_assist, business_id):
    data = {"status": status, "todo": "running"}
    if is_assist is not None:
        data["is_assist"] = is_assist
    if business_id is not None:
        data["bk_biz_id"] = business_id
    with patch("backend.iam_app.handlers.drf_perm.ticket.Permission") as permission:
        request = Mock(query_params=data)
        assert TicketListPermission().has_permission(request, Mock())
        query_filter = TicketListFilter(data=data, queryset=Ticket.objects.none(), request=Mock())
        assert query_filter.is_valid() is (business_id in (None, "2"))
        permission.assert_not_called()


@pytest.mark.parametrize(
    "data",
    [
        {"status": "APPROVE"},
        {"creator": "another-user"},
        {"creator": ""},
        {"creator__in": "admin,another-user"},
    ],
)
def test_other_ticket_queries_require_business_id(data):
    request = Mock(query_params=data)
    request.user.username = "admin"
    with patch("backend.iam_app.handlers.drf_perm.ticket.Permission") as permission:
        permission.return_value.is_allowed.return_value = False
        assert not TicketListPermission().has_permission(request, Mock())
        permission.return_value.is_allowed.assert_called_once_with(action=ActionEnum.PLATFORM_MANAGE, resources=[])


@pytest.mark.parametrize(
    "data",
    [
        {"creator": "admin"},
        {"todo": "done"},
        {"todo": "running"},
        {"todo": ""},
        {"todo": "unknown"},
        {"status": "APPROVE", "todo": "done"},
        {"status": "SUCCEEDED", "todo": "running"},
        {"status": "APPROVE,SUCCEEDED", "todo": "running"},
    ],
)
@pytest.mark.parametrize("business_id", [None, "", "abc", "2.5", "2"])
def test_personal_ticket_queries_business_id_optional(data, business_id):
    data = dict(data)
    if business_id is not None:
        data["bk_biz_id"] = business_id
    request = Mock(query_params=data)
    request.user.username = "admin"
    with patch("backend.iam_app.handlers.drf_perm.ticket.Permission") as permission:
        assert TicketListPermission().has_permission(request, Mock())
        query_filter = TicketListFilter(data=data, queryset=Ticket.objects.none(), request=request)
        assert query_filter.is_valid() is (business_id in (None, "2"))
        permission.assert_not_called()


@pytest.mark.django_db
def test_risk_records_filtered_by_business():
    records = []
    for bk_biz_id in [2, 3]:
        risk = RiskMemo.objects.create(name=f"business-filter-{bk_biz_id}", bk_biz_id=bk_biz_id)
        records.append(RiskOperateRecord.objects.create(risk=risk, oper_type="create_risk"))

    query_filter = RiskOpRecordListFilter(
        data={"bk_biz_id": "2"}, queryset=RiskOperateRecord.objects.filter(pk__in=[record.pk for record in records])
    )
    assert query_filter.is_valid()
    assert list(query_filter.qs.values_list("pk", flat=True)) == [records[0].pk]


@pytest.mark.django_db
@pytest.mark.parametrize("data", [{"db_type": "mysql"}, {"db_type": "mysql", "bk_biz_id": "2"}])
def test_package_list_not_filtered_by_business(data):
    packages = [
        Package.objects.create(name=f"business-filter-{index}", size=1, db_type="mysql", allow_biz_ids=allowed)
        for index, allowed in enumerate([None, [], [2], [2, 3], [3], ["2"]])
    ]
    query_filter = PackageListFilter(
        data=data, queryset=Package.objects.filter(pk__in=[package.pk for package in packages])
    )
    assert query_filter.is_valid()
    assert set(query_filter.qs.values_list("pk", flat=True)) == {package.pk for package in packages}


@pytest.mark.parametrize(
    "filter_class,model",
    [(TicketListFilter, Ticket), (RiskOpRecordListFilter, RiskOperateRecord)],
)
def test_business_id_rejects_fraction(filter_class, model):
    query_filter = filter_class(data={"bk_biz_id": "2.5"}, queryset=model.objects.none())
    assert not query_filter.is_valid()

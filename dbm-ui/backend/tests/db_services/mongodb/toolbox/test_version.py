# -*- coding: utf-8 -*-
from types import SimpleNamespace

import pytest
from rest_framework.exceptions import ValidationError

from backend.db_services.mongodb.toolbox.handlers import ToolboxHandler
from backend.db_services.mongodb.toolbox.serializers import ListAvailableVersionSerializer


class _FakePackageQuerySet(list):
    def order_by(self, *args, **kwargs):
        return self


class _FakePackageManager:
    def __init__(self, packages):
        self._packages = packages

    def filter(self, **kwargs):
        return _FakePackageQuerySet(self._packages)


def test_list_available_versions_from_4_4_success(monkeypatch):
    monkeypatch.setattr(
        "backend.db_services.mongodb.toolbox.handlers.Cluster.objects.filter",
        lambda **kwargs: [SimpleNamespace(id=100, major_version="MongoDB-4.4")],
    )
    monkeypatch.setattr(
        "backend.db_services.mongodb.toolbox.handlers.Package.objects",
        _FakePackageManager(
            [
                SimpleNamespace(version="mongodb-7.0.3"),
                SimpleNamespace(version="mongodb-6.0.9"),
                SimpleNamespace(version="mongodb-5.0.14"),
                SimpleNamespace(version="mongodb-5.0.3"),
                SimpleNamespace(version="mongodb-4.4.18"),
            ]
        ),
    )

    data = ToolboxHandler(bk_biz_id=1).list_available_versions(cluster_ids=[100])
    assert data == [
        {"major": "mongodb-4.4", "full_list": ["mongodb-4.4.18"]},
        {"major": "mongodb-5.0", "full_list": ["mongodb-5.0.3", "mongodb-5.0.14"]},
        {"major": "mongodb-6.0", "full_list": ["mongodb-6.0.9"]},
        {"major": "mongodb-7.0", "full_list": ["mongodb-7.0.3"]},
    ]


def test_list_available_versions_same_line_and_higher_lines(monkeypatch):
    monkeypatch.setattr(
        "backend.db_services.mongodb.toolbox.handlers.Cluster.objects.filter",
        lambda **kwargs: [SimpleNamespace(id=100, major_version="MongoDB-5.0.4")],
    )
    monkeypatch.setattr(
        "backend.db_services.mongodb.toolbox.handlers.Package.objects",
        _FakePackageManager(
            [
                SimpleNamespace(version="mongodb-7.0.3"),
                SimpleNamespace(version="mongodb-5.0.14"),
                SimpleNamespace(version="mongodb-5.0.9"),
                SimpleNamespace(version="mongodb-5.0.4"),
                SimpleNamespace(version="mongodb-4.4.18"),
            ]
        ),
    )

    data = ToolboxHandler(bk_biz_id=1).list_available_versions(cluster_ids=[100])
    assert data == [
        {"major": "mongodb-5.0", "full_list": ["mongodb-5.0.9", "mongodb-5.0.14"]},
        {"major": "mongodb-7.0", "full_list": ["mongodb-7.0.3"]},
    ]


def test_list_available_versions_when_no_higher_version(monkeypatch):
    monkeypatch.setattr(
        "backend.db_services.mongodb.toolbox.handlers.Cluster.objects.filter",
        lambda **kwargs: [SimpleNamespace(id=100, major_version="MongoDB-7.0")],
    )
    monkeypatch.setattr(
        "backend.db_services.mongodb.toolbox.handlers.Package.objects",
        _FakePackageManager(
            [
                SimpleNamespace(version="mongodb-7.0.0"),
                SimpleNamespace(version="mongodb-6.0.9"),
            ]
        ),
    )

    data = ToolboxHandler(bk_biz_id=1).list_available_versions(cluster_ids=[100])
    assert data == []


def test_list_available_versions_raise_for_unsupported_current_version(monkeypatch):
    monkeypatch.setattr(
        "backend.db_services.mongodb.toolbox.handlers.Cluster.objects.filter",
        lambda **kwargs: [SimpleNamespace(id=100, major_version="MongoDB-2.6")],
    )

    with pytest.raises(ValidationError):
        ToolboxHandler(bk_biz_id=1).list_available_versions(cluster_ids=[100])


def test_list_available_version_serializer_require_cluster_ids():
    serializer = ListAvailableVersionSerializer(data={})
    assert not serializer.is_valid()
    assert "cluster_ids" in serializer.errors


def test_list_available_version_serializer_accepts_cluster_ids_only():
    serializer = ListAvailableVersionSerializer(data={"cluster_ids": [1]})
    assert serializer.is_valid()
    assert serializer.validated_data == {"cluster_ids": [1]}


def test_list_available_versions_major_intersection(monkeypatch):
    monkeypatch.setattr(
        "backend.db_services.mongodb.toolbox.handlers.Cluster.objects.filter",
        lambda **kwargs: [
            SimpleNamespace(id=100, major_version="MongoDB-4.4"),
            SimpleNamespace(id=101, major_version="MongoDB-5.0"),
        ],
    )
    monkeypatch.setattr(
        "backend.db_services.mongodb.toolbox.handlers.Package.objects",
        _FakePackageManager(
            [
                SimpleNamespace(version="mongodb-7.0.3"),
                SimpleNamespace(version="mongodb-6.0.9"),
                SimpleNamespace(version="mongodb-5.0.14"),
            ]
        ),
    )

    data = ToolboxHandler(bk_biz_id=1).list_available_versions(cluster_ids=[100, 101])
    assert data == [
        {"major": "mongodb-5.0", "full_list": ["mongodb-5.0.14"]},
        {"major": "mongodb-6.0", "full_list": ["mongodb-6.0.9"]},
        {"major": "mongodb-7.0", "full_list": ["mongodb-7.0.3"]},
    ]


def test_list_available_versions_raise_for_missing_cluster(monkeypatch):
    monkeypatch.setattr(
        "backend.db_services.mongodb.toolbox.handlers.Cluster.objects.filter",
        lambda **kwargs: [SimpleNamespace(id=100, major_version="MongoDB-4.4")],
    )

    with pytest.raises(ValidationError):
        ToolboxHandler(bk_biz_id=1).list_available_versions(cluster_ids=[100, 101])

# -*- coding: utf-8 -*-
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from backend.db_package.constants import PackageType
from backend.db_services.version.utils import (
    _normalize_mongodb_list_version,
    query_mongodb_versions,
    strip_full_version,
)


@pytest.mark.parametrize(
    "full_version,display_seg,expected",
    [
        ("4.2.24.0.0.0", 3, "4.2.24"),
        ("4.2.24", 3, "4.2.24"),
        ("", 3, ""),
    ],
)
def test_strip_full_version(full_version, display_seg, expected):
    assert strip_full_version(full_version, display_seg) == expected


@patch("backend.db_services.version.utils.Package.objects")
@patch("backend.db_services.version.utils.DBVersion.objects")
@patch("backend.db_services.version.utils.Distribution.objects")
def test_query_mongodb_versions_only_enabled_and_short_format(
    mock_distribution_objects, mock_dbversion_objects, mock_package_objects
):
    mock_distribution_objects.filter.return_value.values_list.return_value = [1]
    mock_dbversion_objects.filter.return_value.order_by.return_value.values_list.return_value = [
        "3.4.24.0.0.0",
        "5.0.28.0.0.0",
        "4.2.24.0.0.0",
        "4.2.24.0.0.0",
    ]

    versions = query_mongodb_versions()

    mock_distribution_objects.filter.assert_called_once_with(pkg_type=PackageType.MongoDB)
    mock_dbversion_objects.filter.return_value.order_by.assert_called_once_with("-full_version")
    mock_dbversion_objects.filter.assert_called_once_with(distribution_id__in=[1], enable=True)
    mock_package_objects.filter.assert_not_called()
    assert versions == ["5.0.28", "4.2.24", "3.4.24"]


@patch("backend.db_services.version.utils.Package.objects")
@patch("backend.db_services.version.utils.DBVersion.objects")
@patch("backend.db_services.version.utils.Distribution.objects")
def test_query_mongodb_versions_fallback_to_package(
    mock_distribution_objects, mock_dbversion_objects, mock_package_objects
):
    mock_distribution_objects.filter.return_value.values_list.return_value = []
    empty_qs = MagicMock()
    empty_qs.order_by.return_value.values_list.return_value = []
    mock_dbversion_objects.filter.return_value.order_by.return_value = empty_qs

    packages = [
        SimpleNamespace(version="3.4.24.0.0.0", db_version=None),
        SimpleNamespace(version="5.0.28.0.0.0", db_version=None),
    ]
    package_qs = MagicMock()
    package_qs.select_related.return_value = packages
    mock_package_objects.filter.return_value = package_qs

    versions = query_mongodb_versions()

    mock_package_objects.filter.assert_called_once_with(pkg_type=PackageType.MongoDB, enable=True)
    package_qs.select_related.assert_called_once_with("db_version")
    assert versions == ["5.0.28", "3.4.24"]


@patch("backend.db_services.version.utils.Package.objects")
@patch("backend.db_services.version.utils.DBVersion.objects")
@patch("backend.db_services.version.utils.Distribution.objects")
def test_query_mongodb_versions_fallback_resolves_series_via_db_version(
    mock_distribution_objects, mock_dbversion_objects, mock_package_objects
):
    mock_distribution_objects.filter.return_value.values_list.return_value = []
    empty_qs = MagicMock()
    empty_qs.order_by.return_value.values_list.return_value = []
    mock_dbversion_objects.filter.return_value.order_by.return_value = empty_qs

    packages = [
        SimpleNamespace(
            version="mongodb-7.0",
            db_version=SimpleNamespace(base_version="7.0.28", name="mongodb-7.0.28"),
            db_version_id=14,
        ),
        SimpleNamespace(version="mongodb-7.0", db_version=None, db_version_id=None),
    ]
    package_qs = MagicMock()
    package_qs.select_related.return_value = packages
    mock_package_objects.filter.return_value = package_qs

    versions = query_mongodb_versions()
    assert versions == ["7.0.28"]


@patch("backend.db_services.version.utils.Package.objects")
@patch("backend.db_services.version.utils.DBVersion.objects")
@patch("backend.db_services.version.utils.Distribution.objects")
def test_query_mongodb_versions_skips_legacy_package_version(
    mock_distribution_objects, mock_dbversion_objects, mock_package_objects
):
    mock_distribution_objects.filter.return_value.values_list.return_value = []
    empty_qs = MagicMock()
    empty_qs.order_by.return_value.values_list.return_value = []
    mock_dbversion_objects.filter.return_value.order_by.return_value = empty_qs

    packages = [
        SimpleNamespace(version="percona_mongodb-4", db_version=None),
        SimpleNamespace(version="5.0.28.0.0.0", db_version=None),
    ]
    package_qs = MagicMock()
    package_qs.select_related.return_value = packages
    mock_package_objects.filter.return_value = package_qs

    versions = query_mongodb_versions()

    assert versions == ["5.0.28"]
    assert _normalize_mongodb_list_version("percona_mongodb-4") is None
    assert _normalize_mongodb_list_version("4.2.24.0.0.0") == "4.2.24"
    assert _normalize_mongodb_list_version("mongodb-5.0.28") == "5.0.28"

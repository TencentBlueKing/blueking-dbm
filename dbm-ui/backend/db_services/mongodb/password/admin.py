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
from backend.flow.consts import MongoDBDefaultUser, MongoDBManagerUser
from backend.flow.utils.mongodb import mongodb_password
from django.contrib import admin

from .models.password import MongoDBPassword


class FakeQuery:
    """Fake Query object to mimic Django QuerySet behavior"""

    def __init__(self, model):
        self.model = model
        self.order_by = []  # Order by fields
        self.select_related = {}  # Select related fields
        self.where = None  # WHERE clause
        self.distinct = False  # Distinct flag
        self.group_by = None  # GROUP BY clause

    def clone(self):
        """Clone the query object"""
        return FakeQuery(self.model)


class ExternalDataQuerySet:
    """Fake QuerySet to display external data in Django Admin"""

    def __init__(self, model, data_list=None):
        self.model = model
        self._data = data_list or []
        self._offset = 0
        self._limit = None
        self._order_by_fields = []
        # Attributes required by Django Admin
        self.query = FakeQuery(model)
        self.db = "default"
        self.ordered = True

    def __iter__(self):
        return iter(self._get_data())

    def __getitem__(self, k):
        data = self._get_data()
        if isinstance(k, slice):
            # Handle slicing operation (pagination)
            start = k.start or 0
            stop = k.stop
            new_qs = ExternalDataQuerySet(self.model, self._data)
            new_qs._offset = start
            new_qs._limit = (stop - start) if stop else None
            new_qs._order_by_fields = self._order_by_fields
            return new_qs
        return data[k]

    def __len__(self):
        return len(self._data)

    def __bool__(self):
        return len(self._data) > 0

    def count(self):
        return len(self._data)

    def _get_data(self):
        """Get processed data with support for slicing and sorting"""
        data = self._data

        # Simple sorting implementation
        if self._order_by_fields:
            for field in reversed(self._order_by_fields):
                reverse = field.startswith("-")
                field_name = field.lstrip("-")

                # Safe sorting: handle None values and incomparable types
                def safe_sort_key(obj):
                    value = getattr(obj, field_name, None)
                    # Convert None to empty string or 0 to ensure sortability
                    if value is None:
                        return ""
                    # Keep numeric types as is
                    if isinstance(value, (int, float)):
                        return value
                    # Convert other types to string
                    return str(value)

                try:
                    data = sorted(data, key=safe_sort_key, reverse=reverse)
                except Exception as e:
                    # Log error but don't interrupt if sorting fails
                    import logging

                    logging.warning(f"Sorting failed, field: {field_name}, error: {e}")

        # Slicing
        if self._limit is not None:
            return data[self._offset : self._offset + self._limit]
        return data[self._offset :]

    def all(self):
        """Return all data"""
        return self

    def _clone(self):
        """Clone the current QuerySet"""
        new_qs = ExternalDataQuerySet(self.model, self._data)
        new_qs._offset = self._offset
        new_qs._limit = self._limit
        new_qs._order_by_fields = self._order_by_fields[:]
        return new_qs

    def order_by(self, *fields):
        """Support for ordering"""
        new_qs = self._clone()
        new_qs._order_by_fields = list(fields)
        return new_qs

    def filter(self, **kwargs):
        """Simple filter implementation"""
        if not kwargs:
            return self._clone()

        filtered_data = []
        for obj in self._data:
            match = True
            for key, value in kwargs.items():
                if not hasattr(obj, key) or getattr(obj, key) != value:
                    match = False
                    break
            if match:
                filtered_data.append(obj)

        new_qs = self._clone()
        new_qs._data = filtered_data
        return new_qs

    def exclude(self, **kwargs):
        """Exclude certain data"""
        if not kwargs:
            return self._clone()

        filtered_data = []
        for obj in self._data:
            match = False
            for key, value in kwargs.items():
                if hasattr(obj, key) and getattr(obj, key) == value:
                    match = True
                    break
            if not match:
                filtered_data.append(obj)

        new_qs = self._clone()
        new_qs._data = filtered_data
        return new_qs

    def distinct(self):
        """Return deduplicated data"""
        return self._clone()

    def select_related(self, *fields):
        """Simulate select_related (not needed for external data)"""
        return self._clone()

    def prefetch_related(self, *fields):
        """Simulate prefetch_related (not needed for external data)"""
        return self._clone()

    def using(self, alias):
        """Specify database"""
        new_qs = self._clone()
        new_qs.db = alias
        return new_qs

    def none(self):
        """Return empty result"""
        return ExternalDataQuerySet(self.model, [])

    def exists(self):
        """Check if data exists"""
        return len(self._data) > 0

    def values(self, *fields):
        """Return dictionary list"""
        return self

    def values_list(self, *fields, **kwargs):
        """Return value list"""
        return self

    def only(self, *fields):
        """Limit query fields (not needed for external data)"""
        return self._clone()

    def defer(self, *fields):
        """Defer field loading (not needed for external data)"""
        return self._clone()


class FakeModelAdmin(admin.ModelAdmin):
    """
    Fake Model Admin that inherits from admin.ModelAdmin to simulate ModelAdmin behavior.
    Mainly used to display external data in Django Admin.
    Implementation:
    1. Override get_queryset to return external data instead of database data by default
    2. Override get_search_results to handle search
    3. Override has_add_permission to disable add functionality
    4. Override has_change_permission to disable edit functionality
    5. Override has_delete_permission to disable delete functionality
    6. Override changelist_view to display external data
    """

    _error_message = None  # Store error messages

    def get_queryset(self, request):
        """
        Override get_queryset to return external data instead of database data by default
        """
        # Get search term
        search_term = request.GET.get("q", "").strip()

        # Reset error message
        self._error_message = None

        # Fetch data from external source
        external_data = self.fetch_external_data(search_term)

        # Return virtual QuerySet containing external data
        return ExternalDataQuerySet(MongoDBPassword, external_data)

    def get_search_results(self, request, queryset, search_term):
        """
        Custom search results
        Since we've already handled search in get_queryset, return directly here
        """
        # queryset is already ExternalDataQuerySet containing searched data
        return queryset, False

    def has_add_permission(self, request):
        """Disable add functionality (external data is usually read-only)"""
        return False

    def has_change_permission(self, request, obj=None):
        """Disable edit functionality (external data is usually read-only)"""
        # Can return based on conditions if edit is needed in some cases
        if obj and hasattr(obj, "id") and obj.id < 0:
            return False  # External data cannot be edited
        return False  # Disable all edits

    def has_delete_permission(self, request, obj=None):
        """Disable delete functionality (external data is usually read-only)"""
        if obj and hasattr(obj, "id") and obj.id < 0:
            return False  # External data cannot be deleted
        return False  # Disable all deletions

    def changelist_view(self, request, extra_context=None):
        """
        Optional: Add extra context information and tips to the list page
        """
        from django.contrib import messages

        # Show tips only when there's no search term (avoid showing on every search)
        if not request.GET.get("q"):
            messages.info(request, "💡 Usage: Enter IP:Port:CloudID or IP:Port in the search box to query passwords")
            messages.warning(
                request, "🔐 Security: Password information is for operation viewing only, do not disclose!"
            )

        extra_context = extra_context or {}
        extra_context["title"] = "MongoDB Password Management (External Data Source)"
        # Pass flag to template to display help information
        extra_context["custom_help_text"] = True

        # Pass error message to template
        if self._error_message:
            extra_context["error_message"] = self._error_message

        return super().changelist_view(request, extra_context)


@admin.register(MongoDBPassword)
class MongoDBPwdAdmin(FakeModelAdmin):
    search_fields = ["username"]  # input
    list_display = ["id", "username", "password", "component", "ip", "port", "bk_cloud_id"]
    list_display_links = None  # 禁用所有超链接
    list_per_page = 100  # show 100 items per page
    ordering = ["username"]
    model = MongoDBPassword
    mongodb_users = [
        MongoDBManagerUser.DbaUser.value,
        MongoDBManagerUser.MonitorUser.value,
        MongoDBManagerUser.AppDbaUser.value,
        MongoDBManagerUser.AppMonitorUser.value,
        MongoDBDefaultUser.DefaultUser.value,
        MongoDBManagerUser.WebconsoleUser.value,
    ]

    def fetch_external_data(self, search_term=""):
        external_data = []
        if search_term:
            # Replace full-width colon with half-width colon for better user experience
            search_term = search_term.replace("：", ":")

            if ":" in search_term:
                parts = search_term.split(":")
                if len(parts) == 3:
                    ip, port, bk_cloud_id = parts
                elif len(parts) == 2:
                    ip, port = parts
                    bk_cloud_id = 0
                else:
                    return self.error_data(
                        "please input correct IP:port format, like: 1.1.1.1:10000:803 or 1.1.1.1:10000"
                    )
                try:
                    port = int(port)
                    bk_cloud_id = int(bk_cloud_id)
                except ValueError:
                    return self.error_data(
                        f"Invalid port number: {port}. "
                        "Please input correct IP:port format, like: 1.1.1.1:10000:803 or 1.1.1.1:10000"
                    )
            else:
                return self.error_data("please input correct IP:port format, like: 1.1.1.1:10000")

            try:
                instances = [{"ip": ip, "port": port, "bk_cloud_id": bk_cloud_id}]
                v = mongodb_password.MongoDBPassword().get_users_password_from_db(instances, self.mongodb_users)

                # Check return result
                if v is None:
                    return self.error_data(
                        f"API returned None, password service may be unavailable. "
                        f"Query: ip={ip}, port={port}, bk_cloud_id={bk_cloud_id}"
                    )

                if v.get("info"):
                    # API returned error information
                    return self.error_data(f"Password service error: {v.get('info')}")

                if not v.get("password") or len(v.get("password", [])) == 0:
                    return self.error_data(
                        f"No password data found. Possible reasons: 1) Instance doesn't exist; "
                        f"2) Instance has no password configured; 3) Incorrect cloud area ID. "
                        f"Query parameters: ip={ip}, port={port}, bk_cloud_id={bk_cloud_id}"
                    )

                # Successfully retrieved passwords
                for idx, item in enumerate(v["password"]):
                    obj = MongoDBPassword(
                        username=item.get("username", "-"),
                        password=item.get("password", "-"),
                        component=item.get("component", ""),
                        ip=item.get("ip", ""),
                        port=item.get("port", 0),
                        bk_cloud_id=item.get("bk_cloud_id", bk_cloud_id),
                    )
                    # Set unique negative ID to avoid conflicts with database data
                    obj.id = -(idx + 1)
                    obj.pk = obj.id
                    external_data.append(obj)
                return external_data

            except Exception as e:
                import traceback

                error_detail = traceback.format_exc()
                return self.error_data(
                    f"Failed to retrieve password: {str(e)}\n\n"
                    f"Query parameters: ip={ip}, port={port}, bk_cloud_id={bk_cloud_id}\n"
                    f"Error details: {error_detail[:500]}"  # Limit length
                )

        return external_data

    def error_data(self, message):
        """Store error message and return empty list"""
        self._error_message = message
        return []  # Return empty list, no data displayed

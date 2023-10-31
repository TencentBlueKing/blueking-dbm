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
from django.core.management.base import BaseCommand

from backend.db_meta.models import Cluster
from backend.db_meta.utils import remove_cluster


class Command(BaseCommand):
    help = "remove some clusters."

    def add_arguments(self, parser):
        parser.add_argument("cluster_ids", nargs="+", type=int, help="cluster IDs to remove")
        parser.add_argument("-i", "--job-clean", dest="job_clean", action="store_true", help="do job clean")
        parser.add_argument("-c", "--cc-clean", dest="cc_clean", action="store_true", help="do cc clean")

    def handle(self, *args, **options):
        cluster_ids = options.get("cluster_ids")
        job_clean = options.get("job_clean")
        cc_clean = options.get("cc_clean")

        for cluster in Cluster.objects.filter(id__in=cluster_ids):
            remove_cluster(cluster.id, job_clean, cc_clean)

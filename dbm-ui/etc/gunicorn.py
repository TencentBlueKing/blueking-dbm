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
import os

from gevent import monkey  # noqa

monkey.patch_all()

HOST = os.environ.get('HOST', '127.0.0.1')
PORT = os.environ.get('PORT', 8000)
NUMPROCS = int(os.environ.get('NUMPROCS', 2))

bind = '%s:%s' % (HOST, PORT)
backlog = 2048

workers = NUMPROCS

# worker_class = 'sync'
worker_class = 'gevent'
worker_connections = 1000
timeout = 60
keepalive = 2
# The maximum number of requests a worker will process before restarting
max_requests = 2000

spew = False

daemon = False

# logging
errorlog = '-'
loglevel = 'info'
accesslog = '-'
access_log_format = '%(h)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" "%({X-Request-Id}i)s" in %(L)s seconds'

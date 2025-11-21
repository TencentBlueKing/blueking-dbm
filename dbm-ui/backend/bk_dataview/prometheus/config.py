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

import sys

from backend import env


def monitor_celery_report_config():
    boot_cmd = " ".join(sys.argv)
    print(boot_cmd)
    if "celery" in boot_cmd and "-A config.prod worker" in boot_cmd:
        try:
            q_conf_index = sys.argv.index("-Q")
        except ValueError as e:
            sys.stdout.write(
                "[!]can't found -Q option in command: %s, skip celery monitor report config: %s\n" % (boot_cmd, e)
            )
            return

        try:
            queues = sys.argv[q_conf_index + 1]
        except IndexError as e:
            sys.stdout.write(
                "[!]can't found -Q value in command: %s, skip celery monitor report config: %s\n" % (boot_cmd, e)
            )
            return

        # 只对存在以下队列的情况进行上报
        monitor_queues = ["er_execute", "er_schedule", "default"]
        if not any([monitor_queue in queues for monitor_queue in monitor_queues]):
            sys.stdout.write("[!]can't found er queue in command: %s, skip celery monitor report config\n" % boot_cmd)
            return

        from bk_monitor_report import MonitorReporter  # noqa
        from bk_monitor_report.contrib.celery import MonitorReportStep  # noqa
        from blueapps.core.celery import celery_app  # noqa

        reporter = MonitorReporter(
            data_id=env.BKAPP_MONITOR_REPORTER_DATA_ID,  # 监控 Data ID
            access_token=env.BKAPP_MONITOR_REPORTER_ACCESS_TOKEN,  # 自定义上报 Token
            target=env.BKAPP_MONITOR_REPORTER_TARGET,  # 上报唯一标志符
            url=env.BKAPP_MONITOR_REPORTER_URL,  # 上报地址
            report_interval=env.BKAPP_MONITOR_REPORTER_REPORT_INTERVAL,  # 上报周期，秒
            chunk_size=env.BKAPP_MONITOR_REPORTER_CHUNK_SIZE,  # 上报指标分块大小
        )

        # 针对多进程worker需要做特殊梳理，在worker进程中进行reporter start
        prefork_config_check = [("-P", "-P prefork"), ("--pool", "--pool=prefork")]
        if any([config[0] in boot_cmd and config[1] not in boot_cmd for config in prefork_config_check]):
            MonitorReportStep.setup_reporter(reporter)
            celery_app.steps["worker"].add(MonitorReportStep)
        else:
            from celery.signals import worker_process_init  # noqa

            worker_process_init.connect(reporter.start, weak=False)

        sys.stdout.write("[Monitor reporter] celery init success\n")


def monitor_web_report_config():
    boot_cmd = " ".join(sys.argv)
    print(boot_cmd)
    if "gunicorn" in boot_cmd or "runserver" in boot_cmd:
        from bk_monitor_report import MonitorReporter  # noqa

        reporter = MonitorReporter(
            data_id=env.BKAPP_MONITOR_REPORTER_DATA_ID,  # 监控 Data ID
            access_token=env.BKAPP_MONITOR_REPORTER_ACCESS_TOKEN,  # 自定义上报 Token
            target=env.BKAPP_MONITOR_REPORTER_TARGET,  # 上报唯一标志符
            url=env.BKAPP_MONITOR_REPORTER_URL,  # 上报地址
            report_interval=env.BKAPP_MONITOR_REPORTER_REPORT_INTERVAL,  # 上报周期，秒
            chunk_size=env.BKAPP_MONITOR_REPORTER_CHUNK_SIZE,  # 上报指标分块大小
        )
        reporter.start()
        sys.stdout.write("[Monitor reporter] web init success\n")

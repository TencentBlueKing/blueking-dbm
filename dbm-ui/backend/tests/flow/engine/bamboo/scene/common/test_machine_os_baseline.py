# -*- coding: utf-8 -*-
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from backend.flow.plugins.components.collections.common.machine_os_baseline import (
    MachineOsBaselineComponent,
    build_machine_os_baseline_acts,
    render_machine_os_baseline_script,
)


class TestMachineOsBaselineScript(SimpleTestCase):
    def test_script_order_with_hosts(self):
        script = render_machine_os_baseline_script(
            [{"ip": "127.0.0.1", "domain": "ntp.example.com"}], init_ntpdate=True
        )
        hosts_at = script.index('HOSTS_ENTRY="127.0.0.1 ntp.example.com"')
        tos_at = script.index("tos -f dns")
        tos4_at = script.index("TencentOS Server 4")
        chronyd_at = script.index("systemctl enable --now chronyd")
        cron_at = script.index("ntpdate.sh --maxoffset 3")
        force_at = script.index("ntpdate.sh -f")
        self.assertLess(hosts_at, tos_at)
        self.assertLess(tos_at, tos4_at)
        self.assertLess(tos4_at, chronyd_at)
        self.assertLess(chronyd_at, cron_at)
        self.assertLess(cron_at, force_at)
        self.assertIn("RANDOM % 60", script)
        self.assertIn("/etc/tlinux-release", script)

    def test_script_skips_hosts_when_entries_empty(self):
        script = render_machine_os_baseline_script([], init_ntpdate=True)
        self.assertIn("hosts entries empty, skip /etc/hosts", script)
        self.assertNotIn("HOSTS_ENTRY=", script)
        self.assertIn("tos -f dns", script)
        self.assertIn("ntpdate.sh -f", script)
        self.assertIn("systemctl enable --now chronyd", script)

    def test_script_skips_ntpdate_when_disabled(self):
        script = render_machine_os_baseline_script(
            [{"ip": "127.0.0.1", "domain": "a.example.com"}], init_ntpdate=False
        )
        self.assertIn('HOSTS_ENTRY="127.0.0.1 a.example.com"', script)
        self.assertNotIn("ntpdate.sh", script)
        self.assertNotIn("tos -f dns", script)
        self.assertNotIn("chronyd", script)
        self.assertIn("INIT_OS_NTPDATE disabled, skip ntpdate", script)


class TestMachineOsBaselineActs(SimpleTestCase):
    def test_split_by_cloud(self):
        acts = build_machine_os_baseline_acts(
            [
                {"ip": "127.0.0.1", "bk_cloud_id": 0},
                {"ip": "127.0.0.2", "bk_cloud_id": 1},
                {"ip": "127.0.0.3", "bk_cloud_id": 0},
            ],
            [{"ip": "127.0.0.10", "domain": "a.example.com"}],
        )
        self.assertEqual(len(acts), 2)
        self.assertTrue(all(act["act_component_code"] == MachineOsBaselineComponent.code for act in acts))
        self.assertTrue(all(act["act_name"] == "主机OS初始化" for act in acts))
        by_cloud = {act["kwargs"]["exec_targets"][0]["bk_cloud_id"]: act["kwargs"]["exec_targets"] for act in acts}
        self.assertEqual(len(by_cloud[0]), 2)
        self.assertEqual(len(by_cloud[1]), 1)

    def test_empty_hosts_still_builds_one_act(self):
        acts = build_machine_os_baseline_acts([], [])
        self.assertEqual(len(acts), 1)
        self.assertEqual(acts[0]["act_name"], "主机OS初始化")
        self.assertEqual(acts[0]["kwargs"]["exec_targets"], [])
        self.assertTrue(acts[0]["kwargs"]["print_ip_log_on_success"])
        self.assertEqual(acts[0]["act_component_code"], "machine_os_baseline")


class TestImportPipelineBaseline(SimpleTestCase):
    def _flow(self, hosts, os_type="Linux"):
        from backend.flow.engine.bamboo.scene.common.machine_os_init import ImportResourceInitStepFlow

        return ImportResourceInitStepFlow(
            root_id="root-os-baseline",
            data={
                "hosts": hosts,
                "bk_biz_id": 1,
                "operator": "tester",
                "os_type": os_type,
            },
        )

    @patch("backend.flow.engine.bamboo.scene.common.machine_os_init.init_ntpdate_enabled", return_value=True)
    @patch("backend.flow.engine.bamboo.scene.common.machine_os_init.get_or_create_resource_module", return_value=1)
    @patch("backend.flow.engine.bamboo.scene.common.machine_os_init.get_resource_biz", return_value=2)
    @patch(
        "backend.flow.engine.bamboo.scene.common.machine_os_init.build_install_host_common_components",
        return_value={"sub": True},
    )
    @patch("backend.flow.engine.bamboo.scene.common.machine_os_init.SystemSettings.get_setting_value", return_value={})
    def test_linux_mounts_baseline_instead_of_hosts_act(self, *_mocks):
        flow = self._flow(
            [
                {"ip": "127.0.0.1", "host_id": 11, "bk_cloud_id": 0},
                {"ip": "127.0.0.2", "host_id": 12, "bk_cloud_id": 3},
            ]
        )
        pipeline = MagicMock()
        flow._ImportResourceInitStepFlow__build_machine_import_pipeline(pipeline, flow.data)

        pipeline.add_parallel_acts.assert_called()
        acts = pipeline.add_parallel_acts.call_args.kwargs["acts_list"]
        codes = [act["act_component_code"] for act in acts]
        self.assertEqual(codes, ["machine_os_baseline", "machine_os_baseline"])
        add_act_codes = [call.kwargs.get("act_component_code") for call in pipeline.add_act.call_args_list]
        self.assertNotIn("add_hosts_entry", add_act_codes)

    @patch("backend.flow.engine.bamboo.scene.common.machine_os_init.get_or_create_resource_module", return_value=1)
    @patch("backend.flow.engine.bamboo.scene.common.machine_os_init.get_resource_biz", return_value=2)
    @patch(
        "backend.flow.engine.bamboo.scene.common.machine_os_init.build_install_host_common_components",
        return_value={"sub": True},
    )
    @patch("backend.flow.engine.bamboo.scene.common.machine_os_init.SystemSettings.get_setting_value", return_value={})
    def test_windows_skips_baseline(self, *_mocks):
        flow = self._flow([{"ip": "127.0.0.8", "host_id": 18, "bk_cloud_id": 0}], os_type="Windows")
        pipeline = MagicMock()
        flow._ImportResourceInitStepFlow__build_machine_import_pipeline(pipeline, flow.data)

        codes = [call.kwargs.get("act_component_code") for call in pipeline.add_act.call_args_list]
        self.assertNotIn("machine_os_baseline", codes)
        pipeline.add_parallel_acts.assert_not_called()

    @patch("backend.flow.engine.bamboo.scene.common.machine_os_init.init_ntpdate_enabled", return_value=False)
    @patch("backend.flow.engine.bamboo.scene.common.machine_os_init.get_or_create_resource_module", return_value=1)
    @patch("backend.flow.engine.bamboo.scene.common.machine_os_init.get_resource_biz", return_value=2)
    @patch(
        "backend.flow.engine.bamboo.scene.common.machine_os_init.build_install_host_common_components",
        return_value={"sub": True},
    )
    @patch("backend.flow.engine.bamboo.scene.common.machine_os_init.SystemSettings.get_setting_value", return_value={})
    def test_linux_skips_baseline_when_ntpdate_off_and_hosts_empty(self, *_mocks):
        flow = self._flow([{"ip": "127.0.0.1", "host_id": 11, "bk_cloud_id": 0}])
        pipeline = MagicMock()
        flow._ImportResourceInitStepFlow__build_machine_import_pipeline(pipeline, flow.data)

        codes = [call.kwargs.get("act_component_code") for call in pipeline.add_act.call_args_list]
        self.assertNotIn("machine_os_baseline", codes)
        if pipeline.add_parallel_acts.called:
            for call in pipeline.add_parallel_acts.call_args_list:
                parallel_codes = [act["act_component_code"] for act in call.kwargs["acts_list"]]
                self.assertNotIn("machine_os_baseline", parallel_codes)

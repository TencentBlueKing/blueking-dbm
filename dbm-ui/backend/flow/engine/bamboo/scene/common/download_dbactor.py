import logging
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs

logger = logging.getLogger("flow")


class DownloadDbactorFlow(object):
    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def download_dbactor_flow(self):
        """
        下载指定数据库类型的dbactor到机器上
        """
        pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
        sub_pipeline.add_act(
            act_name=_("下发actuator介质"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=self.data["bk_cloud_id"],
                    exec_ip=self.data["ips"],
                    file_list=GetFileList(db_type=self.data["db_type"]).get_db_actuator_package(),
                )
            ),
        )
        pipeline.add_sub_pipeline(sub_pipeline.build_sub_process(sub_name=_("下发actuator介质")))
        pipeline.run_pipeline()

# -*- coding: utf-8 -*-
# 导入模块
from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.flow.consts import ConfigFileEnum, ConfigTypeEnum, MongoDBManagerUser, NameSpaceEnum
from backend.flow.utils.mongodb import mongodb_password


# MongoUtil: MongoDB工具类 用于获取MongoDB的配置信息 以及用户密码等
class MongoUtil:
    @staticmethod
    def _get_define_config(bk_biz_id, namespace, conf_file, conf_type: str):
        """获取一些全局的参数配置"""
        """ bk_biz_id 为"0"时，表示平台级别配置"""
        data = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": bk_biz_id,
                "level_name": LevelName.PLAT if bk_biz_id == "0" else LevelName.APP,
                "level_value": bk_biz_id,
                "conf_file": conf_file,
                "conf_type": conf_type,
                "namespace": namespace,
                "format": FormatType.MAP.value,
            }
        )
        return data["content"]

    def get_mongodb_os_conf(self, bk_biz_id: str = "0"):
        """
        获取os配置信息
        """

        return self._get_define_config(
            bk_biz_id=bk_biz_id,
            namespace=NameSpaceEnum.MongoDBCommon.value,
            conf_type=ConfigTypeEnum.Config.value,
            conf_file=ConfigFileEnum.OsConf.value,
        )

    @staticmethod
    def get_dba_user_password(ip: str, port, bk_cloud_id: int):
        """
        获取dba user and password
        """
        dba_user = MongoDBManagerUser.DbaUser.value
        out = mongodb_password.MongoDBPassword().get_password_from_db(ip, int(port), bk_cloud_id, dba_user)
        if not out or "password" not in out:
            raise Exception("can not get dba_user password for {}:{}:{}".format(ip, port, bk_cloud_id))

        return dba_user, out["password"]

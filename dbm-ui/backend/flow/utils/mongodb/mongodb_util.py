# -*- coding: utf-8 -*-
# 导入模块
import logging

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.flow.consts import ConfigFileEnum, ConfigTypeEnum, MongoDBManagerUser, NameSpaceEnum
from backend.flow.utils.mongodb import mongodb_password
from backend.flow.utils.mongodb.mongodb_module_operate import MongoDBCCTopoOperator

logger = logging.getLogger("flow")


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

    @staticmethod
    def get_mongo_user_password(ip: str, port, bk_cloud_id: int, username: str):
        """
        获取mongo user and password
        """
        out = mongodb_password.MongoDBPassword().get_password_from_db(ip, int(port), bk_cloud_id, username)
        if not out or "password" not in out:
            raise Exception("can not get mongo_user password for {}:{}:{}".format(ip, port, bk_cloud_id))

        return username, out["password"]

    @staticmethod
    def update_instance_labels(*cluster_id_list: int):
        """
        更新服务实例标签和转模块，可以重复执行
        """
        for cluster_id in cluster_id_list:
            cluster = Cluster.objects.filter(id=cluster_id).first()
            if not cluster:
                raise Exception("cluster_id:{} not found".format(cluster_id))

            if (
                cluster.cluster_type != ClusterType.MongoReplicaSet.value
                and cluster.cluster_type != ClusterType.MongoShardedCluster.value
            ):
                raise Exception(
                    "cluster_id:{} cluster_type:{}is not a mongodb cluster".format(cluster_id, cluster.cluster_type)
                )

            storage_objs = cluster.storageinstance_set.all()
            MongoDBCCTopoOperator(cluster).transfer_instances_to_cluster_module(storage_objs, is_increment=True)

            # proxy 没有分片，这里也操作一下，有时候需要更新其它标签
            proxy_objs = cluster.proxyinstance_set.all()
            MongoDBCCTopoOperator(cluster).transfer_instances_to_cluster_module(proxy_objs, is_increment=True)

            logger.info("cluster_id:{} update instance labels success".format(cluster_id))

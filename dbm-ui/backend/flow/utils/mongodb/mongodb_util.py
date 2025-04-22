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
from backend.flow.utils.mongodb.mongodb_repo import MongoRepository

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

    @staticmethod
    def get_mongodb_webconsole_args(cluster_id: int, session: str, command: str, timeout: int = 15):
        """
        获取mongodb webconsole参数
        @param cluster_id: 集群id
        @param session: session，用于标识一个请求，请务必保证带有用户id信息.
        @param command: 命令，如：show dbs, 首次连接可以为空
        @param timeout: 超时时间，单位秒
        """
        cluster = MongoRepository().fetch_one_cluster(withDomain=False, id=cluster_id)
        if not cluster:
            raise Exception("cluster_id:{} not found".format(cluster_id))

        # 获得连接的节点, 集群为mongos节点，副本集优先使用backup节点，没有backup节点则为m1节点
        connect_nodes = []
        if cluster.is_sharded_cluster():
            connect_nodes = cluster.get_mongos()[:2]  # 取两个mongos就行
        else:
            shard = cluster.get_shards()[0]
            node = shard.get_backup_node()
            if node:
                connect_nodes.append(node)
            else:
                connect_nodes.append(shard.get_not_backup_nodes()[0])

        if len(connect_nodes) == 0:
            raise Exception("cluster_id:{} can not get connect node".format(cluster_id))

        # ip port
        node = connect_nodes[0]
        adminUserName = MongoDBManagerUser.DbaUser.value
        password_out = mongodb_password.MongoDBPassword().get_password_from_db(
            node.ip, node.port, node.bk_cloud_id, adminUserName
        )

        if not password_out or "password" not in password_out:
            raise Exception(
                "can not get webconsole_user password for {}({}:{})".format(cluster_id, node.ip, node.port)
            )
        else:
            adminPassword = password_out["password"]

        user, pwd, is_created = MongoUtil.cluster_pwd_get_or_create(
            cluster_id=cluster_id, bk_cloud_id=node.bk_cloud_id, username=MongoDBManagerUser.WebconsoleUser.value
        )

        logger.info(
            "cluster_id:{} webconsole user: {}, password: {}, is_created: {}".format(cluster_id, user, pwd, is_created)
        )

        return {
            "cluster_id": cluster.cluster_id,
            "cluster_type": cluster.cluster_type,
            "cluster_domain": cluster.immute_domain,
            "version": cluster.major_version.split("-")[-1],
            "addresses": [m.addr() for m in connect_nodes],  # 取两个mongos就行
            "set_name": cluster.name,
            "command": command,
            "timeout": timeout,
            "admin_username": adminUserName,
            "admin_password": adminPassword,
            "username": user,
            "password": pwd,
            "session": "{}:{}".format(cluster_id, session),
        }

    @staticmethod
    def cluster_pwd_get_or_create(cluster_id: int, bk_cloud_id: int, username: str) -> (str, str, bool):
        """
        从密码库中获取或生成mongodb用户密码
        按mongo:+cluster_id为主键获取密码, 密码规则为mongodb_password
        返回 值为 (username, password, is_created)
        """
        is_created = False
        cluster = "mongodb_cluster:{}".format(cluster_id)
        out = mongodb_password.MongoDBPassword().get_password_from_db(cluster, int(0), bk_cloud_id, username)
        # 接口返回异常
        if not out or "password" not in out:
            raise Exception("can not get dba_user password for {}:{}".format(cluster_id, bk_cloud_id))

        # 如果密码为空，需要创建密码
        if out["password"] is None or out["password"] == "":
            new_pwd = mongodb_password.MongoDBPassword().create_user_password()
            if new_pwd["password"] is None:
                raise Exception("create password fail, error:{}".format(new_pwd["info"]))
            # 密码长度小于8位，表示创建失败. 我们的密码规则不会允许小于8位的密码
            if len(new_pwd["password"]) < 8:
                raise Exception("create password fail, password length is {}".format(len(new_pwd["password"])))
            err_msg = mongodb_password.MongoDBPassword().save_password_to_db2(
                instances=[
                    {
                        "ip": cluster,
                        "port": 0,
                        "bk_cloud_id": bk_cloud_id,
                    }
                ],
                username=username,
                password=new_pwd["password"],
                operator="admin",
            )

            if err_msg != "":
                raise Exception("save password to db fail, error:{}".format(err_msg))
            out["password"] = new_pwd["password"]
            is_created = True

        return username, out["password"], is_created

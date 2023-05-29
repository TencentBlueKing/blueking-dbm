from dataclasses import dataclass


@dataclass()
class InstanceTuple:
    """
    定义有主从关系的实例信息对
    """

    master_ip: str
    slave_ip: str
    mysql_port: int


@dataclass()
class ShardInfo:
    """
    对应每个分片集所关联的实例信息对
    """

    shard_key: int
    instance_tuple: InstanceTuple

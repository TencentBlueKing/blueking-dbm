# TenDBClusterRemoteUpgradeValidator 使用说明

## 概述

`TenDBClusterRemoteUpgradeValidator` 是用于 TenDBCluster 后端存储节点升级的校验器，继承自 `MysqlBaseValidator`，提供了全面的升级前校验功能。

## 校验内容

### 1. 公共校验

#### 1.1 集群状态正常校验 (`pre_check_cluster_status`)
- **目的**: 确保待升级的集群状态为 `NORMAL`
- **校验逻辑**: 
  - 遍历所有待升级的集群信息
  - 检查集群状态是否为 `ClusterStatus.NORMAL`
  - 如果发现异常状态，记录错误信息
- **异常处理**: 集群不存在或状态异常时记录错误

#### 1.2 包的存在性校验 (`pre_check_package_existence`)
- **目的**: 确保升级包存在且启用
- **校验逻辑**:
  - 遍历所有待升级的集群信息
  - 检查 `pkg_id` 对应的包是否存在且启用
  - 如果发现包不存在或未启用，记录错误信息
- **异常处理**: 包不存在或未启用时记录错误

#### 1.3 存储所有节点版本主版本一致性校验 (`pre_check_storage_version_consistency`)
- **目的**: 确保集群内所有存储节点的主版本号一致
- **校验逻辑**:
  - 遍历所有待升级的集群信息
  - 获取每个集群的所有存储实例（BACKEND_MASTER 和 BACKEND_SLAVE）
  - 解析每个存储实例的版本号，提取主版本号
  - 检查所有存储实例的主版本号是否一致
- **异常处理**: 版本解析失败或主版本不一致时记录错误

### 2. 本地升级特殊校验

#### 2.1 本地升级版本一致性校验 (`pre_check_local_upgrade_version_consistency`)
- **目的**: 本地升级时确保存储版本主版本与包主版本一致
- **触发条件**: 当 `upgrade_local=True` 时执行
- **校验逻辑**:
  - 检查是否为本地升级模式
  - 如果是本地升级，检查存储所有节点版本主版本和包的主版本必须一致
  - 如果发现版本不一致，记录错误信息
- **异常处理**: 存储版本与包版本主版本不一致时记录错误

#### 2.2 分片主从同机校验 (`pre_check_shard_master_slave_same_machine`)
- **目的**: 本地升级时确保主机维度切换时master和slave机器上的分片一致
- **触发条件**: 当 `upgrade_local=True` 时执行
- **校验逻辑**:
  - 检查是否为本地升级模式
  - 如果是本地升级，通过 `cluster.tendbclusterstorageset_set` 获取分片信息
  - 通过 `storage_instance_tuple` 获取主从关系
  - 按master机器IP分组，检查对应的slave机器上的分片是否一致
  - 如果发现master机器和slave机器上的分片不一致，记录错误信息
- **异常处理**: master机器和slave机器上的分片不一致时记录错误

### 3. 迁移升级校验

- **状态**: 待定
- **说明**: 迁移升级的特殊校验逻辑尚未实现，可根据后续需求进行扩展

## 数据格式支持

### 输入数据格式
```python
{
    "upgrade_local": True,  # 是否本地升级
    "infos": [
        {
            "cluster_id": 1,    # 集群ID
            "pkg_id": 123,      # 目标版本包ID
            # 其他升级相关参数...
        }
    ]
}
```

### 校验方法调用顺序
1. `pre_check_cluster_status()` - 集群状态校验
2. `pre_check_package_existence()` - 包存在性校验
3. `pre_check_storage_version_consistency()` - 存储版本一致性校验
4. `pre_check_local_upgrade_version_consistency()` - 本地升级版本一致性校验（条件执行）
5. `pre_check_shard_master_slave_same_machine()` - 分片主从同机校验（条件执行）

## 异常处理

### 异常类型
- `StorageVersionFailedException`: 存储版本相关校验失败
- `UpgradeVersionFailedException`: 升级包相关校验失败

### 异常触发条件
- **StorageVersionFailedException**: 当存储版本一致性校验失败时抛出
- **UpgradeVersionFailedException**: 当包存在性校验失败时抛出

## 使用示例

### 在 Controller 中使用
```python
from backend.flow.engine.bamboo.scene.spider.validate.remote_upgrade_validate import TenDBClusterRemoteUpgradeValidator

class SpiderController(BaseController):
    @validates_with(TenDBClusterRemoteUpgradeValidator)
    def tendbcluster_remote_upgrade(self):
        """
        tendbcluster backend 节点升级
        """
        flow = UpgradeRemoteFlow(root_id=self.root_id, data=self.ticket_data)
        flow.run()
```

### 直接使用校验器
```python
# 创建校验器实例
validator = TenDBClusterRemoteUpgradeValidator(data=ticket_data)

# 执行校验
try:
    validator()
    print("校验通过")
except (StorageVersionFailedException, UpgradeVersionFailedException) as e:
    print(f"校验失败: {e}")
```

## 扩展说明

### 添加新的校验逻辑
1. 在 `TenDBClusterRemoteUpgradeValidator` 类中添加新的校验方法
2. 在 `__call__` 方法中调用新的校验方法
3. 根据校验结果决定是否抛出异常

### 自定义异常处理
- 可以继承现有的异常类或创建新的异常类
- 在 `__call__` 方法中根据错误类型选择合适的异常

## 注意事项

1. **版本解析**: 使用 `major_version_parse` 函数解析版本号，确保版本格式正确
2. **国际化**: 所有错误信息都使用 `_()` 进行国际化处理
3. **异常安全**: 所有数据库操作都包含异常处理，避免因单个集群问题影响整体校验
4. **性能考虑**: 校验过程中会进行多次数据库查询，建议在数据量较大时考虑优化

## 总结

现在 `tendbcluster_remote_upgrade` 方法会自动执行以下校验：

### 公共校验（所有升级模式）
1. **集群状态校验**: 确保集群状态为 `NORMAL`
2. **包存在性校验**: 确保升级包存在且启用
3. **存储版本一致性校验**: 确保集群内所有存储节点的主版本号一致

### 本地升级特殊校验（仅当 `upgrade_local=True` 时）
4. **版本兼容性校验**: 确保存储版本主版本与包主版本一致
5. **分片主从同机校验**: 确保主机维度切换时master和slave机器上的分片一致

### 迁移升级校验
6. **待定**: 根据后续需求进行扩展

所有校验通过后才会执行实际的升级流程，确保升级操作的安全性和可靠性。分片主从同机校验特别重要，因为本地升级时如果master和slave机器上的分片不一致，会导致主机维度切换失败。

### 校验示例

假设有以下分片配置：
- 分片1: master在ip1，slave在ip2
- 分片2: master在ip1，slave在ip2
- 分片3: master在ip1，slave在ip3

在这种情况下，master机器ip1上有分片1、2、3，但slave机器ip2上只有分片1、2，slave机器ip3上只有分片3。这会导致校验失败，因为本地升级要求主机维度切换时master和slave机器上的分片必须一致。

### 正确的配置示例

正确的配置应该是：
- 分片1: master在ip1，slave在ip2
- 分片2: master在ip1，slave在ip2
- 分片3: master在ip3，slave在ip4

这样每个master机器和对应的slave机器上的分片都是一致的，可以进行主机维度的切换。

# Spider升级模块重构说明

## 重构概述

本次重构将原有的三个文件进行了重新组织，将公共函数和工具函数拆分到独立的模块中，提高了代码的可维护性和复用性。

## 文件结构

### 原有文件
- `upgrade_spider_node.py` - Spider节点升级主流程
- `local_upgrade.py` - 本地升级流程
- `migrate_upgrade.py` - 迁移升级流程

### 新增文件
- `upgrade_utils.py` - 升级相关的公共工具函数
- `upgrade_components.py` - 升级相关的组件和子流程

## 重构内容

### 1. upgrade_utils.py
包含以下公共工具函数：

#### 版本和兼容性检查
- `filter_spiders_by_version()` - 过滤需要升级的spider实例
- `check_version_compatibility()` - 检查版本兼容性
- `check_spider_upgrade_version_compatibility()` - 检查spider升级版本兼容性
- `check_spider_node_count_compatibility()` - 检查spider节点数量兼容性
- `check_cross_major_version_upgrade()` - 检查是否跨主版本升级

#### 实例管理
- `get_remote_storage_instances()` - 获取remote存储实例
- `group_master_slave_pairs()` - 将实例按主从配对分组
- `convert_pairs_to_upgrade_instances()` - 转换主从配对格式
- `check_master_slave_pair()` - 检查单个主从对健康状态
- `check_master_slave_relationship()` - 检查主从关系配置

#### 实例信息获取
- `get_spider_upgrade_instances()` - 获取spider升级实例信息
- `get_spider_master_instances()` - 获取spider master实例列表

#### 告警和监控管理
- `add_alarm_shield_act()` - 添加告警屏蔽活动
- `add_disable_alarm_shield_act()` - 添加解除告警屏蔽活动
- `add_monitor_shield_act()` - 添加监控屏蔽活动
- `add_monitor_unshield_act()` - 添加解除监控屏蔽活动

#### 介质管理
- `add_mysql_media_download_for_all_hosts()` - 按主机维度统一下发MySQL升级介质

### 2. upgrade_components.py
包含以下组件和子流程：

#### MySQL升级相关
- `build_mysql_upgrade_pipelines()` - 构建MySQL升级子流程列表
- `build_upgrade_mysql_subflow()` - 构建MySQL升级子流程
- `build_master_slave_switch_subflow()` - 构建主从切换子流程

#### Spider升级相关
- `build_spider_upgrade_subflow()` - 构建spider升级子流程
- `add_spider_alarm_shield_act()` - 添加spider告警屏蔽活动
- `add_spider_disable_alarm_shield_act()` - 添加解除spider告警屏蔽活动
- `add_spider_upgrade_check_act()` - 添加spider升级检查活动
- `add_spider_media_download_act()` - 添加spider介质下发活动
- `add_spider_keyword_check_act()` - 添加spider关键字检查活动

#### 通用组件
- `add_standardize_act()` - 添加标准化活动
- `add_cluster_module_update_act()` - 添加集群模块更新活动

### 3. 重构后的主文件

#### local_upgrade.py
- 保留了 `TenDBClusterStorageLocalUpgradeFlow` 类
- 移除了所有私有工具方法，改为调用 `upgrade_utils.py` 和 `upgrade_components.py` 中的函数
- 简化了代码结构，提高了可读性

#### upgrade_spider_node.py
- 保留了 `UpgradeSpiderFlow` 类
- 移除了重复的工具方法
- 使用新的工具函数进行版本检查和实例管理

#### migrate_upgrade.py
- 保持了原有的迁移升级逻辑
- 添加了对 `local_upgrade.py` 的导入，以便复用本地升级流程

## 重构优势

### 1. 代码复用性
- 公共函数被提取到独立模块，可以在多个地方复用
- 减少了代码重复，提高了维护效率

### 2. 模块化设计
- 按功能将代码分组到不同的模块中
- 每个模块职责单一，便于理解和维护

### 3. 可测试性
- 工具函数独立，便于单元测试
- 降低了函数间的耦合度

### 4. 可维护性
- 代码结构更清晰
- 修改某个功能时影响范围更小

## 使用说明

### 导入方式
```python
# 导入工具函数
from .upgrade_utils import (
    check_version_compatibility,
    get_remote_storage_instances,
    # ... 其他函数
)

# 导入组件函数
from .upgrade_components import (
    build_mysql_upgrade_pipelines,
    add_alarm_shield_act,
    # ... 其他函数
)
```

### 函数调用
重构后的函数调用方式保持不变，只是将原来的私有方法调用改为公共函数调用：

```python
# 重构前
self._check_version_compatibility()

# 重构后
check_version_compatibility(self.cluster_id, self.new_mysql_pkg, self.ticket_data)
```

## 注意事项

1. 所有函数都保持了原有的功能逻辑，没有改变业务行为
2. 国际化支持保持不变，所有中文字符串都使用了 `_()` 包装
3. 日志记录格式保持一致
4. 错误处理机制保持不变

## 后续优化建议

1. 可以考虑将更多的配置参数提取到配置文件中
2. 可以添加更多的单元测试来验证重构后的功能
3. 可以考虑使用类型注解来提高代码的可读性
4. 可以进一步优化函数参数，减少参数传递的复杂度

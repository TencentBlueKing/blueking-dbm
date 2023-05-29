# 用途
用于区分不同的数据库集群类型, 如 _TenDBHA, TenDBCluster, TenDBSingle, Redisxxx, Mongoxxx_ 等等

# 结构
```python
class MetaClusterType(models.Model):
    name = models.CharField(max_length=64, primary_key=True)
```

# 静态数据
* 没有强制性的命名规则, 简短清晰就好
* 增加新的集群类型需要人工录入
* 单节点 _MySQL_ 也当作集群处理 (如以前的 _logdb_ )

## 示例

| name         |
|--------------|
| tendbcluster |
| tendbha      |
| tendbsingle  |
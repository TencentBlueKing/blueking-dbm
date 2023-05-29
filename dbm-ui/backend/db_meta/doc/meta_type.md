# 用途
* 一个数据库集群由若干个节点构成, 如 _TenDBCluster_ 需要 _spider_ 和 _remote_
* 不同类型的集群需要的节点, 或者对节点的命名各不相同. 如 _TenDBHA_ 的 `接入层` 叫做 _proxy_, 而 _TenDBCluster_ 的 `接入层` 叫做 _spider_
* 一台机器不允许既是 `接入层` 又是 `存储层`

`MetaType` 关联了 `MetaLayer, MetaClusterType` 来实现上述需求

# 结构
```python
class MetaType(models.Model):
    name = models.CharField(max_length=64, primary_key=True)
    meta_cluster_type = models.ForeignKey(
        MetaClusterType,
        to_field='name',
        db_column='meta_cluster_type',
        on_delete=models.PROTECT
    )
    meta_layer = models.ForeignKey(
        MetaLayer,
        to_field='name',
        db_column='meta_layer',
        on_delete=models.PROTECT
    )
```

# 静态数据
每增加一个新的数据库集群, 还需要在这里增加集群需要的所有节点类型

## 示例

| meta_cluster_type | name         | meta_layer |
|-------------------|--------------|------------|
| tendbcluster      | remote       | storage    |
| tendbcluster      | spider       | proxy      |
| tendbha           | tendbbackend | storage    |
| tendbha           | tendbproxy   | proxy      |
| tendbsingle       | tendbsingle  | storage    |
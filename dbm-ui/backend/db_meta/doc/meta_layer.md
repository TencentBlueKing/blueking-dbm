# 用途
从用户访问数据的视角来看, 常见的数据库集群由`接入层`和`存储层`构成(单节点 _MySQL_ 没有接入层)

`MetaLayer` 用于明确的标识机器在集群中的上述层级
* 接入层: `proxy`
* 存储层: `storage`

# 结构

```python
class MetaLayer(models.Model):
    name = models.CharField(max_length=64, primary_key=True)
```

# 静态数据

很长一段时间内 `MetaLayer` 都只会有这样两行数据, 除非哪一天需要管理 _3_ 层结构的数据库集群

## 示例

| name    |
|---------|
| proxy   |
| storage |




# 📚 项目单元测试开发规范总结

## 一、测试框架与工具

### 1️⃣ 使用 pytest 框架
```python
import pytest

# 标记测试需要数据库访问
pytestmark = pytest.mark.django_db
```

### 2️⃣ 测试文件组织
```
backend/tests/
├── conftest.py              # 全局 fixtures
├── mock_data/               # 全局 mock 数据
│   ├── components/
│   └── iam_app/
└── db_services/
    └── dbbase/
        └── resources/
            ├── conftest.py   # 模块级 fixtures
            └── test_query.py # 测试文件
```

## 二、命名规范

- ✅ 测试文件命名：`test_*.py`，示例 `test_query.py`
- ✅ 测试类命名：`Test*`，示例 `TestCommonQueryResourceMixin`
- ✅ 测试方法命名：`test_*`，示例 `test_update_headers_default`
- ✅ 使用描述性名称说明测试场景

```python
def test_common_query_cluster_success(self):  # 成功场景
    ...

def test_common_query_cluster_with_tags(self):  # 特定场景
    ...

def test_common_query_instance_empty(self):  # 边界条件
    ...
```

## 三、数据库操作规范

### 1️⃣ 数据库访问标记
```python
# 方式 1：类级别标记
pytestmark = pytest.mark.django_db

# 方式 2：方法级别标记
@pytest.mark.django_db
def test_example():
    ...
```

### 2️⃣ 使用 Fixtures 管理测试数据
```python
@pytest.fixture
def test_cluster_with_entries(test_bk_biz_id, test_cluster_module, test_city):
    """创建包含完整入口的测试集群"""
    # 1. 创建数据
    cluster = Cluster.objects.create(...)

    yield cluster  # 提供给测试使用

    # 2. 清理数据 - 按外键关系逆序删除
    ProxyInstance.objects.filter(cluster=cluster).delete()
    StorageInstance.objects.filter(cluster=cluster).delete()
    ClusterEntry.objects.filter(cluster=cluster).delete()
    cluster.delete()
```

### 3️⃣ 数据清理关键原则
⚠️ 必须按照外键关系的逆序删除！

```python
# ❌ 错误示例 - 会导致 ProtectedError
ClusterEntry.objects.filter(cluster=cluster).delete()  # 先删父对象
CLBEntryDetail.objects.filter(entry__cluster=cluster).delete()  # 后删子对象

# ✅ 正确示例
# 1. 删除有 forward_to 的 ClusterEntry
ClusterEntry.objects.filter(cluster=cluster, forward_to__isnull=False).delete()
# 2. 删除其他 ClusterEntry（会级联删除 CLBEntryDetail 和 PolarisEntryDetail）
ClusterEntry.objects.filter(cluster=cluster).delete()
# 3. 删除实例
ProxyInstance.objects.filter(cluster=cluster).delete()
StorageInstance.objects.filter(cluster=cluster).delete()
# 4. 删除集群
cluster.delete()
# 5. 删除机器
Machine.objects.filter(...).delete()
```

## 四、Mock 使用规范

🎯 最小化原则——只 Mock 必要的外部依赖。

```python
# ✅ 应该 Mock 的：外部服务
@patch("backend.components.CCApi", CCApiMock())
@patch("backend.db_services.ipchooser.query.resource.ResourceQueryHelper.search_cc_cloud")
@patch("backend.flow.utils.dns_manage.DnsManage.get_domain")
def test_example(self, mock_dns, mock_cc_cloud):
    mock_cc_cloud.return_value = {"0": {"bk_cloud_name": "Default Area"}}
    mock_dns.return_value = [{"target": "1.1.1.1", "port": 10000}]
    ...

# ❌ 不应该 Mock 的：数据库查询
# 应该真实创建数据，而不是 Mock ORM 查询
```

## 五、测试数据约定

### 📊 全局测试数据 ID 范围（定义于 `backend/tests/conftest.py`）
```
CLUSTER_ID   = 1-100          # 集群 ID
HOST_ID      = 1-100          # 主机 ID（自定义建议 1000-9999）
BK_HOST_ID   = 10000+         # CC 主机 ID
CITY_ID      = 1-10           # 城市 ID
DB_MODULE_ID = 111            # 模块 ID
DBA_BIZ_ID   = 2005000002     # DBA 业务 ID
SPEC_ID      = 1-100          # 规格 ID
```

### 🎲 自定义测试数据
```python
from django.utils.crypto import get_random_string


def get_random_ip():
    """生成随机 IP"""
    return (
        f"{random.randint(1, 255)}.{random.randint(1, 255)}."
        f"{random.randint(1, 255)}.{random.randint(1, 255)}"
    )


# 使用随机名称避免冲突
cluster_name = get_random_string(6)
```

## 六、Fixture 作用域
```python
# 1. session 级别 - 整个测试会话共享
@pytest.fixture(scope="session", autouse=True)
def __init_city():
    """初始化城市数据"""
    ...

# 2. module 级别 - 模块内共享
@pytest.fixture(scope="module")
def test_city():
    ...

# 3. function 级别（默认）- 每个测试函数独立
@pytest.fixture
def test_cluster_with_entries():
    ...
```

## 七、测试类设计模式

📦 按功能分组：

```python
class TestCommonExportQueryResourceMixin:
    """测试导出功能相关的方法"""

    def test_update_headers_default(self):
        """测试默认的 update_headers 方法"""
        ...

    def test_update_cluster_info_default(self):
        """测试默认的 update_cluster_info 方法"""
        ...


class TestCommonQueryResourceMixin:
    """测试查询功能相关的方法"""

    def test_common_query_cluster_success(self):
        """测试集群通用属性查询 - 成功"""
        ...
```

## 八、断言规范
```python
# ✅ 清晰的断言
def test_example(self):
    result = some_function()

    # 1. 验证返回值类型
    assert isinstance(result, dict)
    # 2. 验证必要字段存在
    assert "cluster_id" in result
    assert "cluster_name" in result
    # 3. 验证字段值
    assert result["cluster_id"] == expected_id
    assert len(result["instances"]) > 0
    # 4. 验证格式
    assert ":" in result["ip_port"]  # 格式应该是 ip:port
```

## 九、避免的常见错误

```python
# ❌ 错误 1：不清理测试数据
@pytest.fixture
def test_cluster():
    cluster = Cluster.objects.create(...)
    return cluster  # ❌ 没有清理

# ✅ 正确写法
@pytest.fixture
def test_cluster():
    cluster = Cluster.objects.create(...)
    yield cluster
    cluster.delete()
```

```python
# ❌ 错误 2：创建重复数据
@pytest.fixture
def test_module():
    return DBModule.objects.create(db_module_id=111, ...)  # ❌ 重复主键

# ✅ 正确写法
@pytest.fixture
def test_module():
    module, created = DBModule.objects.get_or_create(
        db_module_id=111,
        defaults={...},
    )
    yield module
    if created:
        module.delete()
```

```python
# ❌ 错误 3：过度使用 Mock
@patch("backend.db_meta.models.Cluster.objects.filter")
def test_example(self, mock_filter):
    mock_filter.return_value = [...]  # ❌ Mock 了数据库查询

# ✅ 正确 - 真实创建数据
def test_example(self, test_cluster):
    result = Cluster.objects.filter(id=test_cluster.id)
    ...
```

## 十、实际示例
```python
@pytest.fixture
def test_cluster_with_entries(test_bk_biz_id, test_cluster_module, test_city):
    """创建包含完整入口的测试集群"""
    cluster_name = get_random_string(6)

    # 1. 创建集群
    cluster = Cluster.objects.create(
        name=cluster_name,
        cluster_type=ClusterType.TenDBHA,
        immute_domain=f"{cluster_name}.test.db",
        bk_biz_id=test_bk_biz_id,
        db_module_id=test_cluster_module.db_module_id,
    )

    # 2. 创建机器和实例
    master_ip = get_random_ip()
    machine = Machine.objects.create(ip=master_ip, bk_city=test_city, ...)
    storage = StorageInstance.objects.create(machine=machine, port=20000, ...)
    storage.cluster.add(cluster)

    # 3. 创建入口
    ClusterEntry.objects.create(
        cluster=cluster,
        cluster_entry_type=ClusterEntryType.DNS.value,
        entry=cluster.immute_domain,
    )

    yield cluster

    # 4. 清理数据
    ClusterEntry.objects.filter(cluster=cluster).delete()
    StorageInstance.objects.filter(cluster=cluster).delete()
    cluster.delete()
    Machine.objects.filter(bk_biz_id=test_bk_biz_id).delete()


class TestCommonQueryResourceMixin:
    @patch("backend.db_services.ipchooser.query.resource.ResourceQueryHelper.search_cc_cloud")
    def test_common_query_cluster_success(self, mock_cc_cloud, test_cluster_with_entries):
        """测试集群通用属性查询 - 成功"""
        cluster = test_cluster_with_entries
        mock_cc_cloud.return_value = {"0": {"bk_cloud_name": "Default Area"}}

        # 调用被测方法
        headers, data_list = CommonQueryResourceMixin.common_query_cluster(
            bk_biz_id=cluster.bk_biz_id,
            cluster_types=[ClusterType.TenDBHA],
            cluster_ids=[cluster.id],
        )

        # 断言验证
        assert len(headers) > 0
        assert len(data_list) == 1
        assert data_list[0]["cluster_id"] == cluster.id
```

## 十一、运行测试
```bash
# 激活虚拟环境并运行测试
source .venv/bin/activate
export $(cat local.test.env | xargs)

# 运行单个测试文件
pytest backend/tests/db_services/dbbase/resources/test_query.py -v

# 运行单个测试类
pytest backend/tests/db_services/dbbase/resources/test_query.py::TestCommonQueryResourceMixin -v

# 运行单个测试方法
pytest backend/tests/db_services/dbbase/resources/test_query.py::TestCommonQueryResourceMixin::test_common_query_cluster_success -v

# 显示详细错误信息
pytest backend/tests/db_services/dbbase/resources/test_query.py -v --tb=short
```

## 🎯 核心原则总结（重点）
- 真实数据优先：尽量使用真实数据库记录
- 正确清理：按外键关系逆序删除数据
- 隔离独立：每个测试互不影响
- Mock 最小化：只 Mock 外部服务（CC、DNS、Job 等）
- 描述清晰：测试名称清楚说明测试场景
- 覆盖率优先：样例精简但要提升单测覆盖率
- 无需额外输出说明文档

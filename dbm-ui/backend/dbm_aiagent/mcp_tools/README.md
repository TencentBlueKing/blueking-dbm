# MCP 工具开发指南

## 目录结构说明



## 核心概念

### 1. MCP 工具（MCP Tools）
MCP（Model Context Protocol）工具是一组 API 接口，用于为 AI Agent 提供数据库管理相关的功能。每个 MCP 工具可以包含多个 API 接口。

### 2. 目录命名规范
- 工具目录应放在 `backend/dbm_aiagent/mcp_tools/` 下
- 目录名即为 `agent_type`（如 `mysql`、`redis`）
- 文件名即为 `mcp_type`（如 `cluster.py`）

### 3. Operation ID 生成规则
装饰器会自动根据文件路径生成 `operation_id`，格式为：
```
mcp_{agent_type}_{mcp_type}_{function_name}
```
例如：`mcp_common_cluster_get_cluster_base_info`

这个 `operation_id` 就是实际mcp的工具命名，具有唯一性，所以尽可能 function_name 不要重复

## 开发步骤

### 步骤 1: 定义 MCP 工具常量

在 `constants.py` 中添加新的 MCP 工具枚举：

```python
class DBMMcpTools(StrStructuredEnum):
    DBM = EnumField("dbm-mcp", "DBM")
    YOUR_TOOL = EnumField("your-tool-name", "Your Tool Name")  # 新增
```

### 步骤 2: 创建工具目录和文件

在 `mcp_tools/` 下创建新的组件工具目录，例如 `mysql/`：
```
backend/dbm_aiagent/mcp_tools/
└── mysql/
    ├── __init__.py
    ├── your_feature.py      # mcp视图实现
    ├── serializers.py       # 序列化器
    └── urls.py              # 路由配置
```
当然如果你认为你的mcp工具是通用的，也可以放到 `common` 中

### 步骤 3: 定义序列化器

在 `your_tool/serializers.py` 中定义请求和响应序列化器，序列化器的字段需要明确声明数据结构类型和相关注释。
```python
from django.utils.translation import gettext as _
from rest_framework import serializers

class YourFeatureInputSerializer(serializers.Serializer):
    """请求参数序列化器"""
    param1 = serializers.CharField(help_text=_("参数1"))
    param2 = serializers.IntegerField(help_text=_("参数2"), required=False)

class YourFeatureOutputSerializer(serializers.Serializer):
    """响应序列化器"""
    result = serializers.CharField(help_text=_("结果"))
    data = serializers.DictField(help_text=_("数据"))
```

### 步骤 4: 创建 ViewSet

在 `your_tool/your_feature.py` 中创建视图类，每个视图函数需要用 `mcp_tools_api_decorator` 进行装饰，这样会自动注册为 MCP 工具

```python
class YourFeatureViewSet(McpToolsViewSet):
    """你的功能 ViewSet"""

    default_permission_class = []  # 根据需要设置权限类

    @mcp_tools_api_decorator(
        description=_("MCP功能描述"),
        request_slz=YourFeatureInputSerializer,
        response_slz=YourFeatureOutputSerializer,
        tags=[DBMMCPTags.READ],  # 或 DBMMCPTags.WRITE
        mcp=[DBMMcpTools.YOUR_TOOL],  # 指定所属的 MCP 工具
    )
    def your_feature(self, request, *args, **kwargs):
        """
        实现你的业务逻辑
        注意：装饰器内部会自动应用 @action 装饰器，无需手动添加
        """
```

#### 使用 reference_view（引用已有视图）

如果你想复用已有视图的逻辑和权限校验，可以使用 `reference_view` 参数：

```python
from backend.db_services.dbbase.views import DBBaseViewSet

@mcp_tools_api_decorator(
    description=_("获取集群详细信息"),
    request_slz=YourFeatureInputSerializer,
    response_slz=YourFeatureOutputSerializer,
    reference_view=DBBaseViewSet.filter_clusters,  # 引用已有视图
    tags=[DBMMCPTags.READ],
    mcp=[DBMMcpTools.YOUR_TOOL],
)
def filter_clusters(self, request, *args, **kwargs):
    """这个方法会复用 DBBaseViewSet.filter_clusters 的逻辑和权限校验"""
    return Response()
```

**注意**：使用 `reference_view` 时，函数名必须与引用的视图函数名一致。

### 步骤 5: 配置路由

在 `your_tool/urls.py` 中配置路由：

```python
from rest_framework.routers import DefaultRouter

from backend.dbm_aiagent.mcp_tools.your_tool.your_feature import YourFeatureViewSet

routers = DefaultRouter(trailing_slash=True)
routers.register(r"your_feature", YourFeatureViewSet, basename="mcp-your-tool-your-feature")

urlpatterns = routers.urls
```

在 `mcp_tools/urls.py` 中注册子路由：

```python
from django.urls import include, path

urlpatterns = [
    path("common/", include("backend.dbm_aiagent.mcp_tools.common.urls")),
    path("your_tool/", include("backend.dbm_aiagent.mcp_tools.your_tool.urls")),  # 新增
]
```

### 步骤 6: 配置 MCP 服务器

如果你的 MCP 工具是新声明的，则需要在 `config/default.py` 中配置 MCP 服务器信息：

```python
BK_APIGW_STAGE_MCP_SERVERS = [
    {
        "name": "dbm-mcp",
        "description": "DBM MCP Server",
        "labels": ["database", "management"],
        "is_public": False,
        "status": "active",
        "target_app_codes": ["your_app_code"],
    },
    # 如果需要新增 MCP 服务器，在这里添加配置
]
```

### 步骤 7: 生成 API 网关资源文件

运行命令生成 MCP 资源文件：

```bash
python manage.py sync_saas_apigw --mcp
```

## 开发调试

* 目前 paas 环境没有 bkai 基建, 没办法验证 mcp 和 llm 的结合效果
* 即使是想单独验证 mcp 也要在 paas 环境发布两次
* 发布正式环境验证联调效果是不合理的

所以需要能在开发环境简便联调验证

### 本地 mcp-server 搭建
在 `blueking-dbm/dbm-services/common/db-mcp-server` 执行 `make dev-bin VERSION=0 GITDATE=$(date +%y%m%d%H%M)` 编译 mcp-server

1. 修改 mcp 代码后, 执行 `python manage.py sync_saas_apigw --only_mcp_resource` 更新本地描述文件
2. `export DEBUG_MCP=1; python manage.py runserver appdev.aaa.bbb.com:8080` 以调试模式启动 django 服务, server url 没啥要求, 随便
3. `build/db-mcp-server --bind-address 0.0.0.0:9191  --mcp-backend-base-url http://appdev.aaa.bbb.com:8080/` 启动 mcp-server
4. 如果想本地启动 bkai agent, 参考其他文档

### 联调配置
基于 `CodeBuddy`

```json
{
  "mcpServers": {
    "my-custom-mcp": {
      "type": "sse",
      "url": "http://localhost:9191/sse"
    }
  }
}
```

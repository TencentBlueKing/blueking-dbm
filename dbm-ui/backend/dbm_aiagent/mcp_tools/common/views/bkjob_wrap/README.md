# BKJob Wrap MCP 开发指引

MCP 分组：`bkjob-wrap`

默认权限：`McpIsDbaPermission`

通过蓝鲸作业平台在目标主机执行 shell 脚本。典型调用流程：**下发脚本 MCP → `query_result` 查结果**。

---

## 约定

1. **`query_result` 是公共查询**，封装了作业状态、各主机 exit_code / log 等，基本不用二开。
2. **`current_date_and_ip` 是 DEMO**，演示如何新增一个脚本类 MCP，可直接参考，勿当业务接口用。
3. **`impl/execute_script` 严禁直接暴露为 MCP**。它是内部下发通道，必须在 view 里写死 inline 脚本后再调用。
4. **一个功能一个 MCP 一个 inline 脚本**。不要把「任意脚本执行」做成通用 MCP。
5. **按功能按需决定是否启用 Callee Plan**（`enable_callee_plan=True`）。
6. **只支持 bash/sh 脚本**（`script_language: 1`）。不要传 Python / Perl 等。
7. **会自动注入 `LOCAL_IP` 环境变量**，表示本机 IP。注入点在 shebang / 空行 / 注释 / `set ...` 之后；脚本里直接用 `$LOCAL_IP`。
8. **`bk_scope_type`、`bk_scope_id` 没法省**。作业平台 API 强制要求，所有下发与查询都要带。`bk_scope_type = biz` 时 `bk_scope_id` 为 `bk_biz_id`；`bk_scope_type = biz_set` 时 `bk_scope_id` 为业务集 ID。

---

## 新增 MCP 步骤

以 `current_date_and_ip` 为例：

### 1. Serializer

`serializers/bkjob_wrap/<feature>.py` — 定义入参；出参可复用 `ExecuteScriptOutputSerializer`。

### 2. View

在 `viewset.py` 增加方法：

```python
@mcp_tools_api_decorator(
    description=_("..."),
    request_slz=YourInputSerializer,
    response_slz=ExecuteScriptOutputSerializer,
    tags=[DBMMCPTags.WRITE],
    mcp=[DBMMcpTools.BKJOB_WRAP],
    name_prefix="bkjob_wrap",
    enable=True,
    # enable_callee_plan=True,  # 按需
)
def your_feature(self, request, *args, **kwargs):
    ...
    script = """..."""  # inline，写死在 view 里
    job_instance_id = execute_script(
        name="your_feature",
        username=request.user.username,
        bk_cloud_id=...,
        ips=...,
        script=script,
        run_as="root",
        bk_scope_type=...,
        bk_scope_id=...,
    )
    return Response({
        "job_instance_id": job_instance_id,
        "bk_scope_type": bk_scope_type,
        "bk_scope_id": bk_scope_id,
    })
```

### 3. 查结果

调用方拿 `job_instance_id` + `bk_scope_type` + `bk_scope_id` 调 `bkjob_wrap_query_result`。

---

## 现有 MCP

### bkjob_wrap_query_result

| 项 | 说明 |
|---|---|
| 描述 | 查询作业执行结果 |
| 读/写 | 读 |
| Callee Plan | 否 |

公共接口，一般无需改动。见 `serializers/bkjob_wrap/query_result.py`。

### bkjob_wrap_current_date_and_ip（DEMO）

| 项 | 说明 |
|---|---|
| 描述 | 获取目标机器的当前日期和 IP |
| 读/写 | 写 |
| Callee Plan | 否 |

```bash
echo $LOCAL_IP && date
```

---

## 目录结构

```
impl/bkjob_wrap/
  execute_script.py   # 内部下发，勿暴露 MCP
  query_result.py     # 内部查询，已由 query_result MCP 暴露
serializers/bkjob_wrap/
  <feature>.py        # 各功能入参
  execute_script.py   # 公共出参 ExecuteScriptOutputSerializer
  query_result.py     # query_result 入参/出参
views/bkjob_wrap/
  viewset.py          # MCP 入口
```

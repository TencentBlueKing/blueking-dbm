# review 任务详情

改 `src/views/task-history/detail/**` 时扫这些复发点。节点操作四个入口另见 known-issues `node-operation-fork.md`。

- 默认定位是否仍按失败 > 待继续 > 进行中，且只在首次定档
- 页头标题空值回退是否仍是 `flow_alias || ticket_type_display || root_id`
- 画布跳过 / 重试是否与节点状态一致
- 日志行号、收尾请求、编辑器换行、`focusElement` 重试上限有没有被改坏
- 展开子流程后连线会不会重合或压到内容上

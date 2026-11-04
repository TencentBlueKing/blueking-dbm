# 自写 footer 的取消按钮必须走离开确认

- **命中**：新增或修改 `DbSideslider` / `DbDialog` 的 `#footer`，里面有「取消」「关闭」按钮。存量排查：
  ```bash
  rg -l '<(DbSideslider|DbDialog)\b' src -g '*.vue' -g '*.tsx' | xargs rg -l '#footer' \
    | xargs rg --files-without-match 'beforeClose\(\)|useBeforeClose|leaveConfirm' | xargs rg -l '<DbForm|<EditableTable'
  ```
  另一种形态搜不出来，要读代码：弹层绑了 `:before-close`，但 footer 的取消按钮调的函数只是把 `isShow` 置 false
- **为什么**：组件的离开确认只挂在关闭图标、Esc、遮罩上（`before-close`）。自写 footer 后自带的取消按钮不渲染，取消按钮直接置
  `isShow = false` 就绕过了离开确认，编辑过的内容不提示直接丢
- **改成**：按顺序选
  1. **先看能不能删掉 `#footer` 用组件自带的**。自带确定按钮调的是插槽内**子组件** `defineExpose` 的 `submit`（取消调
     `cancel`），由 `hooks/useModelProvider.ts` 在弹层子树里查找；弹层所在组件自己的方法找不到。所以只有内容本来就是独立子组件、
     且它 expose 了 `submit`（返回 Promise，成功 resolve、失败 reject）时才能用。可配的只有 `confirm-text` / `cancel-text` /
     `disabled-confirm`（字符串时带 tooltip）/ `show-confirm`。照抄 `views/db-manage/riak/common/AddNodes.vue` 的 expose 写法
  2. **用不了自带的，就给弹层加 ref，取消按钮先 await `beforeClose()`**：
     ```vue
     <DbSideslider ref="sideslider" ...>
     ```
     ```ts
     const sidesliderRef = useTemplateRef('sideslider');

     // 点取消按钮：内容编辑过先弹离开确认，确认离开后再关闭
     const handleCancel = async () => {
       if (await sidesliderRef.value!.beforeClose()) {
         isShow.value = false;
       }
     };
     ```
     原关闭函数还被 `@closed`、提交成功后复用时不要改它，另起 `handleCancelClick` 守卫后再调原函数。弹层传了自己的
     `:before-close` 时，暴露的 `beforeClose()` 会转调它，不用另写判断
- **不要**：
  - 为了用自带 footer 把同一文件里的表单拆成「外壳 + 内容子组件」。只服务这一处的拆分违反 AGENTS.md 的「不抽离没有复用性的代码」，
    ref 写法改动量小得多
  - 在取消按钮里自己调 `leaveConfirm()` / `useBeforeClose()`：绕过了组件确认后还原页面 `changeConfirm` 的逻辑，关闭后页面状态会错
- **存量**：上面的命令当前只剩 `src/views/db-manage/mysql/common/apply/Index.vue`、`src/views/db-manage/sqlserver/common/apply/Index.vue`，
  两处都是表单在页面上、弹窗只做预览，「关闭」不需要确认，不用改
- **核实**：2026-11-04

## 补充

- 这条只保证「取消」会进离开确认，能不能弹出来还要看内容有没有被标记为已编辑。`DbForm` 只盯 `model`，子组件自己维护的状态
  （如 `views/monitor-alarm/common/monitor-data/AggInfo.vue`）不经过 `model` 就不会被标记，这种只能在页面上实测
- 2026-11-04 按此规则修了 26 个文件：没有自带 footer 可用的（表单都写在弹层所在组件里），全部用了 ref 写法

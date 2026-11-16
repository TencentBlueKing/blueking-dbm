# 弹层提交成功：关闭弹层，列表场景刷新列表

`DbSideslider` / `DbDialog` 里的新建、编辑表单提交成功后，**一律关闭弹层**；弹层由列表打开时，**列表重新请求数据**。
不要提交后留在弹层里回填结果，也不要只就地改列表里的那一行。

## 为什么

- 留在弹层里回填，要额外处理表单基线重置、已编辑状态复位、弹层内其它 Tab 的刷新，代码多且容易漏
- 就地改行只能改到前端知道的字段：后端派生的字段（更新人、更新时间、权限、排序位置、是否还命中当前筛选）都会和服务端不一致

## 写法

弹层组件只负责提交、提示、关闭，然后 emit 一个不带数据的 `success`；刷新由打开它的列表决定。

弹层（自写 `#footer`）：

```ts
type Emits = (e: 'success') => void;

const handleSubmit = () => {
  formRef.value!.validate().then(() => {
    isSubmitting.value = true;
    updateXxx(formData)
      .then(() => {
        messageSuccess(t('保存成功'));
        // 直接置 false 关闭：提交成功不弹离开确认，DbSideslider / DbDialog 关闭时自动还原离开确认状态
        isShow.value = false;
        emits('success');
      })
      .finally(() => {
        isSubmitting.value = false;
      });
  });
};
```

列表：

```vue
<XxxEdit
  v-model:is-show="isShowEdit"
  @success="fetchData" />
```

- 用组件自带 footer（子组件 `defineExpose` 的 `submit`）时，`DbSideslider` / `DbDialog` 在 `submit` resolve 后已自动关闭，只需 emit `success`
- 提交成功的关闭直接置 `isShow = false`，不要走 `beforeClose()`；`beforeClose()` 只给「取消」按钮用（见 known-issues `popover-footer-cancel`）
- `fetchData` 沿用列表现有的取数函数，带上当前搜索条件，不要另写一份请求
- 新建、编辑、删除共用同一个刷新入口，不要各写各的

参考实现：`views/whitelist/list/components/WhitelistOperation.vue`（提交成功 `handleCancel()` + `emits('successed')`）与
`views/whitelist/list/Index.vue`（`@successed="fetchTableData"`）。

## 注意

- **开启 `releate-url-query` 的 `DbTable`，`fetchData` 会回到第 1 页**（URL 联动下每次 `fetchData` 都重置页码）。同族列表都接受这个行为，
  不要为了「留在当前页」改回就地改行，也不要在页面里绕过 `DbTable` 自己改 `pagination`；确需原地刷新，是给 `DbTable` 加 API 的事，先问
- 弹层不是从列表打开的（详情页上的编辑、工具箱里的弹窗）没有列表可刷，关闭弹层后刷新所在页面的数据即可
- 需求明确要求「保存后留在弹层」时以需求为准，但要在 design 里写明，并回填服务端返回值而不是本地表单值

## 不要

- emit 时带上表单数据或接口返回值让列表就地 patch 行
- 提交成功后只 `messageSuccess`、不关闭弹层，让用户自己点取消（会被当成未保存内容触发离开确认）
- 弹层内部直接调用列表的刷新方法（通过 inject / 全局事件），刷新与否由打开方决定

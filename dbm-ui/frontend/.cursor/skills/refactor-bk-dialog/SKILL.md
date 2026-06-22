---
name: refactor-bk-dialog
description: >-
  重构 dialog（弹窗）组件。Use when the user asks to refactor, 重构, 改造 a dialog / 弹窗 / BkDialog component.
disable-model-invocation: true
---

# Refactor BkDialog

重构项目中的 dialog（弹窗）组件。

## 适用场景

- 用户要求重构现有的 dialog / 弹窗组件
- 用户提到 `BkDialog`、`bk-dialog`、`DbDialog`、`Dialog` 相关重构

## 重构步骤

#### 查找所有使用 DbDialog 的地方

#### 判断是否使用了 DbDialog 的 footer slot

#### footer 替换

```vue
<DbDialog>
  <template #footer>
    <BkButton
        class="w-88"
        :disabled="selected.length === 0"
        theme="primary"
        @click="handleSubmit">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        class="ml-8 w-88"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
  </template>
</DbDialog>
```

重构为

```vue
<DbDialog
  :confirmText="t('确定')"
  :cancelText="t('取消')"
  :confirmHandler="confirmHandler"
  :cancelHandler="cancelHandler">

</DbDialog>

<script>
  const confirmHandler: () => Promise<any>
  const cancelHandler: () => Promise<any>
</script>
```

- `button`用`confirmText`、`cancelText`代替
- 如果`button`上面有 `@click` 分别重构为 `confirmHandler`、`、cancelHandler`
- 如果第一个`button`上面有 `disable`和`tips`相关的信息，重构方案改成用`confirmButtonDisableInfo`实现

## 注意事项

- 忽略 src/components/db-dialog 目录
- 只使用于使用了 DbDialog footer 的场景

## 检查清单

- 最后需要输出所有重构的 Dialog 文件路径在项目根目录保存为 refactor-dialog-result.txt

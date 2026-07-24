---
name: refactor-bk-slideslider
description: >-
  重构 slideslider（侧滑面板）组件。Use when the user asks to refactor, 重构, 改造 a slideslider / sideslider / 侧滑 /
  DbSideslider component.
disable-model-invocation: true
---

# Refactor BkSlideslider

重构项目中的 slideslider（侧滑面板）组件。

## 适用场景

- 用户要求重构现有的 slideslider / sideslider / 侧滑面板组件
- 用户提到 `DbSideslider`、`bk-sideslider` 相关重构

## 重构步骤

#### 查找所有使用 DbSideslider 的地方

#### 判断是否使用了 DbSideslider 的 footer slot

#### footer 替换

```vue
<DbSideslider>
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
</DbSideslider>
```

重构为

```vue
<DbSideslider
  :confirmText="t('确定')"
  :cancelText="t('取消')"
  :confirmHandler="confirmHandler"
  :cancelHandler="cancelHandler">

</DbSideslider>

<script>
  const confirmHandler: () => Promise<any>
  const cancelHandler: () => Promise<any>
</script>
```

- `button`用`confirmText`、`cancelText`代替
- 如果`button`上面有 `@click` 分别重构为 `confirmHandler`、`、cancelHandler`
- 如果第一个`button`上面有 `disable`和`tips`相关的信息，重构方案改成用`confirmButtonDisableInfo`实现

## 注意事项

- 忽略 src/components/db-sideslider 目录
- 只使用于使用了 DbSideslider footer 的场景

## 检查清单

- 最后需要输出所有重构的 DbSideslider 文件路径在项目根目录保存为 refactor-sideslider-result.txt

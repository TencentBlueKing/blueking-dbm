# 表单项用 DbFormItem、输入框用 DbInput，不用 BkFormItem / BkInput

- **命中**：`rg -n '<(BkInput|bk-input|BkFormItem|bk-form-item)(\s|>|/|$)' <本次改动的文件>`，或你正要新写表单项 /
  输入框。`eslint.config.mjs` 的 `vue/no-restricted-syntax` 会对这两个标签报 warn
- **为什么**：项目规范要求基础控件先用本地实现。`DbInput`（`src/components/bkui-vue/input/Index.vue`）是 `.dbm-input`
  这套视觉与交互；`DbFormItem`（`src/components/db-form/item.vue`）在 `BkFormItem` 外额外 provide `DBMFormItem`，
  `src/hooks/useFormItem.ts` 的使用方（如 `src/components/ip-selector/IpSelector.vue`）只认它，放在裸 `BkFormItem`
  里拿不到表单项、不会触发校验。同一表单里混用 `Bk*` / `Db*` 会出现视觉与校验行为不一致
- **改成**：标签名直接替换，属性、事件、插槽不用改（`DbFormItem` 用 `v-bind="attrs"` 透传，`DbInput` 支持
  `type="textarea"`、`rows`、`maxlength`、`clearable`、`prefix` / `suffix` 插槽，字数计数显示条件与 bkui 一致）。
  两个都已在 `src/common/importComps.ts` 全局注册，不要 import：

  ```vue
  <DbFormItem
    :label="t('备注')"
    property="remark">
    <DbInput
      v-model="formData.remark"
      :maxlength="500"
      :rows="4"
      type="textarea" />
  </DbFormItem>
  ```

  `DbFormItem` 的 ref 只暴露 `validate` / `clearValidate`；替换前若代码通过 ref 调用 `BkFormItem` 的其他方法或读
  `$el`，先确认替换后仍可用，说不清就保持原样并在回复里报告
- **不要**：把规则升到 `error`。存量文件多，`lint-staged` 会让任何人改到这些文件时被迫整文件迁移，迁移面远超当次需求
- **不要**：顺手把同文件里本次没碰到的 `BkInput` / `BkFormItem` 一起换掉，按 SKILL.md 的修改边界只报告
- **不要**：在 `BkComposeFormItem` 里放 `DbInput` 拼并排控件，见 [compose-form-item-db-component.md](compose-form-item-db-component.md)
- **存量**：`rg -l '<(BkInput|bk-input)(\s|>|/|$)' src | wc -l` 当前 177 个文件；
  `rg -l '<(BkFormItem|bk-form-item)(\s|>|/|$)' src | wc -l` 当前 264 个文件
- **核实**：2026-11-24

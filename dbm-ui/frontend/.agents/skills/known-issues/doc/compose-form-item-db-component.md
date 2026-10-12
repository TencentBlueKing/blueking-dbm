# BkComposeFormItem 里放本地 Db* 组件，第二个控件会掉到下一行

- **命中**：`rg -n --multiline --multiline-dotall "<BkComposeFormItem.*?<Db[A-Z]" src`，或你正要往
  `<BkComposeFormItem>` 里新增一个本地 `Db*` 组件（`DbSelect` / `DbInput` / `DbTagInput`）跟输入框拼成「输入 +
  单位」「输入 + 后缀」的并排控件
- **为什么**：bkui 的并排靠 `.bk-compose-form-item > .bk-input, > .bk-select …` 这一串规则给直接子元素
  `float: left` + `margin-left: -1px` + 接缝圆角；本地实现的根类名是 `.dbm-input` / `.dbm-select`（见
  `src/components/bkui-vue/*/Index.vue`），选择器匹配不上，float 落不到第二个控件上，于是它换行掉到下面，
  而它的下拉箭头是绝对定位，仍留在上一行的位置（临时密码修改「有效时长」，2026-10-12）
- **改成**：并排布局不要交给 `BkComposeFormItem`，用普通 flex 容器自己处理接缝，照抄
  `src/views/temporary-paassword-modify/components/form-item/ValidDuration.vue`：

  ```less
  .valid-duration {
    display: flex;

    .valid-duration-input {
      width: 300px;
      border-right: none;
      border-radius: 2px 0 0 2px;
    }

    .valid-duration-type {
      width: 88px;

      :deep(.dbm-select-input-box) {
        border-radius: 0 2px 2px 0;
      }
    }
  }
  ```

  `DbSelect` 的边框长在内部 `.dbm-select-input-box` 上（根 `.dbm-select` 无边框），所以圆角要 `:deep()` 进去改。
  同一个页面里 `src/views/db-manage/common/password-input/Index.vue` 的 `.password-form-item` 就是这个形态
  （输入框 `border-right: none` + 按钮），跟着它抄视觉一致
- **不要**给 `DbSelect` 挂 `class="bk-select"` 骗过 float 规则：根类名与内部整套样式都是 `dbm-` 前缀，float
  骗过来了也拿不到 `.bk-compose-form-item-head/tail` 的接缝圆角，只是把掉行换个报法
- **不要**改 `src/components/bkui-vue/select/Index.vue` 的根类名去对齐 bkui（`DbSelect` 的引用点遍布 `src/`，
  改动面远超这一个并排需求）
- **存量**：`rg -n --multiline --multiline-dotall "<BkComposeFormItem.*?<Db[A-Z]" src` 当前 4 个文件命中。3 个
  真实使用点在同一目录族里，都已带 `display: flex` 覆盖（同一个坑的既成绕法），不动；`Spec.vue` 那处的
  `DbSelect` 已被注释掉：
  - `src/views/resource-manage/pool/components/summary-view/components/list/components/search-box/components/Spec.vue`
  - `src/views/resource-manage/pool/components/summary-view/components/list/components/search-box/components/Region.vue`
  - `src/views/resource-manage/pool/components/host-list/components/search-box/components/com-factory/components/SpecId.vue`
  - `src/views/resource-manage/pool/components/host-list/components/search-box/components/com-factory/components/CitySubzones.vue`
- **核实**：2026-10-12

---
name: create-component
description: >-
  创建组件，新建组件，生成组件
---

# 组件路径与文件命名

## 目录位置

- 通用组件：`src/components/<component-name>/Index.vue`
- 业务组件：放在所属业务目录下，如 `src/views/db-manage/<db>/<feature>/components/`

## 命名规则

- 组件目录：kebab-case，如 `cluster-selector`
- 组件入口文件：固定为 `Index.vue`
- 子组件文件：PascalCase，如 `SubPart.vue`
- 仅本组件使用的子组件，放在同级 `components/` 目录下

## 结构示例

```
src/components/
  my-component/
    Index.vue          # 组件入口
    components/        # 子组件（可选）
      SubPart.vue
```

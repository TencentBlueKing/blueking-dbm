# 项目独有的编码约定

只列工具查不出来的。导入顺序、模板属性顺序、缩进格式由 ESLint / Prettier / Stylelint 强制，写错跑一次 `--fix`
就会自动修，不必手工记忆。

`AGENTS.md`「项目独有约定」里留了其中最高频的六条摘要，本篇是完整清单。

## 脚本

- **vue / vue-router 的 API 已 auto-import**：`ref`、`computed`、`watch`、`useRouter`、`useRoute` 等不要显式 import
- script setup 宏顺序：`defineOptions` → `defineProps` → `defineEmits` → `defineSlots` → `defineModel` →
  `defineExpose`
- Props 用 `interface` + `withDefaults`；Emits 用类型别名，如
  `type Emits = (e: 'change', value: string) => void`
- 不用 `any`，用具体类型或 `unknown`
- 路径别名优先于相对路径（`@services/*`、`@components/*`、`@views/*`、`@common/*`、`@utils`、`@hooks`、
  `@stores` 等），完整清单见 `tsconfig.json`
- Pinia 沿用 options 风格（`state` / `getters` / `actions`），现有 store 都是这个写法

## 模板与组件选型

- 文案一律走 `t()`（`useI18n`），语言包在 `src/locales/`
- 基础组件优先用 `src/components/bkui-vue/` 下的本地实现（如 `DbInput`，在 `src/common/importComps.ts`
  全局注册）；该目录没有的组件再用 bkui-vue 包（`main.ts` 已全局注册）；element-plus 仅存量日期类组件在用，
  新代码不要再引入
- 具体场景该用哪个组件、视觉与反馈规范见 `dbm-designer` skill

## 样式

- `<script setup>` 与 `<style>` 的内容整体缩进一级（`vueIndentScriptAndStyle`）
- 类名写完整的嵌套类名，禁止 `&_name`、`&-name`、`--name`

## 文件

- 新建 `.vue` / `.ts` 文件要带 MIT 版权头，照抄同目录已有文件的头部
- 技术栈版本不在文档里维护，以 `package.json` 为准

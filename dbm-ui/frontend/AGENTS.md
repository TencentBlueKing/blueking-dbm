# BlueKing DBM Frontend

蓝鲸 DBM（数据库管理系统）的前端，Vue 3 + TypeScript 单页应用。

## 工作目录与命令

仓库根是 `blueking-dbm`（monorepo），前端在 `dbm-ui/frontend`。**所有命令必须在 `dbm-ui/frontend` 下执行**，git
hooks 也是先 `cd dbm-ui/frontend` 再跑。

| 命令                          | 用途                                     |
| ----------------------------- | ---------------------------------------- |
| `yarn dev`                    | 开发服务，`127.0.0.1:8088`，`strictPort` |
| `yarn type-check`             | `vue-tsc --build` 全量类型校验           |
| `npx eslint <改动文件> --fix` | 校验改动文件，见下方说明                 |
| `yarn prettier`               | 格式化 `./src`                           |
| `yarn build`                  | 生产构建                                 |

`yarn lint` 是 `run-s lint:*`，覆盖范围有坑，不要当成全项目检查：`lint:oxlint` 只查 `correctness`，`lint:script`
的 eslint **只覆盖 `src/views/ticket-center/common/ticket-detail`**，`lint:lint-staged` 只处理已 `git add`
的文件。所以校验自己的改动要么直接 `npx eslint <改动文件> --fix`，要么 `git add` 后跑 `yarn lint:lint-staged`（它对
`.js/.ts/.tsx/.vue` 跑 eslint + prettier，对 `.less` 跑 stylelint）。

commit message 走 Conventional Commits，`commit-msg` 钩子会跑 commitlint 校验（type 白名单见
`commitlint.config.mjs`）。

## 改完怎么验证

`src/` 下没有单元测试，也没有单测基建。**不要为了"有测试"而新建测试文件或引入测试框架。**

**验证命令（type-check、eslint、stylelint 等）执行前先经用户确认，不要改完代码就自动跑。** 用户同意后按默认顺序执行：

1. `yarn type-check` 通过
2. 改动文件 `npx eslint <改动文件> --fix` 通过，改了样式再补 stylelint
3. 需要运行时验证的，写清「哪个页面 + 哪个操作 + 预期结果」交给人确认，不要声称自己已经验证过

## 仓库分层

- `src/` 源码
- `public/` 静态资源，构建后原样输出
- `lib/` 内部库（别名 `@lib/*`）
- `openspec/` 变更提案与规格（未纳入 git）

## src 分层

| 目录          | 职责                                                         |
| ------------- | ------------------------------------------------------------ |
| `views/`      | 页面，每个功能一个文件夹                                     |
| `components/` | 跨业务可复用 UI                                              |
| `services/`   | API、数据模型                                                |
| `stores/`     | Pinia                                                        |
| `hooks/`      | 全局 composable                                              |
| `router/`     | 路由入口，`registerModule` / `registerBusinessModule`        |
| `utils/`      | 通用工具                                                     |
| `common/`     | 常量、正则、缓存（`TicketTypes`、`DBTypes`、`ClusterTypes`） |
| `layout/`     | 导航壳                                                       |
| `locales/`    | i18n                                                         |
| `styles/`     | 全局样式                                                     |
| `types/`      | 全局 TypeScript 类型声明                                     |
| `images/`     | 图片资源                                                     |
| `directives/` | 自定义指令                                                   |
| `helper/`     | 本地缓存、校验器                                             |

组件命名：目录 kebab-case，入口固定 `Index.vue`，仅本组件使用的子文件放同级 `components/`。

页面按业务拆在 `src/views/` 下，各自有 `routes.ts`，由 `src/router/index.ts`
聚合。常见模块：`db-manage`、`ticket-center`、`resource-manage`、`monitor-alarm`、`service-apply`、`password-manage`、`db-configure`。

## 项目独有约定

只列工具查不出来的。导入顺序、模板属性顺序、缩进格式由 ESLint / Prettier / Stylelint 强制，写错跑一次 `--fix`
就会自动修，不必手工记忆。

- **vue / vue-router 的 API 已 auto-import**：`ref`、`computed`、`watch`、`useRouter`、`useRoute` 等不要显式 import
- `<script setup>` 与 `<style>` 的内容整体缩进一级（`vueIndentScriptAndStyle`）
- script setup 宏顺序：`defineOptions` → `defineProps` → `defineEmits` → `defineSlots` → `defineModel` → `defineExpose`
- Props 用 `interface` + `withDefaults`；Emits 用类型别名，如 `type Emits = (e: 'change', value: string) => void`
- 文案一律走 `t()`（`useI18n`），语言包在 `src/locales/`
- 基础组件优先用 `src/components/bkui-vue/` 下的本地实现（如 `DbInput`，在 `src/common/importComps.ts`
  全局注册）；该目录没有的组件再用 bkui-vue 包（`main.ts` 已全局注册）；element-plus 仅存量日期类组件在用，新代码不要再引入
- Pinia 沿用 options 风格（`state` / `getters` / `actions`），现有 store 都是这个写法
- 类名写完整的嵌套类名，禁止 `&_name`、`&-name`、`--name`
- 路径别名优先于相对路径（`@services/*`、`@components/*`、`@views/*`、`@common/*`、`@utils`、`@hooks`、`@stores`
  等），完整清单见 `tsconfig.json`
- 不用 `any`，用具体类型或 `unknown`
- 新建 `.vue` / `.ts` 文件要带 MIT 版权头，照抄同目录已有文件的头部
- 技术栈版本不在文档里维护，以 `package.json` 为准

## 工作方式

编码前：

- 明确假设，不确定时询问而非猜测；存在歧义时列出多种解释，不默默选定一种
- 有明显更简单的做法，直接指出
- 发现代码矛盾、逻辑不一致时暂停，请求澄清
- 重构 / 优化类需求，先理解现有功能，给出方案请求确认

改动范围：

- 只改与当前任务直接相关的代码，严格匹配现有代码风格
- 精简和重写只针对本次任务已经动到的代码；不顺手优化相邻代码、注释、排版
- 不重构原本能正常运行的模块
- 本次修改产生的无效导入、废弃变量直接删除
- 项目原有的死代码、冗余内容只做文字提醒，不擅自删除

实现取舍：

- 用最少的代码解决问题
- 不为一次性需求创建抽象层，不为"未来可能用到"增加扩展性和可配置性
- 不抽离没有复用性的代码，允许大段代码保持阅读的完整性

多步骤任务先给简短执行计划，并标注每一步的验证方式。

## 规则与技能索引

`.agents/rules/` 不会被工具自动附加，agent 按下表「什么时候读」主动加载：

| 文件               | 什么时候读                                              |
| ------------------ | ------------------------------------------------------- |
| `db-manage.mdc`    | 改 `db-manage/**`、`services/**`、`ticket-center/**`    |
| `layout.mdc`       | 改 `src/layout/**`，或新增页面要挂菜单入口              |
| `toolbox-code.mdc` | 新增或修改工具箱提单页                                  |

`.agents/skills/` 按各 `SKILL.md` 的 description 触发，其中 `dbm-frontend-design`
覆盖排版交互规范、设计令牌与四类页面骨架，新建或修改页面样式前应先读。

## 不要碰

- `dist/`、`node_modules/`、`src/types/auto-imports.d.ts`（自动生成）
- `.env.local`、`.env.production`
- `auto-copyright.js`：会重写全仓库文件，且在 `"type": "module"` 下用 `require` 会直接报错，不要执行

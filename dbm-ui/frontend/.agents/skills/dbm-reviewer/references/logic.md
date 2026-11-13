# 逻辑 bug 检查项

回答的问题：代码按写的样子跑，结果对不对。改了 `.vue` / `.ts` 就读。与版本、配置有关的判断以 `package.json`、
`tsconfig.json` 为准。

目录：条件与状态 · 响应式 · 生命周期与清理 · 组件契约 · 模板 · 类型 · 空值与下标 · 易错表达式 · 请求与异步状态

## 条件与状态

先顺着主路径把改动读一遍，再代入边界输入（空数组、0、空字符串、单个元素、接口失败）各走一遍：

- 条件写反、漏分支、`&&` / `||` 混用没加括号；提前 `return` 跳过了后面的复位或清理；
- 比较两边类型不一致：数字 id 与字符串 id 用 `===` 比较恒为假，`includes` / `Map.get` 同理；
- 状态没有复位：弹窗、侧滑关闭后再打开残留上次的输入、选中项或报错；切换 Tab、切换业务后还是上一份数据；
- 过滤、排序、分页之后还用原数组的下标取数据；
- 单位、时间换算：GB / MB、秒 / 毫秒、时区，前后是否同一口径；
- 判断「是否修改过」时比较的是同一个引用（对象被原地修改），恒为未修改。

## 响应式

- 解构 `reactive()` 对象或 store 实例后当响应式用，应改 `toRefs` / `storeToRefs`。Vue 3.5 起 `defineProps()`
  解构默认保持响应，不要报；但把解构出的 prop 直接传给 composable（`useXxx(foo)`）传的是当时的值，要写 `() => foo`；
- `<script setup>` 里拿 `ref` / `computed` 直接做 `if (hasXxx)` 判断，没写 `.value`，条件恒为真；
- 给 `reactive` 变量整体重新赋值（`state = {...}`），模板拿到的还是旧对象；
- `watch(state.count, ...)` 传进去的是一个值而不是来源，应写 getter `() => state.count`；
- `computed` 里发请求、改状态，或对来源数组原地 `sort()` / `reverse()` / `splice()`；
- 直接改 props（含对象 prop 的深层属性）；把 prop 赋给本地 `ref` 当初始值，却期望父组件更新后跟着变；
- `async` 的 `watchEffect` 回调里，第一个 `await` 之后读到的依赖不会被追踪；
- `watchEffect` 依赖失控：回调里读了本不想监听的状态，或读写同一个状态造成循环触发。

## 生命周期与清理

- `setInterval` / `setTimeout` / `addEventListener` / `ResizeObserver` 等观察器 / 第三方实例（图表、编辑器）未在
  `onBeforeUnmount` 清理；
- `<script setup>` 里同步创建的 `watch` / `watchEffect` 会随组件卸载自动 stop，不要报。在定时器、请求回调、
  普通 `async` 函数的 `await` 之后创建的 watcher 不会自动停，以及把 stop handle 存到组件外部时，才查是否漏停；
- 在 `await` 之后调用 `onMounted` 等钩子、`provide` / `inject` 或依赖组件实例的 composable，注册不上。
  `<script setup>` 顶层 `await` 由编译器恢复上下文，不要报；
- 页面被 `KeepAlive` 缓存时，轮询和全局监听只在 `onMounted` / `onBeforeUnmount` 处理，失活后仍在跑，
  应配 `onActivated` / `onDeactivated`；
- 改完状态立刻读 DOM 或调子组件方法，没等 `nextTick`；
- 模板 ref 在 `onMounted` 之前访问，或对应元素 `v-if` 为假时访问，未判空。

## 组件契约

- `emit` 的事件名或参数个数、类型与父组件的监听不一致；
- 父组件经 ref 调子组件方法，子组件却没 `defineExpose` 该方法（`<script setup>` 默认不暴露任何东西）；
- 自定义组件的 `v-model`：prop 与事件名不成对（`modelValue` / `update:modelValue`），或 `defineModel`
  与手写的同名 props + emit 混用；
- `inject` 没给默认值也没判空，祖先未 `provide` 时拿到 `undefined`；
- bkui-vue `Upload` 的 `beforeUpload` 只认严格的 `false`，`async` 函数里 `return;` 仍会上传。

## 模板

- 列表存在增删排序时 `v-for` 用 index 当 key；
- `v-if` 与 `v-for` 写在同一元素上：`v-if` 优先级更高，拿不到迭代变量；
- `{{ value || '--' }}` 会把数字 0 显示成 `--`，应用 `??`；
- 修饰符拼写（`v-model.tirm` 不会报错，只是不生效）；
- 整列共用一个 `isExpand` ref 的展开 / 收起，会让所有行一起展开，要按行 id 记。

## 类型

审查阶段不跑全量类型检查，以下靠人工看：

- 新增 `any`，含变相写法：`as any`、`Record<string, any>`、泛型没传落成 `any`、函数参数不标类型；
- 用 `as` 断言或非空断言 `!` 掩盖类型错误，尤其 `as unknown as T`；`@ts-ignore` / `@ts-expect-error` 没写原因；
- 接口返回类型、数据模型与后端字段不符：字段名、是否可空、数字还是字符串；
- 外部数据（`JSON.parse`、`localStorage`、`route.query`、`postMessage`）直接断言成具体类型而不校验。
  `route.query` 的值可能是字符串、数组或 `null`，不能直接当字符串用；
- 类型上是可选的字段被当成必有来用，或反过来为了省判空把可选改成必填。

## 空值与下标

`tsconfig.json` 未开 `noUncheckedIndexedAccess` 时，下标访问的结果不带 `undefined`，编译器不会报，以下几类只能人工看：

- `arr?.[0].x`：数组是 `[]` 时 `[0]` 为 `undefined` 照样抛，要写 `arr?.[0]?.x`；`Object.values(obj)[0]!.x` 同理；
- `map[key].list`：`map` 异步填充（如 `useAlarmSubscribe` 的 `metricsMap`）或 `key` 可能不在其中时，要写 `map[key]?.list`；
- `arr.find(...)` 的结果不判空直接取属性；
- `JSON.parse(decodeURIComponent(route.query[...]))` 没有 `try`：用 `@utils` 的 `parseQueryMemo`；
  `JSON.parse(localStorage...)` 同样要 `try` 并校验类型；
- `Array(n)` 的 n 来自除法或接口时，要守住整数且大于 0，否则 `RangeError`。

## 易错表达式

- 字符串拼接里混用三元：`a += cond ? '\n' : '' + b` 实际是 `a += cond ? '\n' : ('' + b)`，用 `map().join()` 代替；
- `a || b` 用在可能为 `0` / `''` / `false` 的合法值上，应用 `??`；
- 条件里用了没 `await` 的 Promise，恒为真；`forEach` 里写 `await`，外层并不会等；
- `sort()` 不传比较函数时按字符串比较，数字会排错；`sort()` / `reverse()` 原地修改，可能改到 props 或 store 里的数组；
- `window.open(url, '__blank')`：`'__blank'` 是普通窗口名，不是新开标签，应为 `'_blank'`。

## 请求与异步状态

错误处理与 loading：

- 异步无错误处理，或 `catch` 是空的把错误吞掉，失败后页面没有任何提示；
- 失败时 loading 不复位。手动维护的 `isLoading` 只在 `onSuccess` 里置 false 的，要补 `onError`；
- `try/finally` 里用 `.then` 而不 `await`：`finally` 会提前复位 loading，按钮可重复提交；
- 提交类按钮没有 loading 或禁用态，可连点重复提交；
- `Promise.all` 里一个失败整体失败，其余结果被丢弃。要确认这是预期，否则用 `Promise.allSettled`；
- 乐观更新（先改界面再发请求）失败后没有回滚。

竞态与时序：

- 快速切换筛选 / 分页 / Tab 产生请求竞态，后到的旧响应覆盖新数据。修法用请求序号（`let seq`，`.then` 里比对）
  或取消上一次请求；跨页全选、按域名反查集群这类「一次性」请求同样要比对；
- 组件卸载后响应才回来，仍然写状态、弹提示或跳路由；
- 轮询：上一次未返回就发下一次；页面离开没停；失败后既不停也不退避；
- 依赖前一个请求结果的请求，没等前者完成就发出去。

参数与跳转：

- 分页、排序、搜索参数与请求不同步；**换筛选条件不把 `current` 置 1**，按旧 offset 请求出空列表；
- 复制全部 / 导出 / 跨页全选另起请求时，参数要和列表 `dataSource` 一致（如资源池的 `for_biz`），不能只展开搜索参数；
- 新增或修改接口：请求方法、路径、参数名与后端不符；
- 列表数据在弹窗、抽屉里改过之后没有刷新，或刷新时丢了当前的分页与筛选；
- 开新标签打开业务路由（`taskHistoryDetail`、`bizTicketManage` 等）且数据来自别的业务时，href 要过
  `getBusinessHref(href, row.bk_biz_id)`，否则跳到当前业务下打不开。

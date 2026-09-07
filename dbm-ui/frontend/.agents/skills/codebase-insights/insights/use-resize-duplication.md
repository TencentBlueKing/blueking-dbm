# 拖拽改宽度各写一份，且两个 use-resize 同名不同义

状态：未处理

## 现象

「按住把手拖拽改宽度」这套交互在项目里有 3 处独立实现，没有共用原语。其中两处的文件名都叫
`hooks/use-resize.ts`，但语义完全不同：一个调表格列宽，一个调浮层面板宽度，签名与返回值都不一样。

更要紧的是 `table-detail-dialog/hooks/use-resize.ts` 看起来像可复用 hook，实际通过 `getCurrentInstance()?.props`
读宿主组件的 `minWidth` / `defaultOffsetLeft`，还硬查 `.navigation-container` 算默认宽。这些依赖不在参数签名里，
    10|换个组件调用会静默拿到 `undefined`。维护者踩的坑是：想复用它做第三个可拖拽面板，读完才发现复用不了，只能重写一遍——
本篇第 3 处证据就是这么来的。

## 证据

### 1. 三处独立实现，防选中与限宽各写各的

| 位置                                                        | 语义         | 拖拽期防选中                                                | 节流       | 限宽                                                        |
| ----------------------------------------------------------- | ------------ | ----------------------------------------------------------- | ---------- | ----------------------------------------------------------- |
| `components/editable-table/hooks/use-resize.ts`             | 表格列宽     | `onselectstart` + `ondragstart` 置 false（`:179`、`:182`），另在 `:262` 设 `body.style.userSelect` | 移动无节流 | `Math.max(delta, 80)`（`:197`）后再夹 `minWidth \|\| 60` / `maxWidth \|\| 1000000`（`:210-211`） |
    20|| `components/table-detail-dialog/hooks/use-resize.ts`        | 浮层宽度     | `onselectstart` + `ondragstart` 置 false（`:36`、`:39`）    | 60ms（`:17`） | `Math.max(resizeWidth, 900)`，超父宽 90% 就切成 `'90%'`（`:21-22`） |
| `views/task-history/detail/components/task-flow/Index.vue`  | 浮动侧栏宽度 | `event.preventDefault()`（`:173`）                          | 无         | `_.clamp(..., 240, 500)`（`:179`）                          |

前两处的防选中写法一致，是项目既有习惯；第 3 处（本次新增）改用了 `preventDefault`，这一条不一致是本次改动引入的。

### 2. 假抽象的具体依赖点

`components/table-detail-dialog/hooks/use-resize.ts`：

- `:7` `const currentInstance = getCurrentInstance();`
    30|- `:21` 限宽读 `currentInstance?.props.minWidth`
- `:48-49` `onMounted` 里读 `currentInstance?.props.minWidth` 与 `props.defaultOffsetLeft`
- `:51-52` 默认宽度取 `document.body.querySelector('.navigation-container')` 的宽度

四处依赖都没出现在 `(rootRef, resizeHandleRef)` 这个签名里。

### 3. 把手样式反倒是一致的

16×64 的折叠把手（`#dcdee5`，hover `#3a84ff`，`translateY(-50%)`）、8px 的 `col-resize` 条（hover 出蓝色竖线）、
拖拽期 `inset: 0` 的 mask，这三件在 `components/table-detail-dialog/Index.vue:157-215` 与
    40|`task-flow/Index.vue:287-338` 是对齐的。漂移只在 JS 行为层，不在视觉层。

## 项目里已有的正确做法

暂无。三处都是各自实现，没有一处是可以直接复用的原语。视觉层能对齐，靠的是照抄
`table-detail-dialog` 的样式而不是共用组件。

## 建议方向（未采纳）

- 若要抽，抽的边界应该是「mousedown 起一次拖拽、返回位移」这一层（参数全部显式传入：起始值、min、max、方向），
  不要把宽度写回 DOM、不要碰 `getCurrentInstance`。宽度怎么落地（写 `style.width` 还是驱动响应式变量）留给调用方
    50|- 不建议直接改 `table-detail-dialog/hooks/use-resize.ts` 去兼容第二个调用方：它的 `'90%'` 与 `900` 这类取值是
  弹窗专属语义，泛化后会把弹窗的策略带进面板
- 不建议为此引入拖拽库。三处需求都只是一维位移，库的体积换不回这点代码
- 只有 3 处且互不干扰，优先级不高；下一次再出现第 4 处可拖拽面板时再抽比较划算

## 待查证

- 只覆盖了 `mousemove` / `clientX` / `col-resize` 三个关键字命中的文件（`editable-table`、`table-detail-dialog`、
  `task-flow`、`directives/cursor`、`system-search/hooks/useKeyboard`），后两个与拖拽改宽度无关。基于
    60|  pointer 事件或 CSS `resize` 实现的拖拽没有排查
- 是否存在拖拽改「高度」的同类实现（纵向 resize）未查
- 三处的宽度是否需要持久化（刷新后保持用户拖出的宽度）未查，目前看都是内存态

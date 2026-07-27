# 框架布局

## 层级结构与固定尺寸

```
body                          100vh / min-width 1366px / overflow hidden
└─ #app
   ├─ 公告栏（可选）           --notice-height: 40px | 0px
   └─ BkNavigation             height: calc(100vh - var(--notice-height))
      ├─ navigation-header     52px   背景 #0e1525
      └─ navigation-wrapper
         ├─ 侧栏 nav           折叠 60px / 展开 260px   背景 #182132
         └─ container-content
            ├─ content-header  52px   padding 0 14px   背景 #fff   标题 16px/#313238
            └─ content-wrapper padding 20px 24px 0     overflow auto
               └─ DbRouterView height 100%
                  └─ 业务页面
```

框架固定吃掉 **104px**（顶栏 52 + 面包屑 52）。

## 内容区可用高度

```less
// 普通页面
height: calc(100vh - var(--notice-height) - 52px - 52px);

// fullscreen 页面：padding 归零，根节点必须 height: 100%
```

`content-wrapper` **没有 bottom padding**，页面底部留白需要自己补。

## 路由 meta

在 `src/views/<module>/routes.ts` 中声明。

| 字段         | 作用                                     | 何时用                                     |
| ------------ | ---------------------------------------- | ------------------------------------------ |
| `navName`    | 面包屑标题文字                           | 必填                                       |
| `fullscreen` | 内容区 padding 归零，页面自管留白        | 工具箱、详情、单据中心、需要贴边的全屏页   |
| `hideTitle`  | 隐藏标题文字但保留 52px 栏               | 标题需要自绘或 Teleport 时（MySQL 工具箱） |
| `aiBlueking` | 是否显示 AI 助手，默认显示，传 `false` 隐藏 | 不适合 AI 介入的页面                       |

工具箱路由不要手写，用 `src/utils/createToolboxRoute.ts` 的 `createRouteItem()`，它会自动补 `fullscreen`、`navName`、`ticketType`。

```ts
createRouteItem(TicketTypes.MYSQL_ADD_SLAVE, t('添加从库'), { dbConsole: 'mysql.toolbox.slaveAdd' });
```

## 两种底部固定操作区

两者规范一致（高 52px、按钮 `min-width: 88px`、间距 8px、primary 在左），**优先用 SmartAction**。

| 方案                 | 触发方式             | 占位  |
| -------------------- | -------------------- | ----- |
| `SmartAction`        | 滚动到底自动 fixed   | 50px  |
| `.absolute-footer`   | 始终 absolute        | 手动  |

```vue
<SmartAction>
  <!-- 页面内容 -->
  <template #action>
    <BkButton class="mr-8 w-88" theme="primary">{{ t('提交') }}</BkButton>
    <BkButton class="w-88">{{ t('取消') }}</BkButton>
  </template>
</SmartAction>
```

## Teleport 扩展点

需要在面包屑栏追加内容时，**不要改 Layout**，Teleport 到这两个挂载点：

- `#dbContentTitleAppend` — 标题右侧，工具箱用它挂当前工具名
- `#dbContentHeaderAppend` — 整栏最右侧

## 滚动条

| 场景                              | 宽 / 高          | thumb                    | hover     |
| --------------------------------- | ---------------- | ------------------------ | --------- |
| 全局 `*`                          | 4px              | #dcdee5                  | #979ba5   |
| `.db-scroll-y`                    | 4px              | #dcdee5                  | #979ba5   |
| `.db-scroll-x`                    | 8px              | #a0a0a0                  | —         |
| `ScrollFaker`（深色侧栏 / 工具箱） | 6px → hover 14px | rgb(151 155 165 / 80%)   | 90% 不透明 |

需要自定义滚动条且 `height: 100%` 的区域用 `<ScrollFaker>`，深色区传 `theme="dark"`。

## 参考实现

- `src/layout/Index.vue` — 主框架
- `src/styles/reset.less` — 全局 body 与字体
- `src/components/smart-action/Index.vue`
- `src/utils/createToolboxRoute.ts`

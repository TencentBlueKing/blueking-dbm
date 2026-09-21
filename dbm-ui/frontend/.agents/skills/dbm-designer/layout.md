# 框架布局

```
body                 100vh / min-width 1366px / overflow hidden
└─ 应用根节点
   ├─ 公告栏（可选）   40px（无则 0）
   └─ 导航框架         height = 100vh - 公告栏
      ├─ 顶栏          52px  #0e1525
      └─ 导航主体
         ├─ 侧栏       折叠 60px / 展开 260px  #182132
         └─ 内容容器
            ├─ 面包屑   52px  padding 0 14px  标题 16px/#313238
            └─ 内容区   padding 20px 24px 0
               └─ 业务页面
```

框架吃掉 **104px**。内容区无 bottom padding，底留白页面自补。HTML 骨架：[assets/page-frame.html](assets/page-frame.html)。菜单登记见 `dbm-frontend-developer` 的 `references/navigation-menu.md`。

| 类型 | padding | 何时用 |
| --- | --- | --- |
| 普通 | `20px 24px 0`（框架给） | 列表、配置 |
| 全屏 | 0，根节点 `height: 100%` | 工具箱、详情、要贴边的页 |

面包屑扩展点：`#dbContentTitleAppend`（标题右侧）、`#dbContentHeaderAppend`（整栏最右）。不要改框架。

吸底栏优先 `SmartAction`（滚到底才钉）；内容必然超一屏用 `.absolute-footer`。栏内按钮见 [button.md](button.md)。

`DbCard` padding 24、白底。Tab header 42px、内容 `16px 0`。向导条 `.top-steps` 在面包屑下 52px，仍归配置/申请。服务申请宫格不要复制成通用列表。

# 安全检查项

回答的问题：这次改动有没有引入可被利用的口子。改动涉及渲染 HTML、跳转、本地存储、上传下载、权限、新增依赖时读。

## 注入

- XSS：`v-html` 的内容必须先过 `DOMPurify.sanitize()`（既有写法见 `src/components/system-version-log/Index.vue`），只加
  `<!-- eslint-disable vue/no-v-html -->` 绕过 lint 而不 sanitize 按 P0 / P1 报；
- 把接口字段或用户输入拼进 `el.innerHTML` 同样是注入点，新代码改用 `textContent` 或渲染函数；
- 「剥 HTML 标签取纯文本」也不能用 `div.innerHTML = html`：赋值瞬间 `<img onerror>` 就会执行。改用
  `new DOMParser().parseFromString(html, 'text/html').body.textContent`（DOMParser 生成的文档不执行脚本、不加载资源），
  命中按 P0 报；
- 出现 `eval`、`new Function`、`setTimeout('字符串')` 执行动态字符串。

## 跳转与外部内容

- `window.open` / `location.href` 的 url 来自接口或 query 参数时，要校验同源或白名单，防 `javascript:`
  伪协议与开放重定向；
- 外链 `target="_blank"` 需带 `rel="noopener noreferrer"`；
- 上传前校验类型与大小；下载地址用后端返回值而非用户输入拼接；`iframe` 的 `src` 不接受用户输入。

## 敏感信息与权限

- 密码、token、密钥不落 `localStorage` / `sessionStorage` / `document.cookie`（经 `src/common/cache.ts`
  存的同样要看存了什么），不 `console.log`，不作为 GET query 参数或出现在 url 里；
- 前端隐藏按钮不等于有权限。下架 / 删除 / 重启 / 清档等破坏性操作必须依赖后端鉴权并有二次确认，
  不要新增只凭前端判断就发起的高危请求。

## 依赖

- 新增第三方依赖要说明来源与必要性，不引入未审计的小众包。

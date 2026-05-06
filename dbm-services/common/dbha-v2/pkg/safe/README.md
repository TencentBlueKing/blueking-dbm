# safe

`safe` 包为同步执行和 goroutine 提供 **panic-safe wrapper**，确保任何 panic 都会被 recover、记录日志并可选地触发回调，不会击穿保护层导致进程崩溃。

## 核心 API

| 函数                                   | 说明                                               |
|--------------------------------------|--------------------------------------------------|
| `Run(fn, opts...)`                   | 在当前 goroutine 执行 `fn`，recover panic 后记录日志        |
| `Go(fn, opts...)`                    | 在新 goroutine 中执行 `fn`（fire-and-forget）           |
| `GoWait(fn, opts...) func()`         | 同 `Go`，返回 wait 函数，调用后阻塞直到 goroutine 结束           |
| `GoWaits([]fn, opts...) func()`      | 同 `Go`，支持多个 func，返回 wait 函数，调用后阻塞直到 goroutine 结束 |
| `GoCtx(ctx, fn, opts...)`            | 同 `Go`，panic 时 `PanicInfo.Ctx` 会携带传入的 ctx        |
| `GoCtxWait(ctx, fn, opts...) func()` | `GoCtx` + `GoWait` 的组合                           |
| `FormatPanicInfo(pi) string`         | 将 `PanicInfo` 格式化为可读字符串，用于告警或结构化日志               |

## Option

通过 Functional Options 模式配置行为，后传入的 Option 覆盖先传入的同名设置。

| Option | 说明 |
|--------|------|
| `WithLabel(label)` | 附加一个标签，出现在 panic 日志中（空值显示为 `"-"`） |
| `WithLogger(log)` | 指定日志记录器；未设置时使用全局 `logger.Error` |
| `WithOnPanic(fn)` | panic 被 recover 并记录日志后执行的回调，用于打点、告警或清理 |
| `WithRepanic(bool)` | 仅在同步 `Run` 中生效，日志+回调完成后重新 panic；异步模式自动忽略并输出 warning |
| `WithStackMaxBytes(n)` | 限制 stack trace 输出长度（0 = 不限制） |
| `WithPanicSanitizer(fn)` | 在日志和回调之前对 reason/stack 做脱敏变换（详见下方说明） |

## 快速示例

### 基本用法

```go
// 同步执行，panic 被 recover 并记录日志
safe.Run(func() {
    // 可能 panic 的业务逻辑
    riskyWork()
})

// 异步执行，fire-and-forget
safe.Go(func() {
    riskyWork()
}, safe.WithLabel("background-task"))

// 异步执行，等待完成
wait := safe.GoWait(func() {
    riskyWork()
})
wait() // 阻塞直到完成

// 异步执行，等待所有 func 完成
wait := safe.GoWaits([]func() {
    func() { riskyWork() },
})
wait() // 阻塞直到完成
```

### 带回调

```go
safe.Go(func() {
    riskyWork()
},
    safe.WithLabel("my-worker"),
    safe.WithOnPanic(func(pi safe.PanicInfo) {
        metrics.Counter("panic_total").Inc()
        alerting.Send(safe.FormatPanicInfo(pi))
    }),
)
```

### 携带 Context

```go
ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
defer cancel()

safe.GoCtx(ctx, func() {
    riskyWork()
}, safe.WithOnPanic(func(pi safe.PanicInfo) {
    // pi.Ctx 就是传入的 ctx，可用于获取 trace ID 等上下文信息
    traceID := pi.Ctx.Value(traceKey{})
    log.Printf("panic in trace %v: %v", traceID, pi.Reason)
}))
```

### 脱敏 (Sanitizer)

```go
safe.Run(func() {
    panic("secret-token-12345")
},
    safe.WithPanicSanitizer(func(reason any, stack []byte) (any, []byte) {
        return "redacted", bytes.ReplaceAll(stack, []byte("secret"), []byte("***"))
    }),
    safe.WithOnPanic(func(pi safe.PanicInfo) {
        // pi.Reason == "redacted"，日志中也是脱敏后的值
    }),
)
```

## PanicInfo 结构

```go
type PanicInfo struct {
    Ctx         context.Context // 仅 GoCtx/GoCtxWait 时非 nil
    Reason      any             // panic 原因（经过可选的 sanitizer 处理）
    Stack       []byte          // stack trace（经过截断和可选的 sanitizer 处理）
    Truncated   bool            // stack 是否被 WithStackMaxBytes 截断
    RecoveredAt time.Time       // panic 被 recover 的时间点
}
```

## 设计要点

### 四层 recover 保护链

任何外部扩展点自身 panic 都不会击穿保护：

1. **`guard`** — recover 业务 `fn` 的 panic
2. **`safeLog`** — recover logger 自身的 panic，回退到 `log.Printf`
3. **`safeOnPanic`** — recover OnPanic 回调的 panic，回退到 `log.Printf`
4. **`safeSanitize`** — recover sanitizer 的 panic，回退到原始 reason/stack

### WithRepanic 语义

- **同步模式 (`Run`)**：日志 + 回调完成后，用**原始（未脱敏）reason** 重新 panic，供上游 `recover()` 处理
- **异步模式 (`Go`/`GoWait`/`GoCtx`/`GoCtxWait`)**：自动忽略 repanic 请求并输出 warning，防止打崩进程

### WithStackMaxBytes 与 Sanitizer 的契约

- Sanitizer 返回的 stack **会被再次截断**到 `stackMaxBytes`，因此 sanitizer 无需自行控制长度
- 脱敏后的值用于日志和 OnPanic；repanic 始终使用原始 reason

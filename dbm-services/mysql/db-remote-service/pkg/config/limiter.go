package config

import "context"

// GlobalSemaphore 全进程并发信号量, 限制同时在飞的 per-address 执行任务数.
//
// 配置项 RuntimeConfig.Concurrent 即为信号量容量.
// 满了之后新的 Acquire 会阻塞, 直到 client ctx cancel 或前序任务释放.
//
// 这是 v2 的资源保护核心: 防止一次大请求 (1000 addresses) 或并发请求洪流
// 把整个 DRS 进程的 goroutine / 文件描述符 / 后端 MySQL 连接打爆.
//
// 实现选择: 用 buffered channel 而不是 golang.org/x/sync/semaphore, 是为了:
//  1. 零外部依赖增加, 不影响项目最低 go 版本
//  2. 对齐 v1 的 tokenBulkChan 实现风格, 减少阅读成本
type chanSemaphore chan struct{}

var GlobalSemaphore chanSemaphore

// Acquire 取一个 token; ctx 取消时立即返回 ctx.Err()
func (s chanSemaphore) Acquire(ctx context.Context, n int64) error {
	for i := int64(0); i < n; i++ {
		select {
		case s <- struct{}{}:
		case <-ctx.Done():
			// 已经拿到的要还回去, 否则永久泄漏
			for j := int64(0); j < i; j++ {
				<-s
			}
			return ctx.Err()
		}
	}
	return nil
}

// Release 归还 token
func (s chanSemaphore) Release(n int64) {
	for i := int64(0); i < n; i++ {
		<-s
	}
}

// InitGlobalSemaphore 初始化全进程信号量, 在 config.InitConfig 之后调用
func InitGlobalSemaphore() {
	GlobalSemaphore = make(chanSemaphore, RuntimeConfig.Concurrent)
}

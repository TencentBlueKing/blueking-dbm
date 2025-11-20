package cmutil

import (
	"context"
	"errors"
	"fmt"
	"time"

	"dbm-services/common/go-pubpkg/logger"
)

// WithPeriodicLogging 通用的日志封装方法，定期打印执行状态
// name: 任务名称，用于日志标识
// fn: 要执行的函数
// printInterval: 日志打印间隔，如time.Minute
// timeout: 任务执行超时时间，如10*time.Minute，为0表示不超时
func WithPeriodicLogging(name string, fn func(context.Context) error,
	printInterval time.Duration, timeout time.Duration, loggerPrint *logger.Logger) error {
	loggerPrint.Info("开始执行任务: %s", name)

	// 创建一个通道来接收完成信号
	done := make(chan error, 1)
	// 创建上下文用于超时控制
	var ctx context.Context
	var cancel context.CancelFunc

	if timeout > 0 {
		ctx, cancel = context.WithTimeout(context.Background(), timeout)
		defer cancel()
		loggerPrint.Info("任务 %s 设置超时时间: %v", name, timeout)
	} else {
		ctx = context.Background()
	}

	// 启动定时日志打印
	ticker := time.NewTicker(printInterval)
	defer ticker.Stop()

	// 启动任务执行
	go func() {
		done <- fn(ctx)
	}()

	// 监控任务执行和定时日志
	for {
		select {
		case err := <-done:
			if err != nil {
				loggerPrint.Error("任务 %s 执行失败: %v", name, err)
				return err
			}
			loggerPrint.Info("任务 %s 执行完成", name)
			return nil
		case <-ticker.C:
			loggerPrint.Info("任务 %s 正在执行中...", name)
		case <-ctx.Done():
			if errors.Is(ctx.Err(), context.DeadlineExceeded) {
				loggerPrint.Error("任务 %s 执行超时，超时时间: %v", name, timeout)
				return fmt.Errorf("任务 %s 执行超时，超时时间: %v", name, timeout)
			}
			loggerPrint.Error("任务 %s 被取消: %v", name, ctx.Err())
			return fmt.Errorf("任务 %s 被取消: %v", name, ctx.Err())
		}
	}
}

package rpc

import (
	"context"
	"errors"
	"sync"

	"dbm-services/mysql/db-remote-service/pkg/config"
)

func (c *MySQLRPCRequest) execute() (res []MySQLOneAddressRPCResponse, err error) {
	// 使用带缓冲的 channel，防止阻塞
	rChan := make(chan MySQLOneAddressRPCResponse, len(c.Addresses))
	errChan := make(chan error, len(c.Addresses))

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	var wg sync.WaitGroup
	wg.Add(len(c.Addresses))

	for _, addr := range c.Addresses {
		_ = config.GlobalLimiter.Wait(ctx)

		go func(addr string) {
			defer wg.Done()

			// 在执行前检查是否已取消
			select {
			case <-ctx.Done():
				return
			default:
			}

			addrRes := MySQLOneAddressRPCResponse{Address: addr}
			cmdsRes, err := c.executeCmds(addr)
			if cmdsRes != nil {
				addrRes.CmdResults = cmdsRes
			}
			if err != nil {
				addrRes.Error = err.Error()
			}
			rChan <- addrRes
		}(addr)
	}

	// 在单独的 goroutine 中等待所有任务完成后关闭 channel
	go func() {
		wg.Wait()
		close(rChan)
		close(errChan)
	}()

	// 收集结果
	for r := range rChan {
		res = append(res, r)
	}

	// 收集所有错误
	var errs []error
	for e := range errChan {
		errs = append(errs, e)
	}

	return res, errors.Join(errs...)
}

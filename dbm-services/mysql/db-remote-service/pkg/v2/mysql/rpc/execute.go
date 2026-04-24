package rpc

import (
	"context"
	"log/slog"
	"sync"

	"dbm-services/common/go-pubpkg/apm/metric"
	"dbm-services/mysql/db-remote-service/pkg/apm"
	"dbm-services/mysql/db-remote-service/pkg/config"
)

func (c *MySQLRPCRequest) execute(ctx context.Context, user, password string) (res []MySQLOneAddressRPCResponse, err error) {
	rChan := make(chan MySQLOneAddressRPCResponse, len(c.Addresses))

	var wg sync.WaitGroup
	wg.Add(len(c.Addresses))

	for _, addr := range c.Addresses {
		go func(addr string) {
			defer wg.Done()
			runOneAddress(ctx, c, addr, user, password, rChan)
		}(addr)
	}

	go func() {
		wg.Wait()
		close(rChan)
	}()

	for r := range rChan {
		res = append(res, r)
	}

	return res, nil
}

// runOneAddress 在拿到全局信号量后执行单 address 任务, 并写回结果到 rChan.
//
// 反压语义:
//   - ctx 取消 (客户端断开 / 上层超时) 时立即放弃, 不算 throttled
//   - 信号量泄漏由 defer Release 兜底, 即使 panic 也能归还
func runOneAddress(ctx context.Context, c *MySQLRPCRequest, addr, user, password string, rChan chan<- MySQLOneAddressRPCResponse) {
	addrRes := MySQLOneAddressRPCResponse{
		Address:    addr,
		CmdResults: []MySQLCmdRPCResponse{},
	}

	if err := config.GlobalSemaphore.Acquire(ctx, 1); err != nil {
		metric.Id(apm.AddressesTotal).Inc("throttled")
		slog.Warn("v2 mysql semaphore acquire failed",
			slog.String("addr", addr),
			slog.String("error", err.Error()),
		)
		addrRes.Error = "request aborted before acquiring slot: " + err.Error()
		rChan <- addrRes
		return
	}
	defer config.GlobalSemaphore.Release(1)

	metric.Id(apm.InflightAddresses).Add(1)
	defer metric.Id(apm.InflightAddresses).Add(-1)

	cmdsRes, err := c.executeCmds(ctx, addr, user, password)
	if cmdsRes != nil {
		addrRes.CmdResults = cmdsRes
	}
	if err != nil {
		addrRes.Error = err.Error()
		metric.Id(apm.AddressesTotal).Inc("error")
	} else {
		metric.Id(apm.AddressesTotal).Inc("success")
	}

	rChan <- addrRes
}

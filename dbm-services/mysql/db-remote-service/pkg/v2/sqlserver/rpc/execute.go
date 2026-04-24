package rpc

import (
	"context"
	"log/slog"
	"sync"

	"dbm-services/common/go-pubpkg/apm/metric"
	"dbm-services/mysql/db-remote-service/pkg/apm"
	"dbm-services/mysql/db-remote-service/pkg/config"
)

func (c *SqlserverRPCRequest) execute(ctx context.Context, user, password string) (res []SqlserverOneAddressRPCResponse, err error) {
	rChan := make(chan SqlserverOneAddressRPCResponse, len(c.Addresses))

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

func runOneAddress(ctx context.Context, c *SqlserverRPCRequest, addr, user, password string, rChan chan<- SqlserverOneAddressRPCResponse) {
	addrRes := SqlserverOneAddressRPCResponse{
		Address:    addr,
		CmdResults: []SqlserverCmdRPCResponse{},
	}

	if err := config.GlobalSemaphore.Acquire(ctx, 1); err != nil {
		metric.Id(apm.AddressesTotal).Inc("throttled")
		slog.Warn("v2 sqlserver semaphore acquire failed",
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

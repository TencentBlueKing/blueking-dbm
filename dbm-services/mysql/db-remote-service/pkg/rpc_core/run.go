package rpc_core

import (
	"dbm-services/mysql/db-remote-service/pkg/config"
	"sync"

	"golang.org/x/exp/slog"
)

// Run 执行
func (c *RPCWrapper) Run() (res []oneAddressResult) {
	addrResChan := make(chan oneAddressResult)
	tokenBulkChan := make(chan struct{}, config.RuntimeConfig.Concurrent)
	slog.Debug("init bulk chan", slog.Int("concurrent", config.RuntimeConfig.Concurrent))

	go func() {
		var wg sync.WaitGroup
		wg.Add(len(c.addresses))

		for _, address := range c.addresses {
			tokenBulkChan <- struct{}{}
			go func(address string) {
				addrRes, err := c.executeOneAddr(address)
				<-tokenBulkChan

				var errMsg string
				if err != nil {
					errMsg = err.Error()
				}
				addrResChan <- oneAddressResult{
					Address:    address,
					CmdResults: addrRes,
					ErrorMsg:   errMsg,
				}
				wg.Done()
			}(address)
		}
		wg.Wait()
		close(addrResChan)
	}()

	for addrRes := range addrResChan {
		res = append(res, addrRes)
	}
	return
}

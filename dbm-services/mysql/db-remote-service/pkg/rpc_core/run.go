package rpc_core

import (
	"sync"

	"dbm-services/mysql/db-remote-service/pkg/config"
)

// Run 执行
func (c *RPCWrapper) Run() (res []OneAddressResultType) {
	addrResChan := make(chan OneAddressResultType)
	tokenBulkChan := make(chan struct{}, config.RuntimeConfig.Concurrent)
	//c.logger.Debug("init bulk chan", slog.Int("concurrent", config.RuntimeConfig.Concurrent))

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
				addrResChan <- OneAddressResultType{
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

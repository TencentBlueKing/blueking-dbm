package rpc

import (
	"context"
	"dbm-services/mysql/db-remote-service/pkg/config"
	"sync"
)

func (c *MySQLRPCRequest) do() (res []AddrResult, err error) {
	rChan := make(chan AddrResult)
	done := make(chan struct{})

	go func() {
		defer func() {
			close(rChan)
			close(done)
		}()
		var wg = &sync.WaitGroup{}
		wg.Add(len(c.Addresses))
		for _, addr := range c.Addresses {
			_ = config.GlobalLimiter.Wait(context.Background())
			go func(addr string) {
				defer wg.Done()
				cmdResults, err := c.oneAddr(addr)
				addrRes := AddrResult{
					Addr:       addr,
					CmdResults: cmdResults,
					ErrorMsg:   "",
				}
				if err != nil {
					addrRes.ErrorMsg = err.Error()
				}
				rChan <- addrRes
			}(addr)
		}
		wg.Wait()
		done <- struct{}{}
	}()

	for {
		select {
		case <-done:
			return res, nil
		case r := <-rChan:
			//addr := <-addrChan
			//res[addr] = r
			res = append(res, r)
		default:
		}
	}
}

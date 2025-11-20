package rpc

import (
	"context"
	"dbm-services/mysql/db-remote-service/pkg/config"
	"sync"
)

func (c *MySQLRPCRequest) do() (res [][]MySQLRPCResponse, err error) {
	rChan := make(chan []MySQLRPCResponse)
	done := make(chan struct{})
	errChan := make(chan error)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	go func() {
		defer func() {
			close(rChan)
			close(done)
			close(errChan)
		}()
		var wg = &sync.WaitGroup{}
		wg.Add(len(c.Addresses))
		for _, addr := range c.Addresses {
			select {
			case <-ctx.Done():
				return
			default:
			}

			_ = config.GlobalLimiter.Wait(context.Background())
			go func(addr string) {
				defer wg.Done()
				ores, err := c.oneAddr(addr)
				if ores != nil {
					rChan <- ores
				}
				if err != nil {
					errChan <- err
				}
			}(addr)
		}
		wg.Wait()
		done <- struct{}{}
	}()

	for {
		select {
		case <-done:
			return res, nil
		case err := <-errChan:
			cancel()
			return res, err
		case r := <-rChan:
			res = append(res, r)
		default:
		}
	}
}

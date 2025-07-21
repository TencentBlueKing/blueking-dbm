package rpc

import (
	"context"
	"dbm-services/mysql/db-remote-service/pkg/config"
	"dbm-services/mysql/db-remote-service/pkg/v2/mysql/internal/impl"
	"sync"
)

func (c *MySQLRPCRequest) oneAddr(addr string) (res []MySQLRPCResponse, err error) {
	db, conn, connId, err := impl.Prepare(
		addr, config.RuntimeConfig.MySQLAdminUser, config.RuntimeConfig.MySQLAdminPassword,
		c.Timezone, c.Charset, c.ConnectTimeout,
	)
	// 这个必须放在错误处理前面
	// clean 函数内部自适应了
	defer func() {
		impl.Clean(db, conn, connId)
	}()
	if err != nil {
		return nil, err
	}

	rChan := make(chan MySQLRPCResponse)
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
		wg.Add(len(c.Cmds))
		for _, sql := range c.Cmds {
			select {
			case <-ctx.Done():
				return
			default:
			}

			_ = config.GlobalLimiter.Wait(context.Background())
			go func(sql string) {
				defer wg.Done()
				srs, n, err := impl.DoSQL(conn, sql, c.QueryTimeout)
				srp := MySQLRPCResponse{
					Cmd:          sql,
					Result:       srs,
					RowsAffected: n,
					Error:        "",
				}
				if err != nil {
					srp.Error = err.Error()
				}
				rChan <- srp
				if err != nil && !c.Force {
					errChan <- err
				}
			}(sql)
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
		case srp := <-rChan:
			res = append(res, srp)
		default:
		}
	}
}

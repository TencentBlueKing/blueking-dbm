package rpc

import (
	"context"
	"dbm-services/mysql/db-remote-service/pkg/config"
	"dbm-services/mysql/db-remote-service/pkg/v2/mysql/internal/impl"
)

func (c *MySQLRPCRequest) executeCmds(addr string) (res []MySQLCmdRPCResponse, err error) {
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

	for _, sql := range c.Cmds {
		_ = config.GlobalLimiter.Wait(context.Background())

		tableData, rowsAffected, err := impl.DoSQL(conn, sql, c.QueryTimeout)
		response := MySQLCmdRPCResponse{
			Cmd:          sql,
			Result:       tableData,
			RowsAffected: rowsAffected,
			Error:        "",
		}
		if err != nil {
			response.Error = err.Error()
		}
		res = append(res, response)

		// 非 force 模式下遇到错误立即返回
		if err != nil && !c.Force {
			return res, err
		}
	}

	return res, nil
}

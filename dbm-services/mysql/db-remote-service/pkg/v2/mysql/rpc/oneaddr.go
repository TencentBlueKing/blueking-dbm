package rpc

import (
	"context"
	"fmt"
	"log/slog"

	"dbm-services/mysql/db-remote-service/pkg/v2/mysql/internal/impl"
)

func (c *MySQLRPCRequest) executeCmds(ctx context.Context, addr, user, password string) (res []MySQLCmdRPCResponse, err error) {
	db, conn, connId, err := impl.Prepare(
		ctx,
		addr, user, password,
		c.Timezone, c.Charset, c.ConnectTimeout, c.PreHookCmds, c.SkipSetNames,
	)
	if err != nil {
		slog.Error("v2 mysql prepare connection failed",
			slog.String("addr", addr),
			slog.String("error", err.Error()),
		)
		return nil, err
	}
	defer func() {
		impl.Clean(db, conn, connId)
	}()

	for _, sql := range c.Cmds {
		// 客户端断开时立即放弃后续命令; 已执行的结果通过 res 返回
		if err := ctx.Err(); err != nil {
			return res, err
		}

		tableData, rowsAffected, err := impl.DoSQL(conn, sql, c.QueryTimeout)
		response := MySQLCmdRPCResponse{
			Cmd:          sql,
			Result:       tableData,
			RowsAffected: rowsAffected,
			Error:        "",
		}
		if err != nil {
			response.Error = err.Error()
			slog.Error("v2 mysql cmd execution failed",
				slog.String("addr", addr),
				slog.String("cmd", sql),
				slog.String("error", err.Error()),
			)
		}

		// 事务性致命错误 (deadlock / lock-wait-timeout / XA-deadlock):
		//   server 已经/即将自动回滚整个事务, 后续 SQL 即使发出去结果也不可信.
		//   即使 Force=true 也必须在这里中止, 并把"为何不能继续"明确告诉调用方.
		if err != nil {
			if fatal, me := impl.IsTransactionFatalError(err); fatal {
				slog.Error("v2 mysql transaction-fatal error, aborting batch",
					slog.String("addr", addr),
					slog.Uint64("errno", uint64(me.Number)),
					slog.String("message", me.Message),
				)
				response.Error = fmt.Sprintf(
					"transaction-fatal error (mysql errno=%d): %s; aborting remaining commands even though force=%v",
					me.Number, me.Message, c.Force,
				)
				res = append(res, response)
				return res, fmt.Errorf("transaction aborted by mysql errno=%d: %w", me.Number, err)
			}
		}

		res = append(res, response)

		// 非 force 模式下遇到错误立即返回
		if err != nil && !c.Force {
			return res, err
		}
	}

	return res, nil
}

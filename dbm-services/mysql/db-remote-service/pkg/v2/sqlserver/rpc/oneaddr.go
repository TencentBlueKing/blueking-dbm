package rpc

import (
	"context"
	"fmt"
	"log/slog"

	"dbm-services/mysql/db-remote-service/pkg/v2/sqlserver/internal/impl"
)

func (c *SqlserverRPCRequest) executeCmds(ctx context.Context, addr, user, password string) (res []SqlserverCmdRPCResponse, err error) {
	db, conn, err := impl.Prepare(ctx, addr, user, password, c.ConnectTimeout)
	if err != nil {
		slog.Error("v2 sqlserver prepare connection failed",
			slog.String("addr", addr),
			slog.String("error", err.Error()),
		)
		return nil, err
	}
	defer func() {
		impl.Clean(db, conn)
	}()

	for _, sql := range c.Cmds {
		if err := ctx.Err(); err != nil {
			return res, err
		}

		if !c.classifier.IsSupportedCommand(sql) {
			slog.Warn("v2 sqlserver unsupported command",
				slog.String("addr", addr),
				slog.String("cmd", sql),
			)
			response := SqlserverCmdRPCResponse{
				Cmd:   sql,
				Error: fmt.Sprintf("unsupported command: %s", sql),
			}
			res = append(res, response)
			if !c.Force {
				return res, fmt.Errorf("unsupported command: %s", sql)
			}
			continue
		}

		tableData, rowsAffected, err := impl.DoSQL(conn, sql, c.QueryTimeout, c.classifier)
		response := SqlserverCmdRPCResponse{
			Cmd:          sql,
			Result:       tableData,
			RowsAffected: rowsAffected,
			Error:        "",
		}
		if err != nil {
			response.Error = err.Error()
			slog.Error("v2 sqlserver cmd execution failed",
				slog.String("addr", addr),
				slog.String("cmd", sql),
				slog.String("error", err.Error()),
			)
		}

		res = append(res, response)

		if err != nil && !c.Force {
			return res, err
		}
	}

	return res, nil
}

package rpc

import (
	"context"
	"fmt"
	"log/slog"

	"dbm-services/mysql/db-remote-service/pkg/v2/proxy/internal/impl"
)

func (c *ProxyRPCRequest) executeCmds(ctx context.Context, addr, user, password string) (res []ProxyCmdRPCResponse, err error) {
	db, conn, err := impl.Prepare(ctx, addr, user, password, c.ConnectTimeout)
	if err != nil {
		slog.Error("v2 proxy prepare connection failed",
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

		if !impl.IsSupportedCommand(sql) {
			slog.Warn("v2 proxy unsupported command",
				slog.String("addr", addr),
				slog.String("cmd", sql),
			)
			response := ProxyCmdRPCResponse{
				Cmd:   sql,
				Error: fmt.Sprintf("unsupported command: %s", sql),
			}
			res = append(res, response)
			if !c.Force {
				return res, fmt.Errorf("unsupported command: %s", sql)
			}
			continue
		}

		tableData, rowsAffected, err := impl.DoSQL(conn, sql, c.QueryTimeout)
		response := ProxyCmdRPCResponse{
			Cmd:          sql,
			Result:       tableData,
			RowsAffected: rowsAffected,
			Error:        "",
		}
		if err != nil {
			response.Error = err.Error()
			slog.Error("v2 proxy cmd execution failed",
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

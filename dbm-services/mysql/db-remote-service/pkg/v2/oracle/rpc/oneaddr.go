package rpc

import (
	"context"
	"fmt"
	"log/slog"

	"dbm-services/mysql/db-remote-service/pkg/v2/oracle/internal/impl"
)

func (c *OracleRPCRequest) executeCmds(ctx context.Context, addr, user, password string) (res []OracleCmdRPCResponse, err error) {
	db, conn, err := impl.Prepare(ctx, addr, c.ServiceName, user, password, c.ConnectTimeout)
	if err != nil {
		slog.Error("v2 oracle prepare connection failed",
			slog.String("addr", addr),
			slog.String("service_name", c.ServiceName),
			slog.String("error", err.Error()),
		)
		return nil, err
	}
	defer func() {
		impl.Clean(db, conn)
	}()

	for _, rawCmd := range c.Cmds {
		if err := ctx.Err(); err != nil {
			return res, err
		}

		cmd := impl.NormalizeCommand(rawCmd)
		if !impl.IsReadOnlyQuery(cmd) {
			slog.Warn("v2 oracle unsupported command",
				slog.String("addr", addr),
				slog.String("cmd", rawCmd),
			)
			res = append(res, OracleCmdRPCResponse{
				Cmd:   rawCmd,
				Error: fmt.Sprintf("unsupported command (only read-only SELECT/WITH is allowed): %s", rawCmd),
			})
			if !c.Force {
				return res, fmt.Errorf("unsupported command: %s", rawCmd)
			}
			continue
		}

		tableData, err := impl.DoQuery(conn, cmd, c.QueryTimeout)
		response := OracleCmdRPCResponse{
			Cmd:    rawCmd,
			Result: tableData,
		}
		if err != nil {
			response.Error = err.Error()
			slog.Error("v2 oracle cmd execution failed",
				slog.String("addr", addr),
				slog.String("cmd", rawCmd),
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

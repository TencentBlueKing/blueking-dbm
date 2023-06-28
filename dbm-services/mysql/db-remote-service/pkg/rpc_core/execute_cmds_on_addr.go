package rpc_core

import (
	"context"
	"time"

	"github.com/pkg/errors"
	"golang.org/x/exp/slog"
)

func (c *RPCWrapper) executeOneAddr(address string) (res []cmdResult, err error) {
	db, err := c.MakeConnection(address, c.user, c.password, c.connectTimeout)

	if err != nil {
		slog.Error("make connection", err)
		return nil, err
	}

	defer func() {
		_ = db.Close()
	}()

	ctx, cancel := context.WithTimeout(context.Background(), time.Second*time.Duration(c.queryTimeout))
	defer cancel()

	conn, err := db.Connx(ctx)
	if err != nil {
		slog.Error("get conn from db", err)
		return nil, err
	}
	defer func() {
		_ = conn.Close()
	}()

	for idx, command := range c.commands {
		pc, err := c.ParseCommand(command)
		if err != nil {
			slog.Error("parse command", err)
			return nil, err
		}

		if c.IsQueryCommand(pc) {
			tableData, err := queryCmd(conn, command, ctx)
			if err != nil {
				slog.Error(
					"query command", err,
					slog.String("address", address), slog.String("command", command),
				)
				res = append(
					res, cmdResult{
						Cmd:          command,
						RowsAffected: 0,
						TableData:    nil,
						ErrorMsg:     err.Error(),
					},
				)
				if !c.force {
					return res, err
				}
				continue
			}
			res = append(
				res, cmdResult{
					Cmd:          command,
					TableData:    tableData,
					RowsAffected: 0,
					ErrorMsg:     "",
				},
			)
		} else if c.IsExecuteCommand(pc) {
			rowsAffected, err := executeCmd(conn, command, ctx)
			if err != nil {
				slog.Error(
					"execute command", err,
					slog.String("address", address), slog.String("command", command),
				)
				res = append(
					res, cmdResult{
						Cmd:          command,
						TableData:    nil,
						RowsAffected: 0,
						ErrorMsg:     err.Error(),
					},
				)
				if !c.force {
					return res, err
				}
				continue
			}
			res = append(
				res, cmdResult{
					Cmd:          command,
					TableData:    nil,
					RowsAffected: rowsAffected,
					ErrorMsg:     "",
				},
			)
		} else {
			err = errors.Errorf("commands[%d]: %s not support", idx, command)
			slog.Error("dispatch command", err)
			res = append(
				res, cmdResult{Cmd: command, TableData: nil, RowsAffected: 0, ErrorMsg: err.Error()},
			)
			if !c.force {
				return res, err
			}
		}
	}
	return
}

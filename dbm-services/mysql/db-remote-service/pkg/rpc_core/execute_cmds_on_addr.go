package rpc_core

import (
	"context"
	"log/slog"
	"strings"
	"time"

	"github.com/pkg/errors"
)

func (c *RPCWrapper) executeOneAddr(address string) (res []CmdResultType, err error) {
	db, err := c.MakeConnection(address, c.user, c.password, c.connectTimeout, c.timezone)

	if err != nil {
		c.logger.Error("make connection", slog.String("error", err.Error()))
		return nil, err
	}

	defer func() {
		_ = db.Close()
	}()

	ctx, cancel := context.WithTimeout(context.Background(), time.Second*time.Duration(c.queryTimeout))
	defer cancel()

	conn, err := db.Connx(ctx)
	if err != nil {
		c.logger.Error("get conn from db", slog.String("error", err.Error()))
		return nil, err
	}
	defer func() {
		_ = conn.Close()
	}()

	for idx, command := range c.commands {
		command = strings.TrimSpace(command)

		pc, err := c.ParseCommand(command)
		if err != nil {
			c.logger.Error("parse command", slog.String("error", err.Error()))
			return nil, err
		}

		if c.IsQueryCommand(pc) {
			c.logger.Info("query command", slog.String("command", pc.Command))
			tableData, err := queryCmd(c.logger, conn, command, time.Second*time.Duration(c.queryTimeout))
			if err != nil {
				c.logger.Error(
					"query command",
					slog.String("error", err.Error()),
					slog.String("address", address), slog.String("command", command),
				)
				res = append(
					res, CmdResultType{
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
				res, CmdResultType{
					Cmd:          command,
					TableData:    tableData,
					RowsAffected: 0,
					ErrorMsg:     "",
				},
			)
		} else if c.IsExecuteCommand(pc) {
			c.logger.Info("execute command", pc.Command)
			rowsAffected, err := executeCmd(c.logger, conn, command, time.Second*time.Duration(c.queryTimeout))
			if err != nil {
				c.logger.Error(
					"execute command",
					slog.String("error", err.Error()),
					slog.String("address", address), slog.String("command", command),
				)
				res = append(
					res, CmdResultType{
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
				res, CmdResultType{
					Cmd:          command,
					TableData:    nil,
					RowsAffected: rowsAffected,
					ErrorMsg:     "",
				},
			)
		} else {
			err = errors.Errorf("commands[%d]: %s not support", idx, command)
			c.logger.Error("dispatch command", slog.String("error", err.Error()))
			res = append(
				res, CmdResultType{Cmd: command, TableData: nil, RowsAffected: 0, ErrorMsg: err.Error()},
			)
			if !c.force {
				return res, err
			}
		}
	}
	return
}

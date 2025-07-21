package rpc_core

import (
	"context"
	"log/slog"
	"strings"
	"time"

	"github.com/pkg/errors"
)

func (c *RPCWrapper) executeOneAddr(address string) (res []CmdResultType, err error) {
	db, err := c.MakeConnection(address, c.user, c.password, c.connectTimeout, c.timezone, c.charset)

	if err != nil {
		c.logger.Error("make connection", slog.String("error", err.Error()))
		return nil, err
	}
	slog.Info("execute one addr connection make",
		slog.String("address", address),
		slog.Any("db", db),
		slog.Any("stat", db.Stats()),
	)
	//db.Close()

	defer func() {
		err := db.Close()
		if err != nil {
			slog.Error(
				"close db",
				slog.String("address", address),
				slog.Any("db", db),
				slog.String("error", err.Error()),
				slog.Any("stat", db.Stats()),
			)
		} else {
			slog.Info(
				"close db",
				slog.String("address", address),
				slog.Any("db", db),
				slog.Any("stat", db.Stats()),
			)
		}
		db.Stats()
	}()

	conn, err := db.Connx(context.Background()) //db.Connx(ctx)
	if err != nil {
		c.logger.Error("get conn from db", slog.String("error", err.Error()))
		return nil, err
	}
	defer func() {
		err := conn.Close()
		if err != nil {
			slog.Error(
				"close conn",
				slog.String("address", address),
				slog.Any("db", db),
				slog.String("error", err.Error()),
			)
		} else {
			slog.Info(
				"close conn",
				slog.String("address", address),
				slog.Any("db", db))
		}
	}()
	slog.Info("execute one addr get conn", slog.Any("stat", db.Stats()))

	var connId int64 = 0
	_ = conn.GetContext(context.Background(), &connId, `SELECT CONNECTION_ID()`)
	//if err != nil {
	//	c.logger.Error("get conn id", slog.String("error", err.Error()))
	//	return nil, err
	//}

	for idx, command := range c.commands {
		command = strings.TrimSpace(command)

		pc, err := c.ParseCommand(command)
		if err != nil {
			c.logger.Error("parse command", slog.String("error", err.Error()))
			return nil, err
		}

		if c.IsQueryCommand(pc) {
			c.logger.Info("query command", slog.String("command", pc.Command))
			tableData, err := queryCmd(c.logger, db, conn, connId, command, time.Second*time.Duration(c.queryTimeout))
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
			rowsAffected, err := executeCmd(c.logger, db, conn, connId, command, time.Second*time.Duration(c.queryTimeout))
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

package mysql_rpc

import (
	"context"
	"dbm-services/mysql/db-remote-service/pkg/config"
	"dbm-services/mysql/db-remote-service/pkg/parser"
	"fmt"
	"strings"
	"time"

	_ "github.com/go-sql-driver/mysql" // mysql
	"github.com/jmoiron/sqlx"
	"golang.org/x/exp/slices"
	"golang.org/x/exp/slog"
)

// MySQLRPCEmbed mysql 实现
type MySQLRPCEmbed struct {
}

// MakeConnection mysql 建立连接
func (c *MySQLRPCEmbed) MakeConnection(address string, user string, password string, timeout int) (*sqlx.DB, error) {
	ctx, cancel := context.WithTimeout(context.Background(), time.Second*time.Duration(timeout))
	defer cancel()

	db, err := sqlx.ConnectContext(
		ctx,
		"mysql",
		fmt.Sprintf(`%s:%s@tcp(%s)/`, user, password, address),
	)

	if err != nil {
		slog.Error("connect to mysql", err, slog.String("address", address))
		return nil, err
	}

	return db, nil
}

// ParseCommand mysql 解析命令
func (c *MySQLRPCEmbed) ParseCommand(command string) (*parser.ParseQueryBase, error) {
	/*
		由于 tmysqlparser 和中控兼容性不好, 不再使用 tmysqlparser 解析
		改回不那么精确的用 sql 首单词来区分下
	*/
	firstWord := strings.Split(command, " ")[0]
	slog.Info("parse command",
		slog.String("command", command),
		slog.String("first command word", firstWord))

	return &parser.ParseQueryBase{
		QueryId:   0,
		Command:   firstWord,
		ErrorCode: 0,
		ErrorMsg:  "",
	}, nil
}

// IsQueryCommand mysql 解析命令
func (c *MySQLRPCEmbed) IsQueryCommand(pc *parser.ParseQueryBase) bool {
	return slices.Index(genericDoQueryCommand, strings.ToLower(pc.Command)) >= 0
}

// IsExecuteCommand mysql 解析命令
func (c *MySQLRPCEmbed) IsExecuteCommand(pc *parser.ParseQueryBase) bool {
	return !c.IsQueryCommand(pc)
	// return slices.Index(doExecuteParseCommands, pc.Command) >= 0
}

// User mysql 用户
func (c *MySQLRPCEmbed) User() string {
	return config.RuntimeConfig.MySQLAdminUser
}

// Password mysql 密码
func (c *MySQLRPCEmbed) Password() string {
	return config.RuntimeConfig.MySQLAdminPassword
}

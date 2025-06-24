package sqlserver_rpc

import (
	"context"
	"dbm-services/mysql/db-remote-service/pkg/rpc_core"
	"fmt"
	"log/slog"
	"strings"
	"time"

	"dbm-services/mysql/db-remote-service/pkg/config"

	_ "github.com/denisenkom/go-mssqldb" // go-mssqldb TODO
	"github.com/jmoiron/sqlx"
)

// SqlserverRPCEmbed sqlserver 实现
type SqlserverRPCEmbed struct {
}

// InitQueryParseCommands 定义可以支持查询语句的结构
func (c *SqlserverRPCEmbed) InitQueryParseCommands() []string {
	return []string{
		"show",
		"select",
		"restore filelistonly",
		"restore headeronly",
	}
}

// InitQueryParseCommands 定义可以支持查询语句的结构
func (c *SqlserverRPCEmbed) InitExecuteParseCommands() []string {
	return []string{
		"use",
		"insert",
		"exec msdb.dbo.sp_update_job",
		"drop login",
		"alter login",
		"create login",
		"create user",
		"drop user",
		"alter authorization",
		"exec sp_addrolemember",
	}
}

// ParseCommand sqlserver 解析命令
func (c *SqlserverRPCEmbed) ParseCommand(command string) (*rpc_core.ParseQueryBase, error) {
	return &rpc_core.ParseQueryBase{
		QueryId:   0,
		Command:   command,
		ErrorCode: 0,
		ErrorMsg:  "",
	}, nil
}

// MakeConnection sqlserver 建立连接
func (c *SqlserverRPCEmbed) MakeConnection(address string, user string, password string, timeout int, timezone string, charset string) (*sqlx.DB, error) {
	host := strings.Split(address, ":")[0]
	port := strings.Split(address, ":")[1]
	ctx, cancel := context.WithTimeout(context.Background(), time.Second*time.Duration(timeout))
	defer cancel()

	db, err := sqlx.ConnectContext(
		ctx,
		"sqlserver",
		fmt.Sprintf(
			"server=%s;port=%s;user id=%s;password=%s;database=master;encrypt=disable;collation=utf8mb4_unicode_ci",
			host, port, user, password,
		),
	)

	if err != nil {
		slog.Error("connect to sqlserver",
			slog.String("error", err.Error()),
			slog.String("address", address),
		)
		return nil, err
	}

	return db, nil
}

// IsQueryCommand sqlserver 解析命令
func (c *SqlserverRPCEmbed) IsQueryCommand(pc *rpc_core.ParseQueryBase) bool {
	sqlserverQueryParseCommands := c.InitQueryParseCommands()
	for _, ele := range sqlserverQueryParseCommands {
		if strings.HasPrefix(strings.ToLower(pc.Command), ele) {
			return true
		}
	}

	return false
}

// IsExecuteCommand sqlserver 解析命令
func (c *SqlserverRPCEmbed) IsExecuteCommand(pc *rpc_core.ParseQueryBase) bool {
	sqlserverExecuteParseCommands := c.InitExecuteParseCommands()
	for _, ele := range sqlserverExecuteParseCommands {
		if strings.HasPrefix(strings.ToLower(pc.Command), ele) {
			return true
		}
	}

	return false
}

// User sqlserver 用户
func (c *SqlserverRPCEmbed) User() string {
	return config.RuntimeConfig.SqlserverAdminUser
}

// Password sqlserver 密码
func (c *SqlserverRPCEmbed) Password() string {
	return config.RuntimeConfig.SqlserverAdminPassword
}

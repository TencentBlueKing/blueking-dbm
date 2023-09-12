package mysql_rpc

import (
	"context"
	"fmt"
	"regexp"
	"strings"
	"time"

	"dbm-services/mysql/db-remote-service/pkg/config"
	"dbm-services/mysql/db-remote-service/pkg/parser"

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
	///*
	//	由于 tmysqlparser 和中控兼容性不好, 不再使用 tmysqlparser 解析
	//	改回不那么精确的用 sql 首单词来区分下
	//*/
	//pattern := regexp.MustCompile(`\s+`)
	//firstWord := pattern.Split(command, -1)[0]
	//slog.Info("parse command",
	//	slog.String("command", command),
	//	slog.String("first command word", firstWord))

	return &parser.ParseQueryBase{
		QueryId:   0,
		Command:   command, //strings.ToLower(firstWord),
		ErrorCode: 0,
		ErrorMsg:  "",
	}, nil
}

// IsQueryCommand mysql 解析命令
func (c *MySQLRPCEmbed) IsQueryCommand(pc *parser.ParseQueryBase) bool {
	return isQueryCommand(pc.Command)
}

// IsExecuteCommand mysql 解析命令
func (c *MySQLRPCEmbed) IsExecuteCommand(pc *parser.ParseQueryBase) bool {
	return !isQueryCommand(pc.Command)
}

// User mysql 用户
func (c *MySQLRPCEmbed) User() string {
	return config.RuntimeConfig.MySQLAdminUser
}

// Password mysql 密码
func (c *MySQLRPCEmbed) Password() string {
	return config.RuntimeConfig.MySQLAdminPassword
}

func isQueryCommand(command string) bool {
	pattern := regexp.MustCompile(`\s+`)
	firstWord := strings.ToLower(pattern.Split(command, -1)[0])
	if firstWord == "tdbctl" {
		return isTDBCTLQuery(command)
	} else {
		return slices.Index(genericDoQueryCommand, firstWord) >= 0
	}
}

func isTDBCTLQuery(command string) bool {
	splitPattern := regexp.MustCompile(`\s+`)
	secondWord := strings.ToLower(splitPattern.Split(command, -1)[1])
	switch secondWord {
	case "get", "show":
		return true
	case "connect":
		catchPattern := regexp.MustCompile(`(?mi)^.*execute\s+['"](.*)['"]$`)
		executeCmd := catchPattern.FindAllStringSubmatch(command, -1)[0][1]
		return isQueryCommand(executeCmd)
	default:
		return false
	}
}

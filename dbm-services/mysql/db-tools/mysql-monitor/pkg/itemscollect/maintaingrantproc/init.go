package maintaingrantproc

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/staticembed"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"
	"errors"
	"log/slog"
	"regexp"
	"strings"

	"github.com/go-sql-driver/mysql"
	"github.com/jmoiron/sqlx"
)

var name = "maintaingrantproc"

type Checker struct {
	db *sqlx.DB
}

func (c *Checker) Run() (msg string, err error) {
	grantProcContent, err := staticembed.ProcedureSQL.ReadFile(staticembed.GrantProcedureSQLFileName)
	if err != nil {
		return "", err
	}

	// 兼容
	sqls := []string{
		"set tc_admin = 0;",
		"create database if not exists infodba_schema",
	}
	for _, line := range strings.SplitAfterN(string(grantProcContent), "#", -1) {
		// 这是在补全, 所以过滤掉 drop 语句
		if !regexp.MustCompile(`^\\s*$`).MatchString(line) &&
			!strings.Contains(line, "DROP PROCEDURE IF EXISTS infodba_schema") &&
			!strings.Contains(line, "DROP TABLE IF EXISTS infodba_schema") {
			sqls = append(sqls, line)
		}
	}

	if len(sqls) < 2 {
		return "", nil // 忽略错误
	}

	// 不管错误
	for _, sql := range sqls {
		if regexp.MustCompile("^\\s*$").MatchString(sql) {
			continue
		}

		_, err := c.db.Exec(sql)
		if err == nil {
			slog.Debug(name, slog.String("sql", sql))
		} else {
			var me *mysql.MySQLError
			if errors.As(err, &me) {
				// 库存在, 存储过程存在, set tc_admin 的错误可以忽略
				if me.Number == 1007 || me.Number == 1304 || me.Number == 1193 {
					slog.Debug(name, slog.String("sql", sql))
				} else {
					slog.Error(name, slog.String("sql", sql), slog.String("error", err.Error()))
					return "", err // 其他 mysql 错误也要报告下
				}
			} else {
				slog.Error(name, slog.String("sql", sql), slog.String("error", err.Error()))
				return "", err // 非 mysql 错误就要报告下了
			}
		}
	}

	return "", nil
}

func (c *Checker) Name() string {
	return name
}

func NewChecker(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	return &Checker{
		db: cc.MySqlDB,
	}
}

func Register() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return name, NewChecker
}

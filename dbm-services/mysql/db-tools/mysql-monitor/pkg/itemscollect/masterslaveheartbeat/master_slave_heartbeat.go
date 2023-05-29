// Package masterslaveheartbeat 主备心跳
package masterslaveheartbeat

import (
	"context"
	"database/sql"
	"fmt"
	"log/slog"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/internal/cst"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
)

var (
	name       = "master-slave-heartbeat"
	checkTable = "master_slave_heartbeat"

	HeartBeatTable = fmt.Sprintf("%s.%s", cst.DBASchema, checkTable)
	DropTableSQL   = fmt.Sprintf("DROP TABLE IF EXISTS %s", HeartBeatTable)
	CreateTableSQL = fmt.Sprintf(`CREATE TABLE IF NOT EXISTS %s (
		master_server_id varchar(40) COMMENT 'server_id that run this update',
		slave_server_id  varchar(40) COMMENT 'slave server_id',
		master_time varchar(32) COMMENT 'the time on master',
		slave_time varchar(32) COMMENT 'the time on slave',
		delay_sec int DEFAULT 0 COMMENT 'the slave delay to master',
		PRIMARY KEY (master_server_id)
		) ENGINE=InnoDB`, HeartBeatTable,
	)
)

// Checker TODO
type Checker struct {
	db             *sqlx.DB
	heartBeatTable string
}

func (c *Checker) updateHeartbeat() error {
	ctx, cancel := context.WithTimeout(context.Background(), config.MonitorConfig.InteractTimeout)
	defer cancel()

	masterServerId := ""
	binlogFormatOld := ""
	err := c.db.QueryRow("select @@server_id, @@binlog_format").
		Scan(&masterServerId, &binlogFormatOld)
	if err != nil {
		slog.Error(
			"master-slave-heartbeat query server_id, binlog_format",
			slog.String("error", err.Error()),
		)
		return err
	}
	slog.Debug(
		"master-slave-heartbeat",
		slog.String("server_id", masterServerId),
		slog.String("binlog_format", binlogFormatOld),
	)

	// will set session variables, so get a connection from pool
	conn, err := c.db.DB.Conn(context.Background())
	if err != nil {
		slog.Error("master-slave-heartbeat get conn from db", slog.String("error", err.Error()))
		return err
	}
	defer func() {
		_ = conn.Close()
	}()

	if config.MonitorConfig.MachineType == "spider" {
		_, err := conn.ExecContext(ctx, "set tc_admin=0")
		if err != nil {
			slog.Error("master-slave-heartbeat", slog.String("error", err.Error()))
			return err
		}
	}

	txrrSQL := "SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ" // SET SESSION transaction_isolation = 'REPEATABLE-READ'
	binlogSQL := "SET SESSION binlog_format='STATEMENT'"
	insertSQL := fmt.Sprintf(
		`REPLACE INTO %s(master_server_id, slave_server_id, master_time, slave_time, delay_sec) 
VALUES('%s', @@server_id, now(), sysdate(), timestampdiff(SECOND, now(),sysdate()))`,
		c.heartBeatTable, masterServerId)

	if _, err = conn.ExecContext(ctx, txrrSQL); err != nil {
		err := errors.WithMessage(err, "update heartbeat need SET SESSION tx_isolation = 'REPEATABLE-READ'")
		slog.Error("master-slave-heartbeat", slog.String("error", err.Error()))
		return err
	}
	if _, err = conn.ExecContext(ctx, binlogSQL); err != nil {
		err := errors.WithMessage(err, "update heartbeat need binlog_format=STATEMENT")
		slog.Error("master-slave-heartbeat", slog.String("error", err.Error()))
		return err
	}

	res, err := conn.ExecContext(ctx, insertSQL)
	if err != nil {
		// 不再自动创建表
		// merr.Number == 1146 || merr.Number == 1054 , c.initTableHeartbeat()
		return err
	} else {
		if num, _ := res.RowsAffected(); num > 0 {
			slog.Debug("master-slave-heartbeat insert success")
		}
	}
	slog.Debug("master-slave-heartbeat update slave success")
	return nil
}

func (c *Checker) initTableHeartbeat() (sql.Result, error) {
	_, _ = c.db.Exec(DropTableSQL) // we do not care if table drop success, but care if table create success or not
	return c.db.Exec(CreateTableSQL)
}

// Run TODO
func (c *Checker) Run() (msg string, err error) {
	// check if dbbackup loadbackup running, skip this round
	err = c.updateHeartbeat()
	return "", err
}

// Name TODO
func (c *Checker) Name() string {
	return name
}

// New TODO
func New(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	if config.MonitorConfig.MachineType == "spider" && *config.MonitorConfig.Role == "spider_master" {
		return &Checker{
			db:             cc.CtlDB,
			heartBeatTable: HeartBeatTable,
		}
	} else {
		return &Checker{
			db:             cc.MySqlDB,
			heartBeatTable: HeartBeatTable,
		}
	}
}

// Register TODO
func Register() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return name, New
}

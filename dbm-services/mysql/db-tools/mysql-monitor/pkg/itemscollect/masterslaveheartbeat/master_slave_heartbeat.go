// Package masterslaveheartbeat 主备心跳
package masterslaveheartbeat

import (
	"context"
	"database/sql"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/utils"

	"fmt"
	"log/slog"
	"strconv"
	"strings"

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

type primaryDesc struct {
	ServerName   string `db:"SERVER_NAME"`
	Host         string `db:"HOST"`
	Port         uint32 `db:"PORT"`
	IsThisServer uint32 `db:"IS_THIS_SERVER"`
}

func (c *Checker) updateHeartbeat() error {
	masterServerId := ""
	binlogFormatOld := ""
	err := c.db.QueryRow("select @@server_id, @@binlog_format").
		Scan(&masterServerId, &binlogFormatOld)
	if err != nil {
		slog.Error(
			name,
			slog.String("error", err.Error()),
		)
		return err
	}
	slog.Info(
		name,
		slog.String("server_id", masterServerId),
		slog.String("binlog_format", binlogFormatOld),
	)

	// will set session variables, so get a connection from pool
	conn, err := c.db.DB.Conn(context.Background())
	if err != nil {
		slog.Error(name, slog.String("error", err.Error()))
		return err
	}
	defer func() {
		_ = conn.Close()
	}()

	if config.MonitorConfig.MachineType == "spider" {
		_, err := conn.ExecContext(context.Background(), "set tc_admin=0")
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

	if _, err = conn.ExecContext(context.Background(), txrrSQL); err != nil {
		err := errors.Wrapf(err, "update heartbeat need SET SESSION tx_isolation = 'REPEATABLE-READ'")
		slog.Error("master-slave-heartbeat", slog.String("error", err.Error()))
		return err
	}
	if _, err = conn.ExecContext(context.Background(), binlogSQL); err != nil {
		err := errors.WithMessage(err, "update heartbeat need binlog_format=STATEMENT")
		slog.Error("master-slave-heartbeat", slog.String("error", err.Error()))
		return err
	}

	res, err := conn.ExecContext(context.Background(), insertSQL)
	if err != nil {
		// 不再自动创建表
		// merr.Number == 1146 || merr.Number == 1054 , c.initTableHeartbeat()
		return err
	} else {
		if num, _ := res.RowsAffected(); num > 0 {
			slog.Info("master-slave-heartbeat insert success")
		}
	}
	slog.Info("master-slave-heartbeat update slave success")
	return nil
}

func (c *Checker) reportHeartbeatDelay() error {
	slaveStatus := make(map[string]interface{})
	rows, err := c.db.Queryx(`SHOW SLAVE STATUS`)
	if err != nil {
		slog.Error(name, slog.String("error", err.Error()))
		return err
	}
	defer func() {
		_ = rows.Close()
	}()

	for rows.Next() {
		err := rows.MapScan(slaveStatus)
		if err != nil {
			slog.Error(name, slog.String("error", err.Error()))
			return err
		}
		break
	}

	for k, v := range slaveStatus {
		if value, ok := v.([]byte); ok {
			slaveStatus[k] = strings.TrimSpace(string(value))
		}
	}

	masterServerId, err := strconv.ParseInt(slaveStatus["Master_Server_Id"].(string), 10, 64)
	if err != nil {
		slog.Error(name, slog.String("error", err.Error()))
		return err
	}

	slog.Info(name, slog.Any("master server id", masterServerId))

	var timeDelay int64
	err = c.db.QueryRowx(
		`select convert((unix_timestamp(now())-unix_timestamp(master_time)),UNSIGNED) as time_delay 
					from infodba_schema.master_slave_heartbeat 
					where master_server_id = ? and slave_server_id != master_server_id`,
		masterServerId,
	).Scan(&timeDelay)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			timeDelay = 99999999
		} else {
			return err
		}
	}

	slog.Info("master_slave_heartbeat delay", slog.Int64("delay", timeDelay))

	utils.SendMonitorMetrics(
		strings.Replace(name, "-", "_", -1),
		timeDelay,
		map[string]interface{}{
			"master-server_id": masterServerId,
			"master-host":      slaveStatus["Master_Host"],
			"master-port":      slaveStatus["Master_Port"],
		},
	)

	return nil
}

func (c *Checker) initTableHeartbeat() (sql.Result, error) {
	_, _ = c.db.Exec(DropTableSQL) // we do not care if table drop success, but care if table create success or not
	return c.db.Exec(CreateTableSQL)
}

// Run TODO
func (c *Checker) Run() (msg string, err error) {
	// check if dbbackup loadbackup running, skip this round
	slog.Info(name, slog.String("role", *config.MonitorConfig.Role))
	slog.Info(name, slog.String("machine type", config.MonitorConfig.MachineType))
	if config.MonitorConfig.MachineType == "spider" {
		return c.heartBeatOnSpider()
	} else {
		return c.heartBeatOnStorage()

	}
}

func (c *Checker) heartBeatOnSpider() (msg string, err error) {
	if *config.MonitorConfig.Role != "spider_master" {
		return "", nil
	}

	res := primaryDesc{}
	err = c.db.QueryRowx(`tdbctl get primary`).StructScan(&res)
	if err != nil {
		slog.Error(name, slog.String("err", err.Error()))
		return "", err
	}
	slog.Info(name, slog.Bool("is primary", res.IsThisServer == 1))
	if res.IsThisServer == 1 {
		err = c.updateHeartbeat()
	} else {
		err = c.reportHeartbeatDelay()
	}

	return "", err
}

func (c *Checker) heartBeatOnStorage() (msg string, err error) {
	slog.Info(name, slog.String("machine type", config.MonitorConfig.MachineType))
	switch *config.MonitorConfig.Role {
	case "master":
		err = c.updateHeartbeat()
		if err != nil {
			return "", err
		}
	case "slave":
		err = c.reportHeartbeatDelay()
		if err != nil {
			return "", err
		}
	case "repeater":
		err = c.updateHeartbeat()
		if err != nil {
			return "", err
		}
		err = c.reportHeartbeatDelay()
		if err != nil {
			return "", err
		}
	default:
		return "", errors.Errorf("unkown role: %s", *config.MonitorConfig.Role)
	}
	return "", nil
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

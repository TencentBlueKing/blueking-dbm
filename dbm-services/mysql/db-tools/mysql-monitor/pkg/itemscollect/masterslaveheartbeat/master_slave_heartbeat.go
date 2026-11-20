// Package masterslaveheartbeat 主备心跳
package masterslaveheartbeat

import (
	"context"
	"database/sql"

	//"errors"
	"fmt"
	"log/slog"
	"strconv"
	"strings"
	"time"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/utils"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/internal/cst"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"

	"github.com/go-sql-driver/mysql"
	"github.com/pkg/errors"
)

var (
	name       = "master-slave-heartbeat"
	checkTable = "master_slave_heartbeat"

	HeartBeatTable = fmt.Sprintf("%s.%s", cst.DBASchema, checkTable)
	DropTableSQL   = fmt.Sprintf("DROP TABLE IF EXISTS %s", HeartBeatTable)
	CreateTableSQL = fmt.Sprintf(
		`CREATE TABLE IF NOT EXISTS %s (
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
	db             *pkg.MySQLMonitorDBH
	heartBeatTable string
}

type primaryDesc struct {
	ServerName   string `db:"SERVER_NAME"`
	Host         string `db:"HOST"`
	Port         uint32 `db:"PORT"`
	IsThisServer uint32 `db:"IS_THIS_SERVER"`
}

func (c *Checker) updateHeartbeat(ctx context.Context) error {
	masterServerId := ""
	binlogFormatOld := ""
	err := c.db.QueryRowContext(ctx, "select @@server_id, @@binlog_format").
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
	conn, err := c.db.DB.Conn(ctx)
	if err != nil {
		slog.Error(name, slog.String("error", err.Error()))
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
		c.heartBeatTable, masterServerId,
	)

	if _, err = conn.ExecContext(ctx, txrrSQL); err != nil {
		err := errors.Wrapf(err, "update heartbeat need SET SESSION tx_isolation = 'REPEATABLE-READ'")
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
		slog.Error(name, slog.String("error", err.Error()))
		return err
	}

	if num, _ := res.RowsAffected(); num > 0 {
		slog.Info("master-slave-heartbeat insert success")
	}
	slog.Info("master-slave-heartbeat update slave success")
	return nil
}

func (c *Checker) reportHeartbeatDelay(ctx context.Context) (*pkg.MySQLMonitorDBH, string, error) {
	slaveStatus := make(map[string]interface{})
	rows, err := c.db.QueryxContext(ctx, `SHOW SLAVE STATUS`)
	if err != nil {
		slog.Error(name, slog.String("error", err.Error()))
		return c.db, "", err
	}
	defer func() {
		_ = rows.Close()
	}()

	for rows.Next() {
		err := rows.MapScan(slaveStatus)
		if err != nil {
			slog.Error(name, slog.String("error", err.Error()))
			return c.db, "", err
		}
		break
	}

	for k, v := range slaveStatus {
		if value, ok := v.([]byte); ok {
			slaveStatus[k] = strings.TrimSpace(string(value))
		}
	}
	if len(slaveStatus) == 0 {
		slog.Error(name, slog.String("error", "slave status is empty"))
		return c.db, "slave status is empty", nil
	}
	masterServerId, err := strconv.ParseInt(slaveStatus["Master_Server_Id"].(string), 10, 64)
	if err != nil {
		slog.Error(name, slog.String("error", err.Error()))
		return c.db, err.Error(), nil
	}

	slog.Info(name, slog.Any("master server id", masterServerId))

	var timeDelay int64

	var _useless interface{}
	var uptime int64
	err = c.db.QueryRowx(
		`show global status where Variable_name = 'Uptime';`,
	).Scan(&_useless, &uptime)
	if err != nil {
		slog.Error(name, slog.String("error", err.Error()))
		return c.db, err.Error(), nil
	}
	slog.Info(name, slog.Int64("uptime", uptime))

	if uptime < 3600 {
		timeDelay = 0
		slog.Info(
			name,
			slog.String("uptime", fmt.Sprintf("%v", uptime)),
			slog.String("force report time_delay", fmt.Sprintf("%v", timeDelay)),
		)
	} else {
		// GREATEST(...,0) on SIGNED avoids negative-to-UNSIGNED wraparound on clock skew (master_time ahead of NOW()).
		err = c.db.QueryRowx(
			`select GREATEST(CAST(UNIX_TIMESTAMP(NOW())-UNIX_TIMESTAMP(master_time) AS SIGNED), 0) as time_delay 
					from infodba_schema.master_slave_heartbeat 
					where master_server_id = ? and slave_server_id != master_server_id`,
			masterServerId,
		).Scan(&timeDelay)
		if err != nil {
			if errors.Is(err, sql.ErrNoRows) {
				timeDelay = 99999999
			} else {
				var me *mysql.MySQLError
				ok := errors.As(err, &me)
				if ok && me.Number == 1461 { // max_prepared_stmt_count too small
					slog.Info(
						name, slog.String("sql", "set global max_prepared_stmt_count=@@max_prepared_stmt_count+100"),
					)
					//_, _ = c.db.Exec("set global max_prepared_stmt_count=@@max_prepared_stmt_count+100")
				} else {
					slog.Error(name, slog.String("error", err.Error()))
					return c.db, err.Error(), nil
				}
			}
		}

		slog.Info("master_slave_heartbeat delay", slog.Int64("delay", timeDelay))
	}

	utils.SendMonitorMetrics(
		strings.Replace(name, "-", "_", -1),
		timeDelay,
		map[string]interface{}{
			"master-server_id": masterServerId,
			"master-host":      slaveStatus["Master_Host"],
			"master-port":      slaveStatus["Master_Port"],
			"instance_host":    c.db.Host,
			"instance_port":    c.db.Port,
		},
	)

	return nil, "", nil
}

func (c *Checker) initTableHeartbeat() (sql.Result, error) {
	_, _ = c.db.Exec(DropTableSQL) // we do not care if table drop success, but care if table create success or not
	return c.db.Exec(CreateTableSQL)
}

// Run TODO
func (c *Checker) Run() (warnDB *pkg.MySQLMonitorDBH, msg string, err error) {
	// check if dbbackup load backup running, skip this round
	slog.Info(name, slog.String("role", *config.MonitorConfig.Role))
	slog.Info(name, slog.String("machine type", config.MonitorConfig.MachineType))
	if config.MonitorConfig.MachineType == "spider" {
		return c.heartBeatOnSpider()
	}

	return c.heartBeatOnStorage()
}

func (c *Checker) heartBeatOnSpider() (warnDB *pkg.MySQLMonitorDBH, msg string, err error) {
	if *config.MonitorConfig.Role != "spider_master" {
		return nil, "", nil
	}

	// 设大，暂不启用 context timeout，可能会影响 db hang 告警（当然，如果真的有 db hang了也有其他 collect会触发）
	ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
	defer cancel()

	res := primaryDesc{}
	err = c.db.QueryRowxContext(ctx, `tdbctl get primary`).StructScan(&res)
	if err != nil {
		slog.Error(name, slog.String("err", err.Error()))
		return c.db, err.Error(), nil // 获取 primary 失败转成明确的告警
	}
	slog.Info(name, slog.Bool("is primary", res.IsThisServer == 1))
	if res.IsThisServer == 1 {
		err = c.updateHeartbeat(ctx)
	} else {
		warnDB, msg, err = c.reportHeartbeatDelay(ctx)
	}

	return warnDB, msg, err
}

func (c *Checker) heartBeatOnStorage() (warnDB *pkg.MySQLMonitorDBH, msg string, err error) {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	slog.Info(name, slog.String("machine type", config.MonitorConfig.MachineType))
	switch *config.MonitorConfig.Role {
	case "master":
		err = c.updateHeartbeat(ctx)
		if err != nil {
			return c.db, err.Error(), nil
		}
	case "slave":
		return c.reportHeartbeatDelay(ctx)

	case "repeater":
		err = c.updateHeartbeat(ctx)
		if err != nil {
			return c.db, err.Error(), nil
		}
		return c.reportHeartbeatDelay(ctx)

	default:
		return c.db, fmt.Sprintf("unknown role: %s", *config.MonitorConfig.Role), nil
	}
	return nil, "", nil
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
	}

	return &Checker{
		db:             cc.MySqlDB,
		heartBeatTable: HeartBeatTable,
	}
}

// Register TODO
func Register() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return name, New
}

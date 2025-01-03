package dbhaheartbeat

import (
	"database/sql"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/utils"
	"fmt"
	"log/slog"
	"strings"
	"time"

	"github.com/jmoiron/sqlx"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"
)

/*
1. 超过 2min 没心跳就产生 event
2. 监控平台上连续重复 5 次再告警
这个监控重要, 但是不需要过于敏感
*/

var name = "dbha-heartbeat"
var beatName string

type Checker struct {
	db *sqlx.DB
}

func init() {
	beatName = strings.Replace(name, "-", "_", -1)
}

func (c *Checker) Run() (msg string, err error) {
	var res sql.NullTime
	err = c.db.QueryRowx(
		`SELECT MAX(ck_time) FROM infodba_schema.check_heartbeat WHERE uid = @@server_id`,
	).Scan(&res)

	if v, err := res.Value(); err != nil {
		return "", err
	} else {
		if v == nil {
			return fmt.Sprintf("empty dbha heartbeat ck_time"), nil
		}

		slog.Info("dbha-heartbeat",
			slog.Time("latest heartbeat", res.Time))

		//// 最近2分钟没有新的心跳
		//if res.Time.Add(2 * time.Minute).Before(time.Now()) {
		//	return fmt.Sprintf("last heartbeat time: %s", res.Time.In(time.Local)), nil
		//}

		// 2 分钟内有探测则发送保持心跳
		if res.Time.Add(2 * time.Minute).After(time.Now()) {
			utils.SendMonitorMetrics(beatName, 1, nil)
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

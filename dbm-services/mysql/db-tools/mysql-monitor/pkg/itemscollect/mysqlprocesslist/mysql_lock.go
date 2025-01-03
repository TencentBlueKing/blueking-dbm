package mysqlprocesslist

import (
	"log/slog"
	"strings"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/internal/cst"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/utils"

	"github.com/dlclark/regexp2"
)

/*
+------+------+-------------------+------+---------+------+----------+------------------+
|Id 0  |User 1| Host 2            | db 3 |Command 4|Time 5| State 6  | Info 7           |
+------+------+-------------------+------+---------+------+----------+------------------+
| 4157 | root | 127.0.0.1:58872 | NULL | Query   |    0 | starting | show processlist |
+------+------+-------------------+------+---------+------+----------+------------------+
perl 版监控的一些逻辑
1. 会抓取 FLUSH TABLE WITH READ LOCK 操作然后干掉, 不应该这样
2. Status 包含 lock 时, 忽略掉 Status == 'System lock' && Command =~ 'LOAD DATA' | '^BINLOG'
3. 接上面, 夜间锁表评估更加宽容, Time < 300 不告警 --- 废弃策略

1. 锁表信息统一改为 锁状态>5s 触发
2. 上报自定义指标
3. 由监控平台策略决定是否需要发告警
4. db, user 等信息全部加入到维度里面, 方便做告警策略
*/

var lockThreshold int64
var nameMySQLLockMetric string

func init() {
	lockThreshold = 5
	nameMySQLLockMetric = strings.Replace(nameMySQLLock, "-", "_", -1)
}

func mysqlLock() (string, error) {
	processList, err := loadSnapShot()
	if err != nil {
		return "", err
	}

	for _, p := range processList {
		pstr, err := p.JsonString()
		if err != nil {
			return "", err
		}

		slog.Debug("mysql lock check process", slog.Any("process", pstr))

		if strings.ToLower(p.User.String) == cst.SystemUser {
			continue
		}

		hasLongWait, err := hasLongWaitingForTableFlush(p)
		if err != nil {
			return "", err
		}
		if hasLongWait {
			utils.SendMonitorMetrics(nameMySQLLockMetric, p.Time.Int64, map[string]interface{}{
				"lock_user":    p.User.String,
				"lock_id":      p.Id.Int64,
				"lock_db":      p.Db.String,
				"lock_command": p.Command.String,
				"lock_info":    p.Info.String,
				"lock_host":    p.Host.String,
				"lock_state":   p.State.String,
			})
			slog.Debug("mysql lock check process", slog.Bool("has long wait for table flush", hasLongWait))
			continue
		}

		hasNormal, err := hasNormalLock(p)
		if err != nil {
			return "", err
		}
		if hasNormal {
			utils.SendMonitorMetrics(nameMySQLLockMetric, p.Time.Int64, map[string]interface{}{
				"lock_user":    p.User.String,
				"lock_id":      p.Id.Int64,
				"lock_db":      p.Db.String,
				"lock_command": p.Command.String,
				"lock_info":    p.Info.String,
				"lock_host":    p.Host.String,
				"lock_state":   p.State.String,
			})
			slog.Debug("mysql lock check process", slog.Bool("has normal lock", hasNormal))
			continue
		}
	}
	return "", nil
}

func hasLongWaitingForTableFlush(p *mysqlProcess) (bool, error) {
	return p.Time.Int64 > lockThreshold /*60*/ &&
			strings.Contains(strings.ToLower(p.State.String), "waiting for table flush"),
		nil
}

func hasNormalLock(p *mysqlProcess) (bool, error) {
	reLockPattern := regexp2.MustCompile(`lock`, regexp2.IgnoreCase)
	match, err := reLockPattern.MatchString(p.State.String)
	if err != nil {
		slog.Error("apply lock pattern", slog.String("error", err.Error()))
		return false, err
	}
	if !match {
		return false, nil
	}

	reSystemLockPattern := regexp2.MustCompile(`system lock`, regexp2.IgnoreCase)
	match, err = reSystemLockPattern.MatchString(p.State.String)
	if err != nil {
		slog.Error("apply system lock pattern", slog.String("error", err.Error()))
		return false, err
	}

	slog.Debug("check system lock", slog.Bool("match status lock", match))
	if match {
		return false, nil
	}

	reExcludeSql := regexp2.MustCompile(`(?=(?:(^binlog|load data)))`, regexp2.IgnoreCase)
	match, err = reExcludeSql.MatchString(p.Info.String)
	if err != nil {
		slog.Error("apply exclude commands pattern", slog.String("error", err.Error()))
		return false, err
	}

	slog.Debug("check normal lock", slog.Bool("exclude command binlog|load data", match))
	if match {
		return false, nil
	}

	return p.Time.Int64 > lockThreshold, nil
}

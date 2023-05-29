package mysql_processlist

import (
	"strings"
	"time"

	"github.com/dlclark/regexp2"
	"golang.org/x/exp/slog"
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
3. 接上面, 夜间锁表评估更加宽容, Time < 300 不告警
*/

func mysqlLock() (string, error) {
	processList, err := loadSnapShot()
	if err != nil {
		return "", err
	}

	var locks []string
	for _, p := range processList {
		pstr, err := p.JsonString()
		if err != nil {
			return "", err
		}

		slog.Debug("mysql lock check process", slog.Any("process", pstr))

		if strings.ToLower(p.User.String) == "system user" {
			continue
		}

		hasLongWait, err := hasLongWaitingForTableFlush(p)
		if err != nil {
			return "", err
		}
		slog.Debug("mysql lock check process", slog.Bool("has long wait for table flush", hasLongWait))

		hasNormal, err := hasNormalLock(p)
		if err != nil {
			return "", err
		}
		slog.Debug("mysql lock check process", slog.Bool("has normal lock", hasNormal))

		if hasLongWait || hasNormal {
			locks = append(locks, pstr)
		}
	}
	return strings.Join(locks, ","), nil
}

func hasLongWaitingForTableFlush(p *mysqlProcess) (bool, error) {
	return p.Time.Int64 > 60 &&
			strings.Contains(strings.ToLower(p.State.String), "waiting for table flush"),
		nil
}

func hasNormalLock(p *mysqlProcess) (bool, error) {
	reLockPattern := regexp2.MustCompile(`lock`, regexp2.IgnoreCase)
	match, err := reLockPattern.MatchString(p.State.String)
	if err != nil {
		slog.Error("apply lock pattern", err)
		return false, err
	}
	if !match {
		return false, nil
	}

	reSystemLockPattern := regexp2.MustCompile(`system lock`, regexp2.IgnoreCase)
	match, err = reSystemLockPattern.MatchString(p.State.String)
	if err != nil {
		slog.Error("apply system lock pattern", err)
		return false, err
	}

	slog.Debug("check normal lock", slog.Bool("match status lock", match))
	if match {
		return false, nil
	}

	// reExcludeCommands := regexp2.MustCompile(`^(?!.*(?:(^binlog|load data)))`, regexp2.IgnoreCase)
	reExcludeSql := regexp2.MustCompile(`(?=(?:(^binlog|load data)))`, regexp2.IgnoreCase)
	match, err = reExcludeSql.MatchString(p.Info.String)
	if err != nil {
		slog.Error("apply exclude commands pattern", err)
		return false, err
	}

	slog.Debug("check normal lock", slog.Bool("exclude command binlog|load data", match))
	if match {
		return false, nil
	}

	now := time.Now()
	if now.Hour() >= 21 && now.Hour() < 9 {
		if p.Time.Int64 > 300 {
			return true, nil
		}
	} else {
		if p.Time.Int64 > 5 {
			return true, nil
		}
	}
	return false, nil
}

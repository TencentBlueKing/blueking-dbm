package scenesnapshot

/*
按需采集: scene-snapshot 一般是 @every 1m 跑一次, 每轮都落快照比较浪费磁盘.
开启 options.snapshot_on_demand 后, 只在实例看起来有异常时才采集, 满足任一条件即采集:

	存在 Time 大于 snapshot_long_query_time 秒的查询, 默认 30
	Threads_running 超过 snapshot_threads_running, 默认 50
	可用连接数少于 snapshot_free_connections, 默认 10

snapshot_long_query_exclude_user 可以排除掉一些跑很久属于正常的 user, 比如备份、校验.
*/

import (
	"log/slog"
	"strings"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg"
)

// 按需采集条件的默认阈值
const (
	defaultSnapshotKeepHours             = 48
	defaultSnapshotLongQueryTime   int64 = 30
	defaultSnapshotThreadsRunning        = 50
	defaultSnapshotFreeConnections       = 10
)

// initSnapshotOptions 阈值没配置时用默认值
func (c *Checker) initSnapshotOptions() {
	// 保留天数和按需采集无关, 无条件填充
	if c.SnapshotKeepHours <= 0 {
		c.SnapshotKeepHours = defaultSnapshotKeepHours
	}

	if !c.SnapshotOnDemand {
		return
	}

	if c.SnapshotLongQueryTime <= 0 {
		c.SnapshotLongQueryTime = defaultSnapshotLongQueryTime
	}
	if c.SnapshotThreadsRunning <= 0 {
		c.SnapshotThreadsRunning = defaultSnapshotThreadsRunning
	}
	if c.SnapshotFreeConnections <= 0 {
		c.SnapshotFreeConnections = defaultSnapshotFreeConnections
	}
}

// needSnapshotToDisk 是否需要采集现场, 没开按需采集就每轮都采集
func (c *Checker) needSnapshotToDisk(processList []*mysqlProcess) bool {
	if !c.SnapshotOnDemand {
		return true
	}

	if p := c.findLongQuery(processList); p != nil {
		slog.Info(
			name, slog.String("msg", "snapshot on demand: long query found"),
			slog.Int64("id", p.Id.Int64), slog.Int64("time", p.Time.Int64),
			slog.String("db", p.Db.String), slog.String("info", p.Info.String),
		)
		return true
	}

	threadsRunning, err := queryThreadsRunning(c.db)
	if err != nil {
		// 拿不到状态值时按需要采集处理, 避免漏现场
		return true
	}
	if threadsRunning > c.SnapshotThreadsRunning {
		slog.Info(
			name, slog.String("msg", "snapshot on demand: threads running exceed"),
			slog.Int("threads_running", threadsRunning),
			slog.Int("snapshot_threads_running", c.SnapshotThreadsRunning),
		)
		return true
	}

	// 连接快用满时也要留现场, 否则登不上去就什么都看不到了
	// processlist 就是当前的全部连接, 不用再查一次 Threads_connected
	maxConnections, err := queryMaxConnections(c.db)
	if err != nil {
		// c.db 已经是有效连接了，这里失败是未知错误，不快照了
		return false
	}
	if freeConnections := maxConnections - len(processList); freeConnections < c.SnapshotFreeConnections {
		slog.Info(
			name, slog.String("msg", "snapshot on demand: free connections not enough"),
			slog.Int("free_connections", freeConnections),
			slog.Int("max_connections", maxConnections),
			slog.Int("threads_connected", len(processList)),
			slog.Int("snapshot_free_connections", c.SnapshotFreeConnections),
		)
		return true
	}

	return false
}

// findLongQuery 找出执行时间超过阈值的查询
// Sleep 是空闲连接, Time 再大也不算异常, 不参与判断
// 主要是想解决一种，慢查询还未记录 slowlog，但 db 崩掉的连sql 都抓不到的情况
func (c *Checker) findLongQuery(processList []*mysqlProcess) *mysqlProcess {
	for _, p := range processList {
		if skipProcess(p, 0) {
			continue
		}
		if strings.EqualFold(strings.TrimSpace(p.Command.String), "sleep") {
			continue
		}
		if c.isLongQueryExcludeUser(p.User.String) {
			continue
		}
		if p.Time.Int64 > c.SnapshotLongQueryTime {
			return p
		}
	}

	return nil
}

// isLongQueryExcludeUser 判断长查询时是否忽略这个 user
func (c *Checker) isLongQueryExcludeUser(user string) bool {
	user = strings.TrimSpace(user)
	for _, ele := range c.SnapshotLongQueryExcludeUser {
		if strings.EqualFold(user, strings.TrimSpace(ele)) {
			return true
		}
	}

	return false
}

func queryThreadsRunning(db *pkg.MySQLMonitorDBH) (int, error) {
	var varName string
	var threadsRunning int

	err := db.QueryRowx(
		`SHOW GLOBAL STATUS LIKE 'Threads_running'`,
	).Scan(&varName, &threadsRunning)
	if err != nil {
		slog.Error(name, slog.String("msg", "query threads running"), slog.String("error", err.Error()))
		return 0, err
	}

	return threadsRunning, nil
}

func queryMaxConnections(db *pkg.MySQLMonitorDBH) (int, error) {
	var varName string
	var maxConnections int

	err := db.QueryRowx(
		`SHOW GLOBAL VARIABLES LIKE 'max_connections'`,
	).Scan(&varName, &maxConnections)
	if err != nil {
		slog.Error(name, slog.String("msg", "query max connections"), slog.String("error", err.Error()))
		return 0, err
	}

	return maxConnections, nil
}

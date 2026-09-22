package scenesnapshot

/*
现场快照按 天/实例 归档到 scenes 目录, 每轮采集一个 gz 文件

└> ls scenes/processlist.20000.20231130/
20231130121345.gz  20231130121547.gz  20231130121932.gz

└> zcat scenes/processlist.20000.20231130/20231130121932.gz
+-------+------+-------------------+----+---------+------+-----------+--------------------------------+
|  ID   | USER |       HOST        | DB | COMMAND | TIME |   STATE   |              INFO              |
+-------+------+-------------------+----+---------+------+-----------+--------------------------------+
| 74590 | root | 127.0.0.1:54219 |    | Query   |    0 | executing | SELECT ID, USER,               |
|       |      |                   |    |         |      |           | HOST, DB, COMMAND,             |
|       |      |                   |    |         |      |           | TIME, STATE, INFO FROM         |
|       |      |                   |    |         |      |           | INFORMATION_SCHEMA.PROCESSLIST |
+-------+------+-------------------+----+---------+------+-----------+--------------------------------+
| 74572 | root | 127.0.0.2:62014 |    | Sleep   | 2865 |           |                                |
+-------+------+-------------------+----+---------+------+-----------+--------------------------------+
*/

import (
	"log/slog"
	"os"
	"path/filepath"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/itemscollect/scenesnapshot/internal/archivescenes"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"

	"github.com/go-viper/mapstructure/v2"
)

var executable string
var sceneBase string

var name = "scene-snapshot"

func init() {
	executable, _ = os.Executable()
	sceneBase = filepath.Join(
		filepath.Dir(executable),
		"scenes",
	)

	_ = os.MkdirAll(sceneBase, 0755)
}

type Checker struct {
	// SnapshotKeepDays 快照保留天数, 不配置用默认值 2
	SnapshotKeepDays int `mapstructure:"snapshot_keep_days"`
	// SnapshotOnDemand 是否按需采集快照, 默认 false 即每轮都采集, 详见 on_demand.go
	SnapshotOnDemand bool `mapstructure:"snapshot_on_demand"`
	// SnapshotLongQueryTime 按需采集条件: 存在 Time 大于 N 秒的查询, 不配置用默认值 30
	SnapshotLongQueryTime int64 `mapstructure:"snapshot_long_query_time"`
	// SnapshotLongQueryExcludeUser 判断长查询时忽略这些 user, 精确匹配, 忽略大小写
	// 比如备份、校验之类的后台任务, 跑很久是正常的
	SnapshotLongQueryExcludeUser []string `mapstructure:"snapshot_long_query_exclude_user"`
	// SnapshotThreadsRunning 按需采集条件: Threads_running 超过 N, 不配置用默认值 50
	SnapshotThreadsRunning int `mapstructure:"snapshot_threads_running"`
	// SnapshotFreeConnections 按需采集条件: max_connections 剩余可用连接少于 N, 不配置用默认值 10
	SnapshotFreeConnections int `mapstructure:"snapshot_free_connections"`

	// QueryKillEnable 是否开启 query kill
	QueryKillEnable bool `mapstructure:"query_kill_enable"`
	// QueryKillMaxPerRound 全局上限, 单轮所有规则合计最多处理 N 个连接, 0 不限制
	QueryKillMaxPerRound int `mapstructure:"query_kill_max_per_round"`
	// QueryKillRules query kill 规则, 详见 query_kill.go
	QueryKillRules []*QueryKillRuleDef `mapstructure:"query_kill_rules"`

	db             *pkg.MySQLMonitorDBH
	optionMap      monitoriteminterface.ItemOptions
	queryKillRules []*QueryKillRuleDef // 校验通过的规则
}

func (c *Checker) Run() (warnDB *pkg.MySQLMonitorDBH, msg string, err error) {
	processList, err := queryProcesslist(c.db)
	if err != nil {
		return nil, "", err
	}

	if c.needSnapshotToDisk(processList) {
		// 有新快照产生才需要清理过期的
		c.cleanOldScenes()

		err = processListScene(processList)
		if err != nil {
			return nil, "", err
		}

		err = engineInnodbStatusScene(c.db)
		if err != nil {
			return nil, "", err
		}
	}

	// 快照做完再判断是否需要 kill query
	c.queryKillProcesslist(processList)

	return nil, "", nil
}

// cleanOldScenes 删除过期的快照目录
// 清理失败不影响采集, 只记录日志
func (c *Checker) cleanOldScenes() {
	for _, sceneName := range []string{processListName, engineInnodbStatusName} {
		if err := archivescenes.DeleteOld(sceneName, sceneBase, c.SnapshotKeepDays); err != nil {
			slog.Warn(
				name, slog.String("msg", "delete old scenes"),
				slog.String("scene", sceneName), slog.String("error", err.Error()),
			)
		}
	}
}

func (c *Checker) Name() string {
	return name
}

func NewChecker(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	opts := cc.GetCustomOptions(name) // ItemOptions is map[string]interface{}

	var itemObj Checker
	if err := mapstructure.Decode(opts, &itemObj); err != nil { // map interface to struct
		slog.Error(
			name,
			slog.String("msg", "custom options format error"), slog.Any("error", err),
		)
		panic(err)
	}
	itemObj.db = cc.MySqlDB
	itemObj.optionMap = opts

	itemObj.initSnapshotOptions()
	itemObj.initQueryKillRules()

	return &itemObj
}

func Register() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return name, NewChecker
}

// Package ibdstatistic ibd大小统计
package ibdstatistic

import (
	"database/sql"
	"log/slog"
	"regexp"
	"sort"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/internal/cst"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"

	"github.com/jmoiron/sqlx"
	"github.com/mitchellh/mapstructure"
	"github.com/pkg/errors"
)

/*
以扫描磁盘文件的方式统计 innodb 库表大小
本来计划同时实现 .frm 和 .par 文件丢失的告警
但是在 8.0 里面已经没有这两个文件了
所以就只做一个单纯统计表大小的功能
虽然都是磁盘文件扫描, 但还是没办法和 ext3_check 整合
因为不太好把文件信息缓存下来共享使用, 可能会比较大
同时经过实际测试, 50w 表的统计耗时 2s, 所以独立扫描一次问题应该也不大
*/

var name = "ibd-statistic"

var ibdExt string
var partitionPattern *regexp.Regexp
var defaultMergeRules []*MergeRuleDef
var systemDBs = []string{
	"mysql",
	"sys",
	"information_schema",
	"infodba_schema",
	"performance_schema",
	"test",
	"db_infobase",
	cst.OTHER_DB_NAME,
}

func init() {
	ibdExt = ".ibd"
	partitionPattern = regexp.MustCompile(`^(.*)#[pP]#.*\.ibd`)

}

type MergeRuleDef struct {
	From string `mapstructure:"from"`
	To   string `mapstructure:"to"`
}

type ibdStatistic struct {
	// DisableMergePartition 是否合并分区表，默认合并
	DisableMergePartition bool `mapstructure:"disable_merge_partition"`
	// DisableMergeRules 是否启用库表名合并规则，默认启用，已内置 3 条规则
	DisableMergeRules bool `mapstructure:"disable_merge_rules"`

	// MergeRules 合并表名，比如 db\.test_(\d+) 会合并 db.test_1 db.test_2 成 db.test_X
	// 提示：这里的替换规则，可能会把 spider remote _<shard> 也去掉，统计时需要注意
	MergeRules []*MergeRuleDef `mapstructure:"merge_rules"`
	// TopkNum 只上报排名前 k 条记录，0 表示全部
	TopkNum int `mapstructure:"topk_num"`

	optionMap        monitoriteminterface.ItemOptions
	reMergeRulesFrom []*regexp.Regexp
	reMergeRulesTo   []string
	db               *sqlx.DB
}

// Run TODO
func (c *ibdStatistic) Run() (msg string, err error) {
	var dataDir sql.NullString
	err = c.db.Get(&dataDir, `SELECT @@datadir`)
	if err != nil {
		slog.Error("ibd-statistic", slog.String("error", err.Error()))
		return "", err
	}

	if !dataDir.Valid {
		err := errors.Errorf("invalid datadir: '%s'", dataDir.String)
		slog.Error("ibd-statistic", slog.String("error", err.Error()))
		return "", err
	}

	dbTableSize, dbSize, err := c.collectResult2(dataDir.String)
	if err != nil {
		return "", err
	}

	if c.TopkNum > 0 {
		type dbTableInfo struct {
			dbTableName string
			size        int64
		}
		var dbTableSizeSorted []dbTableInfo

		for k, v := range dbTableSize {
			dbTableSizeSorted = append(dbTableSizeSorted, dbTableInfo{dbTableName: k, size: v})
		}
		// 降序
		sort.Slice(dbTableSizeSorted, func(i, j int) bool {
			return dbTableSizeSorted[i].size > dbTableSizeSorted[j].size
		})
		dbTableSize = nil
		dbTableSize = make(map[string]int64) // reuse
		for i, sz := range dbTableSizeSorted {
			if i < c.TopkNum {
				dbTableSize[sz.dbTableName] = sz.size
			} else {
				dbTableSize[cst.OTHER_DB_TABLE_NAME] += sz.size
			}
		}
	}

	err = reportLog2(dbTableSize, dbSize)
	if err != nil {
		return "", err
	}

	return "", nil
}

// Name TODO
func (c *ibdStatistic) Name() string {
	return name
}

func (c *ibdStatistic) initCustomOptions() {
	defaultMergeRules = []*MergeRuleDef{
		// 规则配在 yaml 里要 \\. 转义
		// 合并转换后的库表明，必须是 dbX.tableY 格式，如果.分割出的 dbName,tableName 为空，会报错
		&MergeRuleDef{
			// "(?P<db>stage_truncate_).+\\..*"
			// 将以 stage_truncate_ 开头的库表 合并成 stage_truncate_MERGED._MERGED
			From: `(?P<db>stage_truncate_20\d\d).+\..*`,
			To:   `${db}_MERGED._MERGED`,
		},
		&MergeRuleDef{
			// "(?P<db>bak_20\\d\\d).+\\..*"
			// 将 bak_20190218_dbtest.tb1 / bak_20190318_dbtest_1.tb2 合并成 bak_2019._MERGED
			From: `(?P<db>bak_20\d\d).+\..*`,
			To:   `${db}_MERGED._MERGED`,
		},
		&MergeRuleDef{
			// "(bak_cbs)_.+_(\\d+)\\.(?P<table>.+)"
			// 将 bak_cbs_dbtest.tb1 bak_cbs_dbtesta.tb2  合并成 bak_cbs_X.tb1 bak_cbs_X.tb2
			From: `(bak_cbs)_.+\.(?P<table>.+)`,
			To:   `${1}_MERGED.${table}`,
		},
	}
	if config.MonitorConfig.MachineType == "remote" { // spider 集群
		defaultMergeRules = []*MergeRuleDef{
			// 规则配在 yaml 里要 \\. 转义
			// 合并转换后的库表明，必须是 dbX.tableY 格式，如果.分割出的 dbName,tableName 为空，会报错
			&MergeRuleDef{
				// "(?P<db>stage_truncate_).+\\..*"
				// 将以 stage_truncate_ 开头的库表 合并成 stage_truncate_MERGED._MERGED
				From: `(?P<db>stage_truncate_20\d\d)_.+_(?P<shard>\d+)\..*`,
				To:   `${db}_MERGED_${shard}._MERGED`,
			},
			&MergeRuleDef{
				// "(?P<db>bak_20\\d\\d).+\\..*"
				// 将 bak_20190218_dbtest.tb1 / bak_20190318_dbtest_1.tb2 合并成 bak_2019._MERGED
				From: `(?P<db>bak_20\d\d).+_(?P<shard>\d+)\..*`,
				To:   `${db}_MERGED_${shard}._MERGED`,
			},
			&MergeRuleDef{
				// "(bak_cbs)_.+_(\\d+)\\.(?P<table>.+)"
				// 将 bak_cbs_dbtest_0.tb1 bak_cbs_dbtesta_1.tb2  合并成 bak_cbs_X_0.tb1 bak_cbs_X_1.tb2
				From: `(bak_cbs)_.+_(\d+)\.(?P<table>.+)`,
				To:   `${1}_MERGED_${2}.${table}`,
			},
		}
	}
}

// New TODO
func New(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	opts := cc.GetCustomOptions(name)
	var itemObj ibdStatistic
	if err := mapstructure.Decode(opts, &itemObj); err != nil {
		panic(err)
	}
	itemObj.db = cc.MySqlDB
	itemObj.optionMap = opts

	itemObj.initCustomOptions()

	if !itemObj.DisableMergeRules {
		if len(itemObj.MergeRules) == 0 {
			itemObj.MergeRules = defaultMergeRules
			slog.Info("ibd-statistic", slog.String("msg", "use default merge rules"),
				slog.Int("count", len(itemObj.MergeRules)))
		} else {
			slog.Info("ibd-statistic", slog.String("msg", "use custom merge rules"),
				slog.Int("count", len(itemObj.MergeRules)))
		}
	}
	return &itemObj
}

// Register TODO
func Register() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return name, New
}

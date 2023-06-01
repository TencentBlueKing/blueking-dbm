package ext3_check

import (
	"fmt"
	"strings"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitor_item_interface"

	"github.com/jmoiron/sqlx"
	"github.com/pkg/errors"
)

/*
1. 先拿到 mysql 的 日志目录 和 数据目录
2. 看看是不是 ext3
3. 如果是就找有没有接近 2T 的文件
4. 是不是还要检查下文件的 +e 属性呢?
5. 是不是还要检查磁盘的 huge file 属性呢?
*/

var name = "ext3-check"

var mysqlDirVariables []string
var hugeSize int64

func init() {
	mysqlDirVariables = []string{
		"datadir",
		"innodb_data_home_dir",
		"slow_query_log_file",
		"tmpdir",
	}

	hugeSize = 1024 * 1024 * 1024 * 1024 // 1T
}

type ext3Check struct {
	db *sqlx.DB
}

// Run TODO
func (e *ext3Check) Run() (msg string, err error) {
	dirs, err := mysqlDirs(e.db, mysqlDirVariables)
	if err != nil {
		return "", errors.Wrap(err, "get mysql variable dirs")
	}

	ftDirs, err := filterDirFs(uniqueDirs(dirs), "ext3")
	if err != nil {
		return "", errors.Wrap(err, "filter dirs by fs")
	}

	hugeFiles, err := findHugeFile(ftDirs, hugeSize)
	if err != nil {
		return "", errors.Wrap(err, "find huge file")
	}

	if len(hugeFiles) > 0 {
		return fmt.Sprintf("ext3 FS huge file found: %s", strings.Join(hugeFiles, ",")), nil
	} else {
		return "", nil
	}
}

// Name TODO
func (e *ext3Check) Name() string {
	return name
}

// New TODO
func New(cc *monitor_item_interface.ConnectionCollect) monitor_item_interface.MonitorItemInterface {
	return &ext3Check{db: cc.MySqlDB}
}

// Register TODO
func Register() (string, monitor_item_interface.MonitorItemConstructorFuncType) {
	return name, New
}

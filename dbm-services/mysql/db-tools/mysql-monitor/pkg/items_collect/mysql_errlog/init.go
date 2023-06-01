package mysql_errlog

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitor_item_interface"

	"github.com/dlclark/regexp2"
	"github.com/jmoiron/sqlx"
	"golang.org/x/exp/slog"
)

var executable string
var maxScanSize int64 = 50 * 1024 * 1024
var offsetRegFile string
var errLogRegFile string
var scanned bool

var rowStartPattern *regexp2.Regexp
var baseErrTokenPattern *regexp2.Regexp

var nameMySQLErrNotice = "mysql-err-notice"
var nameMySQLErrCritical = "mysql-err-critical"
var nameSpiderErrNotice = "spider-err-notice"
var nameSpiderErrWarn = "spider-err-warn"
var nameSpiderErrCritical = "spider-err-critical"

var mysqlNoticePattern *regexp2.Regexp
var mysqlCriticalExcludePattern *regexp2.Regexp
var spiderNoticePattern *regexp2.Regexp
var spiderWarnPattern *regexp2.Regexp
var spiderCriticalPattern *regexp2.Regexp

func init() {
	executable, _ = os.Executable()
	offsetRegFile = filepath.Join(filepath.Dir(executable), "errlog_offset.reg")
	errLogRegFile = filepath.Join(filepath.Dir(executable), "errlog.reg")

	now := time.Now()
	rowStartPattern = regexp2.MustCompile(
		fmt.Sprintf(
			`^(?=(?:(%s|%s|%s)))`,
			now.Format("060102"),
			now.Format("20060102"),
			now.Format("2006-01-02"),
		),
		regexp2.None,
	)

	baseErrTokenPattern = regexp2.MustCompile(
		fmt.Sprintf(
			`(?=(?:(%s)))`,
			strings.Join(
				[]string{"error", "warn", "fail", "restarted", "hanging", "locked"},
				"|",
			),
		),
		regexp2.IgnoreCase,
	)

	spiderNoticePattern = regexp2.MustCompile(
		fmt.Sprintf(
			`(?=(?:(%s)))`,
			strings.Join(
				[]string{"Got error 12701", "Got error 1159"},
				"|",
			),
		),
		regexp2.IgnoreCase,
	)

	spiderWarnPattern = regexp2.MustCompile(
		fmt.Sprintf(
			`(?=(?:(%s)))`,
			strings.Join(
				[]string{"ERROR SPIDER RESULT", "Got error 1317", "Got error 1146"},
				"|",
			),
		),
		regexp2.IgnoreCase,
	)

	spiderCriticalPattern = regexp2.MustCompile(
		fmt.Sprintf(
			`(?=(?:(%s)))`,
			strings.Join(
				[]string{"2014 Commands out of sync", "Table has no partition"},
				"|",
			),
		),
		regexp2.IgnoreCase,
	)

	scanned = false
}

// Checker TODO
type Checker struct {
	db   *sqlx.DB
	name string
	f    func() (string, error)
}

// Run TODO
func (c *Checker) Run() (msg string, err error) {
	err = snapShot(c.db)
	if err != nil {
		slog.Error(c.name, err)
		return "", err
	}

	return c.f()
}

// Name TODO
func (c *Checker) Name() string {
	return c.name
}

// NewMySQLErrNotice TODO
func NewMySQLErrNotice(cc *monitor_item_interface.ConnectionCollect) monitor_item_interface.MonitorItemInterface {
	return &Checker{
		db:   cc.MySqlDB,
		name: nameMySQLErrNotice,
		f:    mysqlNotice,
	}
}

// NewMySQLErrCritical TODO
func NewMySQLErrCritical(cc *monitor_item_interface.ConnectionCollect) monitor_item_interface.MonitorItemInterface {
	return &Checker{
		db:   cc.MySqlDB,
		name: nameMySQLErrCritical,
		f:    mysqlCritical,
	}
}

// NewSpiderErrNotice TODO
func NewSpiderErrNotice(cc *monitor_item_interface.ConnectionCollect) monitor_item_interface.MonitorItemInterface {
	return &Checker{
		db:   cc.MySqlDB,
		name: nameSpiderErrNotice,
		f:    spiderNotice,
	}
}

// NewSpiderErrWarn TODO
func NewSpiderErrWarn(cc *monitor_item_interface.ConnectionCollect) monitor_item_interface.MonitorItemInterface {
	return &Checker{
		db:   cc.MySqlDB,
		name: nameSpiderErrWarn,
		f:    spiderWarn,
	}
}

// NewSpiderErrCritical TODO
func NewSpiderErrCritical(cc *monitor_item_interface.ConnectionCollect) monitor_item_interface.MonitorItemInterface {
	return &Checker{
		db:   cc.MySqlDB,
		name: nameSpiderErrCritical,
		f:    spiderCritical,
	}
}

// RegisterMySQLErrNotice TODO
func RegisterMySQLErrNotice() (string, monitor_item_interface.MonitorItemConstructorFuncType) {
	return nameMySQLErrNotice, NewMySQLErrNotice
}

// RegisterMySQLErrCritical TODO
func RegisterMySQLErrCritical() (string, monitor_item_interface.MonitorItemConstructorFuncType) {
	return nameMySQLErrCritical, NewMySQLErrCritical
}

// RegisterSpiderErrNotice TODO
func RegisterSpiderErrNotice() (string, monitor_item_interface.MonitorItemConstructorFuncType) {
	return nameSpiderErrNotice, NewSpiderErrNotice
}

// RegisterSpiderErrWarn TODO
func RegisterSpiderErrWarn() (string, monitor_item_interface.MonitorItemConstructorFuncType) {
	return nameSpiderErrWarn, NewSpiderErrWarn
}

// RegisterSpiderErrCritical TODO
func RegisterSpiderErrCritical() (string, monitor_item_interface.MonitorItemConstructorFuncType) {
	return nameSpiderErrCritical, NewSpiderErrCritical
}

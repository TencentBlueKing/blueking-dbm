package rotateslowlog

import (
	"dbm-services/common/go-pubpkg/reportlog"
	offsetlinescanner "dbm-services/common/reglinescanner"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/gofrs/flock"
	"github.com/jmoiron/sqlx"
)

var executable string

var reporterName = "report-slowlog"
var schemaHeadPattern *regexp.Regexp
var useDBPattern *regexp.Regexp

func init() {
	executable, _ = os.Executable()
	schemaHeadPattern = regexp.MustCompile(`(?smU)^#\s+Schema:\s+(.*)\s+.*$`)
	useDBPattern = regexp.MustCompile(`(?smUi)^use\s+(.*)\s*;$`)
}

type SlowlogReport struct {
	db                   *sqlx.DB
	currentDB            string
	currentDBRegFilePath string
	reporter             *reportlog.Reporter
}

func (c *SlowlogReport) Run() (msg string, err error) {
	slowLogOn, slowLogPath, err := slowLogStatus(c.db)
	if err != nil {
		return "", err
	}

	if !slowLogOn {
		return "", nil
	}

	lockFilePath := filepath.Join(
		cst.MySQLMonitorInstallPath, "locks", fmt.Sprintf("%d-%s.lock", config.MonitorConfig.Port, reporterName),
	)
	fl := flock.New(lockFilePath)
	defer func() {
		_ = fl.Unlock()
	}()

	_, err = fl.TryLock()
	if err != nil {
		return "", err
	}

	err = c.loadCurrentDBFromDisk()
	if err != nil {
		return "", err
	}

	err = c.initLogReporter()
	if err != nil {
		return "", err
	}

	offsetRegFilePath := filepath.Join(
		filepath.Dir(executable), fmt.Sprintf("slowlog_offset.%d.reg", config.MonitorConfig.Port),
	)

	scanner, err := offsetlinescanner.NewOffsetScanner(slowLogPath, offsetRegFilePath)
	if err != nil {
		return "", err
	}

	scanner.Buffer(make([]byte, 1024*1024*100), 1024*1024*100)

	var slowQuerySeg []string
	for scanner.Scan() {
		line := scanner.Text()
		line = strings.TrimSpace(line)
		if line == "" ||
			strings.HasPrefix(line, "Time") ||
			strings.HasPrefix(line, "Tcp") ||
			strings.HasPrefix(line, "/") ||
			strings.HasPrefix(line, "# Time") {
			continue
		}

		slowQuerySeg = append(slowQuerySeg, line)
		if !strings.HasPrefix(line, "#") && !strings.HasPrefix(line, "SET timestamp") {
			err := c.rewriteSeg(slowQuerySeg)
			if err != nil {
				return "", err
			}

			slowQuerySeg = []string{}
		}
	}
	if err := scanner.Err(); err != nil {
		return "", err
	}
	return "", nil
}

func (c *SlowlogReport) initLogReporter() error {
	slowLogRealDir := "/data/dbbak/slowlog-rewrite"
	err := os.MkdirAll(slowLogRealDir, 0755)
	if err != nil {
		return err
	}
	slowLogReportDir := filepath.Join(cst.DBAReportBase, "mysql/slowlog")

	err = os.Symlink(slowLogRealDir, slowLogReportDir)
	if err != nil && !errors.Is(err, os.ErrExist) {
		return err
	}

	logReporter, err := reportlog.NewReporter(
		slowLogReportDir, fmt.Sprintf("slowlog_%d.log", config.MonitorConfig.Port), &reportlog.LoggerOption{
			MaxSize:    100,
			MaxBackups: 1,
			MaxAge:     1,
			Compress:   false,
		},
	)
	if err != nil {
		return err
	}
	c.reporter = logReporter
	return nil
}

func (c *SlowlogReport) loadCurrentDBFromDisk() error {
	content, err := os.ReadFile(c.currentDBRegFilePath)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			c.currentDB = ""
			f, err := os.OpenFile(c.currentDBRegFilePath, os.O_RDONLY|os.O_CREATE, 0755)
			if err != nil {
				return err
			}
			_ = f.Close()
		} else {
			return err
		}
	}
	c.currentDB = strings.TrimSpace(string(content))
	return nil
}

func (c *SlowlogReport) rewriteSeg(slowQuerySeg []string) error {
	usedDB := c.catchUseDB(slowQuerySeg)
	if usedDB != "" {
		c.currentDB = usedDB
		err := os.WriteFile(c.currentDBRegFilePath, []byte(usedDB), 0644)
		if err != nil {
			return err
		}
	}

	hasSchemaDB, _ := c.catchSchemaDB(slowQuerySeg)

	var logSegContent []string
	for _, line := range slowQuerySeg {
		if !hasSchemaDB && strings.HasPrefix(line, "# Query_time") {
			logSegContent = append(logSegContent, fmt.Sprintf("# Schema: %s", c.currentDB))
		}
		logSegContent = append(logSegContent, line)
	}
	c.reporter.RawPrintln(strings.Join(logSegContent, "\n"))
	return nil
}

func (c *SlowlogReport) catchUseDB(slowQuerySeg []string) string {
	for _, line := range slowQuerySeg {
		m := useDBPattern.FindAllStringSubmatch(line, -1)
		if len(m) > 0 {
			return strings.TrimSpace(m[0][1])
		}
	}
	return ""
}

func (c *SlowlogReport) catchSchemaDB(slowQuerySeg []string) (bool, string) {
	for _, line := range slowQuerySeg {
		m := schemaHeadPattern.FindAllStringSubmatch(line, -1)
		if len(m) > 0 {
			return true, strings.TrimSpace(m[0][1])
		}
	}
	return false, ""
}

func (c *SlowlogReport) Name() string {
	return reporterName
}

func NewSlowlogReport(db *sqlx.DB) *SlowlogReport {
	r := &SlowlogReport{
		db: db,
		currentDBRegFilePath: filepath.Join(
			cst.MySQLMonitorInstallPath, fmt.Sprintf("%d-current_db.reg", config.MonitorConfig.Port),
		),
	}
	return r
}

func NewSlowlogReportItem(cc *monitoriteminterface.ConnectionCollect) monitoriteminterface.MonitorItemInterface {
	r := NewSlowlogReport(cc.MySqlDB)
	return r
}

func RegisterSlowlogReport() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return reporterName, NewSlowlogReportItem
}

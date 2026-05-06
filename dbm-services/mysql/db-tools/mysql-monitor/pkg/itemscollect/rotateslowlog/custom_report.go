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
	"strconv"
	"strings"
	"time"

	"github.com/gofrs/flock"
	"github.com/jmoiron/sqlx"
)

var executable string

var reporterName = "report-slowlog"
var schemaHeadPattern *regexp.Regexp
var useDBPattern *regexp.Regexp
var commentHeadTimePattern *regexp.Regexp
var setTimestampPattern *regexp.Regexp
var queryTimePattern *regexp.Regexp

func init() {
	executable, _ = os.Executable()
	schemaHeadPattern = regexp.MustCompile(`(?smU)^#\s+Schema:\s+(.*)\s+.*$`)
	useDBPattern = regexp.MustCompile(`(?smUi)^use\s+(.*)\s*;$`)
	commentHeadTimePattern = regexp.MustCompile(`(?m)^#\s+Time:\s+(.*)$`)
	setTimestampPattern = regexp.MustCompile(`(?m)^SET\s+timestamp\s*=\s*(\d+)\s*;$`)
	queryTimePattern = regexp.MustCompile(`(?m)^#\s+Query_time:\s+([\d.]+)`)
}

type SlowlogReport struct {
	db                         *sqlx.DB
	currentDB                  string
	currentDBRegFilePath       string
	commentHeadTime            string
	commentHeadTimeRegFilePath string
	reporter                   *reportlog.Reporter
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

	err = c.loadCommentHeadTimeFromDisk()
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
			strings.HasPrefix(line, "/") {
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

// loadStringFromDisk 从磁盘加载字符串内容的通用方法
func loadStringFromDisk(filePath string) (string, error) {
	content, err := os.ReadFile(filePath)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			f, err := os.OpenFile(filePath, os.O_RDONLY|os.O_CREATE, 0755)
			if err != nil {
				return "", err
			}
			_ = f.Close()
			return "", nil
		}
		return "", err
	}
	return strings.TrimSpace(string(content)), nil
}

func (c *SlowlogReport) loadCurrentDBFromDisk() error {
	val, err := loadStringFromDisk(c.currentDBRegFilePath)
	if err != nil {
		return err
	}
	c.currentDB = val
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

	hasCommentHeadTime, timeStr := c.catchCommentHeadTime(slowQuerySeg)
	if hasCommentHeadTime {
		c.commentHeadTime = timeStr
		err := os.WriteFile(c.commentHeadTimeRegFilePath, []byte(timeStr), 0644)
		if err != nil {
			return err
		}
	}

	var queryStartTs int64
	var hasValidQueryStartTs bool
	// 对比 commentHeadTime 和 SET timestamp 的时间戳
	hasSetTimestamp, setTs := c.catchSetTimestamp(slowQuerySeg)
	if hasSetTimestamp && c.commentHeadTime != "" {
		commentTs, err := parseTimeToTimestamp(c.commentHeadTime)
		if err == nil {
			if commentTs == setTs {
				// 时间戳相同，计算 query_start_ts
				hasQueryTime, queryTime := c.catchQueryTime(slowQuerySeg)
				if hasQueryTime {
					queryStartTs = setTs - int64(queryTime)
					hasValidQueryStartTs = true
				}
			} else {
				queryStartTs = setTs
				hasValidQueryStartTs = true
			}
		}
	}

	// 只有正常赋值才将 queryStartTs 写入 logSegContent 第一行
	var logSegContent []string
	if hasValidQueryStartTs {
		logSegContent = append(logSegContent, fmt.Sprintf("# Query_start_ts: %d", queryStartTs))
	}

	hasSchemaDB, _ := c.catchSchemaDB(slowQuerySeg)

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

// catchByPattern 通用的正则匹配方法
func catchByPattern(slowQuerySeg []string, pattern *regexp.Regexp) (bool, string) {
	for _, line := range slowQuerySeg {
		m := pattern.FindAllStringSubmatch(line, -1)
		if len(m) > 0 {
			return true, strings.TrimSpace(m[0][1])
		}
	}
	return false, ""
}

func (c *SlowlogReport) catchSchemaDB(slowQuerySeg []string) (bool, string) {
	return catchByPattern(slowQuerySeg, schemaHeadPattern)
}

func (c *SlowlogReport) loadCommentHeadTimeFromDisk() error {
	val, err := loadStringFromDisk(c.commentHeadTimeRegFilePath)
	if err != nil {
		return err
	}
	c.commentHeadTime = val
	return nil
}

func (c *SlowlogReport) catchCommentHeadTime(slowQuerySeg []string) (bool, string) {
	return catchByPattern(slowQuerySeg, commentHeadTimePattern)
}

// catchSetTimestamp 从 slowQuerySeg 中提取 SET timestamp=xxx 的时间戳
func (c *SlowlogReport) catchSetTimestamp(slowQuerySeg []string) (bool, int64) {
	for _, line := range slowQuerySeg {
		m := setTimestampPattern.FindAllStringSubmatch(line, -1)
		if len(m) > 0 {
			tsStr := strings.TrimSpace(m[0][1])
			ts, err := strconv.ParseInt(tsStr, 10, 64)
			if err == nil {
				return true, ts
			}
		}
	}
	return false, 0
}

// catchQueryTime 从 slowQuerySeg 中提取 Query_time 的值（秒）
func (c *SlowlogReport) catchQueryTime(slowQuerySeg []string) (bool, float64) {
	for _, line := range slowQuerySeg {
		m := queryTimePattern.FindAllStringSubmatch(line, -1)
		if len(m) > 0 {
			qtStr := strings.TrimSpace(m[0][1])
			qt, err := strconv.ParseFloat(qtStr, 64)
			if err == nil {
				return true, qt
			}
		}
	}
	return false, 0
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
		commentHeadTimeRegFilePath: filepath.Join(
			cst.MySQLMonitorInstallPath, fmt.Sprintf("%d-comment_head_time.reg", config.MonitorConfig.Port),
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

// parseTimeToTimestamp 将三种不同格式的时间字符串转换为时间戳
// 格式1: "260127  2:05:24" (YYMMDD  H:MM:SS，中间可能有多个空格)
// 格式2: "2026-01-27T01:58:55.960323+08:00" (RFC3339Nano 带时区)
// 格式3: "2026-01-24T19:03:14.039913Z" (RFC3339Nano UTC时区)
func parseTimeToTimestamp(timeStr string) (int64, error) {
	var t time.Time
	var err error

	// 尝试格式2和格式3: RFC3339Nano (带时区或UTC)
	t, err = time.Parse(time.RFC3339Nano, timeStr)
	if err == nil {
		return t.Unix(), nil
	}

	// 尝试格式3的变体: RFC3339 (不带纳秒)
	t, err = time.Parse(time.RFC3339, timeStr)
	if err == nil {
		return t.Unix(), nil
	}

	// 尝试格式1: "260127  2:05:24" (YYMMDD + 多个空格 + H:MM:SS)
	// 先用正则标准化：将多个空格替换为单个空格
	re := regexp.MustCompile(`\s+`)
	normalizedStr := re.ReplaceAllString(timeStr, " ")

	// 解析标准化后的格式，使用本地时区
	t, err = time.ParseInLocation("060102 15:04:05", normalizedStr, time.Local)
	if err == nil {
		return t.Unix(), nil
	}

	return 0, fmt.Errorf("无法解析时间格式: %s", timeStr)
}

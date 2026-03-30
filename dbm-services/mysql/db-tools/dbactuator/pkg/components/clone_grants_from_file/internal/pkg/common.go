package pkg

import (
	"bufio"
	"dbm-services/common/go-pubpkg/logger"
	"fmt"
	"os"
	"regexp"
	"strings"
	"sync/atomic"
	"time"
)

// BuildSystemUserMap 合并静态和动态系统用户列表，返回用于快速查找的 map。
// staticUsers 是预定义的系统用户列表，dynamicUsers 是运行时传入的额外系统用户。
func BuildSystemUserMap(staticUsers, dynamicUsers []string) map[string]struct{} {
	m := make(map[string]struct{}, len(staticUsers)+len(dynamicUsers))
	for _, u := range staticUsers {
		m[u] = struct{}{}
	}
	for _, u := range dynamicUsers {
		m[u] = struct{}{}
	}
	return m
}

// HostReplacer 封装 IP 替换逻辑。
// 当 sourceIP 和 targetIP 不同且均非空时，替换语句中的 host 部分。
type HostReplacer struct {
	needReplace bool
	oldHostSQ   string // 单引号格式: 'sourceIP'
	newHostSQ   string // 单引号格式: 'targetIP'
	oldHostBQ   string // 反引号格式: `sourceIP`
	newHostBQ   string // 反引号格式: `targetIP`
}

// NewHostReplacer 创建 HostReplacer。
// 如果 sourceIP 和 targetIP 相同或任一为空，则 Replace 方法不做任何替换。
func NewHostReplacer(sourceIP, targetIP string) *HostReplacer {
	r := &HostReplacer{}
	if sourceIP != "" && targetIP != "" && sourceIP != targetIP {
		r.needReplace = true
		r.oldHostSQ = "@'" + sourceIP + "'"
		r.newHostSQ = "@'" + targetIP + "'"
		r.oldHostBQ = "@`" + sourceIP + "`"
		r.newHostBQ = "@`" + targetIP + "`"
	}
	return r
}

// Replace 对语句执行 host 替换，同时处理单引号和反引号两种格式。
// 如果不需要替换，原样返回。
func (r *HostReplacer) Replace(stmt string) string {
	if !r.needReplace {
		return stmt
	}
	stmt = strings.ReplaceAll(stmt, r.oldHostSQ, r.newHostSQ)
	stmt = strings.ReplaceAll(stmt, r.oldHostBQ, r.newHostBQ)
	return stmt
}

// LineScanner 封装逐行扫描 SQL 备份文件的通用逻辑：
// 进度日志、去除行尾分号、跳过空行。
//
// 进度日志通过独立的 ticker goroutine 按固定时间间隔输出，
// 避免快速处理大量行时造成日志风暴。调用方必须在使用完毕后调用 Stop()。
type LineScanner struct {
	scanner    *bufio.Scanner
	path       string
	totalLines int
	lineNo     int64
	stmt       string
	stopCh     chan struct{}
}

// ProgressLogDuration 进度日志的输出时间间隔。
const ProgressLogDuration = 5 * time.Second

// NewLineScanner 创建 LineScanner 并启动后台进度日志 goroutine。
// 调用方必须在扫描结束后调用 Stop() 停止后台 goroutine。
func NewLineScanner(scanner *bufio.Scanner, path string, totalLines int) *LineScanner {
	ls := &LineScanner{
		scanner:    scanner,
		path:       path,
		totalLines: totalLines,
		stopCh:     make(chan struct{}),
	}
	go ls.progressLogger()
	return ls
}

func (ls *LineScanner) progressLogger() {
	ticker := time.NewTicker(ProgressLogDuration)
	defer ticker.Stop()

	for {
		select {
		case <-ticker.C:
			current := atomic.LoadInt64(&ls.lineNo)
			logger.Info("scanning file=%s currentLine=%d totalLines=%d", ls.path, current, ls.totalLines)
		case <-ls.stopCh:
			return
		}
	}
}

// Stop 停止后台进度日志 goroutine。必须在扫描结束后调用。
func (ls *LineScanner) Stop() {
	close(ls.stopCh)
}

// Next 读取下一个非空语句。
// 返回 false 表示没有更多行。调用方通过 Stmt() 获取当前语句，LineNo() 获取行号。
func (ls *LineScanner) Next() bool {
	for ls.scanner.Scan() {
		atomic.AddInt64(&ls.lineNo, 1)
		line := ls.scanner.Text()

		stmt := strings.TrimSuffix(strings.TrimSpace(line), ";")
		if stmt == "" {
			continue
		}

		ls.stmt = stmt
		return true
	}
	return false
}

// Stmt 返回当前行去除首尾空白和尾部分号后的语句。
func (ls *LineScanner) Stmt() string {
	return ls.stmt
}

// LineNo 返回当前行号。
func (ls *LineScanner) LineNo() int {
	return int(atomic.LoadInt64(&ls.lineNo))
}

// Err 返回扫描过程中的错误。
func (ls *LineScanner) Err() error {
	return ls.scanner.Err()
}

// IsGrantUsageOnAll 判断语句是否是 GRANT USAGE ON *.* 格式。
//
// 在 MySQL 5.5/5.6 中，GRANT USAGE ON *.* 是"创建用户"的载体，本身不授予任何实际权限。
// SHOW GRANTS 输出中，全局级别的用户信息（认证、资源限制）都附着在这条语句上。
//
// 示例匹配：
//
//	GRANT USAGE ON *.* TO 'app'@'%'
//	GRANT USAGE ON *.* TO 'app'@'%' IDENTIFIED BY PASSWORD '*xxx' WITH MAX_QUERIES_PER_HOUR 90
//
// 示例不匹配：
//
//	GRANT SELECT ON *.* TO 'app'@'%'
//	GRANT USAGE ON `db`.* TO 'app'@'%'
func IsGrantUsageOnAll(stmt string) bool {
	upper := strings.ToUpper(strings.TrimSpace(stmt))
	return strings.HasPrefix(upper, "GRANT USAGE ON *.*")
}

// IsSystemOrJobUser 判断用户是否为系统用户或 Job 账号，这类用户在权限迁移时应跳过。
//
// 系统用户通过 systemUsers map 查找（由 BuildSystemUserMap 生成）。
// Job 账号使用 "J_" 前缀命名，且 host 为 localhost 或源 IP，
// 例如 'J_backup'@'localhost'
func IsSystemOrJobUser(user, host, sourceIP string, systemUsers map[string]struct{}) bool {
	if _, ok := systemUsers[user]; ok {
		return true
	}
	return strings.HasPrefix(user, "J_") && (host == "localhost" || host == sourceIP)
}

// OpenFileWithScanner 打开文件并创建带大缓冲区的 Scanner。
// 返回 Scanner、关闭函数和可能的错误。调用方必须在使用完毕后调用 closeFunc。
func OpenFileWithScanner(path string) (*bufio.Scanner, func(), error) {
	f, err := os.Open(path)
	if err != nil {
		logger.Error("open backup file: %v", err)
		return nil, nil, fmt.Errorf("open backup file: %w", err)
	}
	logger.Info("opened backup file for scanning file=%s", path)

	scanner := bufio.NewScanner(f)
	scanner.Buffer(make([]byte, 0, 1024*1024), 1024*1024)

	closeFunc := func() {
		_ = f.Close()
	}

	return scanner, closeFunc, nil
}

// ReplacePrivName 在 GRANT 语句中将旧权限名替换为新权限名（大小写不敏感）。
func ReplacePrivName(stmt, oldPriv, newPriv string) string {
	re := regexp.MustCompile(`(?i)` + regexp.QuoteMeta(oldPriv))
	return re.ReplaceAllLiteralString(stmt, newPriv)
}

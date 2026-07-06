package reportslowlog

import (
	"bufio"
	"bytes"
	"errors"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/go-viper/mapstructure/v2"

	offsetlinescanner "dbm-services/common/reglinescanner"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/config"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"

	"github.com/gofrs/flock"
	"github.com/jmoiron/sqlx"
)

var executable string

var reporterName = "slowlog-rewrite"

func init() {
	executable, _ = os.Executable()
}

// maxLogFileSize 单个日志文件最大大小（200MB），超过后轮转
// 这个文件目标不是给人长期看到，是用于日志采集上报，所以不需要保留太久
const maxLogFileSize = 200 * 1024 * 1024

type SlowlogReport struct {
	// SlowLogFile 手动指定 log file path
	SlowLogFile string `mapstructure:"slow_log_file"`

	db                         *sqlx.DB
	currentDB                  string
	currentDBRegFilePath       string
	commentHeadTime            string
	commentHeadTs              int64 // commentHeadTime 对应的缓存 unix timestamp
	commentHeadTsCached        bool  // commentHeadTs 是否已缓存
	commentHeadTimeRegFilePath string
	logFilePath                string
	logFile                    *os.File
	writer                     *bufio.Writer
	writtenBytes               int64 // 当前文件已写入字节数
	// 复用的段缓冲区，避免每段重新分配
	segBuf           []byte      // 连续内存块，存储当前段所有行的原始数据
	segRanges        []lineRange // 每行在 segBuf 中的偏移量和长度
	segF             segFields   // 扫描时同步收集的字段
	firstBodyLineIdx int         // 第一个非 # 行在 segRanges 中的索引，-1 表示全是注释行
	scanner          *offsetlinescanner.OffsetCommitScanner
}

// lineRange 记录一行在 segBuf 中的位置
type lineRange struct {
	offset int
	length int
}

func isSegmentStartLine(line []byte) bool {
	return bytes.HasPrefix(line, TimePrefix) || bytes.HasPrefix(line, UserPrefix)
}

func isBlankLine(line []byte) bool {
	return len(bytes.TrimSpace(line)) == 0
}

func isSkippableSlowlogHeaderLine(line []byte) bool {
	line = bytes.TrimSpace(line)
	return bytes.HasPrefix(line, []byte("Time")) ||
		bytes.HasPrefix(line, []byte("Tcp")) ||
		bytes.HasPrefix(line, []byte("/"))
}

func lineEndsWithSemicolon(line []byte) bool {
	// line = bytes.TrimRight(line, " \t\r")
	return len(line) > 0 && line[len(line)-1] == ';'
}

func firstNonSpaceByte(line []byte) byte {
	line = bytes.TrimLeft(line, " \t\r\n\v\f")
	if len(line) == 0 {
		return 0
	}
	return line[0]
}

func (c *SlowlogReport) ProcessSlowLog(slowLogPath string) (string, error) {
	var err error
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

	err = c.initLogWriter()
	if err != nil {
		return "", err
	}
	defer func() {
		if closeErr := c.closeLogWriter(); closeErr != nil && err == nil {
			err = closeErr
		}
	}()

	offsetRegFilePath := filepath.Join(
		filepath.Dir(executable), fmt.Sprintf("slowlog_offset.%d.reg", config.MonitorConfig.Port),
	)

	scanner, err := offsetlinescanner.NewOffsetCommitScanner(slowLogPath, offsetRegFilePath)
	if err != nil {
		return "", err
	}
	defer func() {
		if closeErr := scanner.Close(); closeErr != nil && err == nil {
			err = closeErr
		}
	}()
	c.scanner = scanner

	//scanner.Buffer(make([]byte, 64*1024), 100*1024*1024)

	// 预分配段缓冲区（初始 64KB，会按需增长但不会缩小，跨段复用）
	if c.segBuf == nil {
		c.segBuf = make([]byte, 0, 64*1024)
	}
	if c.segRanges == nil {
		c.segRanges = make([]lineRange, 0, 128)
	}
	c.segRanges = c.segRanges[:0]
	c.segBuf = c.segBuf[:0]

	const commitInterval = 100 // 每处理 50 个段才提交一次 offset，减少 reg 文件写入 IO
	var segCount int           // 自上次 Commit 以来已处理的段数
	var segReady bool          // 标记当前段最后一行是否以分号结尾，等待下一个 # Time 行确认段结束
	var inSegment bool         // 标记是否已进入段内（遇到 # Time: 或 # User@Host: 后为 true）
	c.segF = segFields{}
	c.firstBodyLineIdx = -1
	for scanner.Scan() {
		rawLine := scanner.Bytes()
		line := bytes.TrimSpace(rawLine)

		// 段结束判断：前一行以分号结尾（segReady），且当前行是 "# Time:" 或 "# User@Host:" 开头（下一个段的起始）
		if segReady && isSegmentStartLine(rawLine) {
			if err := c.rewriteSeg(); err != nil {
				return "", err
			}

			segCount++
			// 批量提交 offset：每 commitInterval 个段才写一次 reg 文件，减少磁盘 IO
			if segCount >= commitInterval {
				if err := c.updateOffsetFile(); err != nil {
					return "", err
				}
				segCount = 0
			}
			// 重置段缓冲区和字段（保留底层容量）
			c.resetSeg()
			segReady = false
			inSegment = false // 标记段结束
		}

		// 遇到段起始行，标记进入段内
		if isSegmentStartLine(rawLine) {
			inSegment = true
		}

		// 仅在段外跳过 slowlog 文件头信息行（Time/Tcp// 开头）
		// 段内不跳过任何行，避免误删以 / 开头的 SQL hint、空行等合法内容
		if !inSegment {
			continue
		}

		// 将行数据追加到连续的 segBuf 中，记录偏移量和长度
		start := len(c.segBuf)
		c.segBuf = append(c.segBuf, rawLine...)
		c.segRanges = append(c.segRanges, lineRange{offset: start, length: len(rawLine)})

		// 同步解析该行，更新 segFields
		c.parseLine(line)

		// 记录第一个非 # 行的索引（注入位置）
		firstByte := firstNonSpaceByte(rawLine)
		if c.firstBodyLineIdx < 0 && firstByte != 0 && firstByte != '#' {
			c.firstBodyLineIdx = len(c.segRanges) - 1
		}

		// 任何非空行以分号结尾时，标记段待提交（等待下一个 # Time 行确认）
		// 段内空行属于原始 SQL 内容，不应清除 segReady，否则分号后的空行会导致下一段 header 无法切段。
		if !isBlankLine(rawLine) {
			segReady = lineEndsWithSemicolon(rawLine)
		}
	}
	// 先检查 scanner 是否有错误，有错误时不处理残留段，直接返回
	if err := scanner.Err(); err != nil {
		return "", err
	}
	// 处理末尾残留段：仅当最后一行以分号结尾（segReady）时才处理，避免消费半段
	if len(c.segRanges) > 0 && segReady {
		if err := c.rewriteSeg(); err != nil {
			return "", err
		}
		if err := c.updateOffsetFile(); err != nil {
			return "", err
		}
	}

	return "", nil
}

func (c *SlowlogReport) Run() (msg string, err error) {
	if c.SlowLogFile == "" {
		slowLogOn, slowLogPath, err := slowLogStatus(c.db)
		if err != nil {
			return "", err
		}
		if !slowLogOn {
			return "", nil
		}
		c.SlowLogFile = slowLogPath
	}

	return c.ProcessSlowLog(c.SlowLogFile)
}

// updateOffset 尽可能保证原子操作
func (c *SlowlogReport) updateOffsetFile() error {
	if err := c.writer.Flush(); err != nil {
		return err
	}
	if err := c.scanner.Commit(); err != nil {
		return err
	}
	// 统一持久化状态文件到磁盘
	if err := c.persistState(); err != nil {
		return err
	}
	return nil
}

// initLogWriter 初始化直接写入的 bufio.Writer，绕过 lumberjack 减少内存拷贝
func (c *SlowlogReport) initLogWriter() error {
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

	c.logFilePath = filepath.Join(slowLogReportDir, fmt.Sprintf("slowlog_%d.log", config.MonitorConfig.Port))

	// 打开文件（追加模式），获取当前文件大小
	f, err := os.OpenFile(c.logFilePath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err != nil {
		return err
	}

	fi, err := f.Stat()
	if err != nil {
		_ = f.Close()
		return err
	}

	c.logFile = f
	c.writtenBytes = fi.Size()
	// 使用 256KB 的写缓冲区，减少系统调用次数
	c.writer = bufio.NewWriterSize(f, 256*1024)
	return nil
}

// closeLogWriter 刷新缓冲区并关闭文件，返回 flush 或 close 过程中的第一个错误
func (c *SlowlogReport) closeLogWriter() error {
	var firstErr error
	if c.writer != nil {
		if err := c.writer.Flush(); err != nil {
			firstErr = err
		}
	}
	if c.logFile != nil {
		if err := c.logFile.Close(); err != nil && firstErr == nil {
			firstErr = err
		}
	}
	return firstErr
}

// resetSeg 重置段缓冲区和字段，保留底层容量
// maxKeepSegBufCap segBuf 容量回收阈值（4MB）
const maxKeepSegBufCap = 4 * 1024 * 1024

// maxKeepSegRangesCap segRanges 容量回收阈值（10000 行）
const maxKeepSegRangesCap = 10000

func (c *SlowlogReport) resetSeg() {
	// segBuf 容量回收：超过 4MB 时重新分配，避免异常大 SQL 导致永久占用
	if cap(c.segBuf) > maxKeepSegBufCap {
		c.segBuf = make([]byte, 0, 64*1024)
	} else {
		c.segBuf = c.segBuf[:0]
	}
	// segRanges 容量回收
	if cap(c.segRanges) > maxKeepSegRangesCap {
		c.segRanges = make([]lineRange, 0, 128)
	} else {
		c.segRanges = c.segRanges[:0]
	}
	c.segF = segFields{}
	c.firstBodyLineIdx = -1
}

// parseLine 解析单行并更新 segFields（扫描时同步调用，避免二次遍历）
func (c *SlowlogReport) parseLine(line []byte) {
	if len(line) == 0 {
		return
	}
	if line[0] == '#' {
		if !c.segF.hasTime && bytes.HasPrefix(line, TimePrefix) {
			val := bytes.TrimSpace(line[len(TimePrefix):])
			if len(val) > 0 {
				c.segF.timeStr = string(val)
				c.segF.hasTime = true
			}
			return
		}
		if !c.segF.hasQT && bytes.HasPrefix(line, QueryTimePrefix) {
			rest := bytes.TrimLeft(line[len(QueryTimePrefix):], " \t")
			end := bytes.IndexByte(rest, ' ')
			var numBytes []byte
			if end > 0 {
				numBytes = rest[:end]
			} else {
				numBytes = rest
			}
			if len(numBytes) > 0 {
				qt, err := strconv.ParseFloat(string(numBytes), 64)
				if err == nil {
					c.segF.queryTime = qt
					c.segF.hasQT = true
				}
			}
		}
		if c.segF.schema == "" {
			if idx := bytes.Index(line, []byte("Schema:")); idx >= 0 {
				rest := line[idx+7:]
				rest = bytes.TrimLeft(rest, " \t")
				end := bytes.IndexByte(rest, ' ')
				var val []byte
				if end > 0 {
					val = rest[:end]
				} else if len(rest) > 0 {
					val = rest
				}
				if len(val) > 0 && !bytes.Contains(val, []byte(":")) {
					c.segF.schema = string(val)
				}
			}
		}
		if c.segF.sessionId == "" {
			c.segF.sessionId = extractSessionId(line)
		}
	} else {
		if c.segF.usedDB == "" {
			c.segF.usedDB = extractUseDB(line)
		}
		if !c.segF.hasSetTs {
			if ts, ok := extractSetTimestamp(line); ok {
				c.segF.setTs = ts
				c.segF.hasSetTs = true
			}
		}
	}
}

// rotateIfNeeded 检查文件大小，超过阈值则轮转
func (c *SlowlogReport) rotateIfNeeded() error {
	if c.writtenBytes < maxLogFileSize {
		return nil
	}

	// 先刷新缓冲区
	if err := c.writer.Flush(); err != nil {
		return err
	}
	_ = c.logFile.Close()

	// 轮转：删除旧的备份文件，将当前文件重命名为备份
	backupPath := c.logFilePath + ".1"
	_ = os.Remove(backupPath)
	_ = os.Rename(c.logFilePath, backupPath)

	// 重新打开新文件
	f, err := os.OpenFile(c.logFilePath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err != nil {
		return err
	}
	c.logFile = f
	c.writer.Reset(f)
	c.writtenBytes = 0
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

// buildSegLines 从 segBuf 和 segRanges 构建 [][]byte 切片（保留供测试使用）
func (c *SlowlogReport) buildSegLines() [][]byte {
	lines := make([][]byte, len(c.segRanges))
	for i, r := range c.segRanges {
		lines[i] = c.segBuf[r.offset : r.offset+r.length]
	}
	return lines
}

// rewriteSegBytes 兼容方法：接收 segLines 参数，内部调用 collectSegFields + rewriteSeg
// 保留供测试使用，主逻辑已改用 parseLine + rewriteSeg
func (c *SlowlogReport) rewriteSegBytes(segLines [][]byte) error {
	// 使用 collectSegFields 收集字段
	c.segF = c.collectSegFields(segLines)
	// 填充 segBuf 和 segRanges
	c.segBuf = c.segBuf[:0]
	c.segRanges = c.segRanges[:0]
	c.firstBodyLineIdx = -1
	for i, line := range segLines {
		start := len(c.segBuf)
		c.segBuf = append(c.segBuf, line...)
		c.segRanges = append(c.segRanges, lineRange{offset: start, length: len(line)})
		if c.firstBodyLineIdx < 0 && len(line) > 0 && line[0] != '#' {
			c.firstBodyLineIdx = i
		}
	}
	// 兼容：如果 commentHeadTime 非空但未缓存 timestamp，先解析缓存
	if c.commentHeadTime != "" && !c.commentHeadTsCached {
		ts, err := parseTimeToTimestamp(c.commentHeadTime)
		if err == nil {
			c.commentHeadTs = ts
			c.commentHeadTsCached = true
		}
	}
	return c.rewriteSeg()
}

// segFields 存储从段中一次性收集的所有字段
type segFields struct {
	usedDB    string  // use xxx 语句中的数据库名
	schema    string  // Schema: xxx 中的数据库名
	sessionId string  // Id: xxx 或 Thread_id: xxx 中的会话 ID
	timeStr   string  // # Time: xxx 中的时间字符串
	setTs     int64   // SET timestamp=xxx 中的时间戳
	queryTime float64 // Query_time: xxx 中的查询耗时
	hasTime   bool    // 是否有 # Time 行
	hasSetTs  bool    // 是否有 SET timestamp 行
	hasQT     bool    // 是否有 Query_time 行
}

// collectSegFields 一次遍历 segLines，收集所有需要的字段（全部使用手写 parser，无正则）
func (c *SlowlogReport) collectSegFields(segLines [][]byte) segFields {
	var f segFields
	for _, line := range segLines {
		if len(line) == 0 {
			continue
		}
		if line[0] == '#' {
			// 提取 # Time: xxx
			if !f.hasTime && bytes.HasPrefix(line, TimePrefix) {
				val := bytes.TrimSpace(line[len(TimePrefix):])
				if len(val) > 0 {
					f.timeStr = string(val)
					f.hasTime = true
				}
				continue
			}
			// 提取 # Query_time: xxx（手写解析浮点数）
			if !f.hasQT && bytes.HasPrefix(line, QueryTimePrefix) {
				rest := bytes.TrimLeft(line[len(QueryTimePrefix):], " \t")
				// 截取到下一个空格
				end := bytes.IndexByte(rest, ' ')
				var numBytes []byte
				if end > 0 {
					numBytes = rest[:end]
				} else {
					numBytes = rest
				}
				if len(numBytes) > 0 {
					qt, err := strconv.ParseFloat(string(numBytes), 64)
					if err == nil {
						f.queryTime = qt
						f.hasQT = true
					}
				}
			}
			// 提取 Schema: xxx（手写解析，验证值不含 ':'）
			if f.schema == "" {
				if idx := bytes.Index(line, []byte("Schema:")); idx >= 0 {
					rest := line[idx+7:]
					rest = bytes.TrimLeft(rest, " \t")
					end := bytes.IndexByte(rest, ' ')
					var val []byte
					if end > 0 {
						val = rest[:end]
					} else if len(rest) > 0 {
						val = rest
					}
					if len(val) > 0 && !bytes.Contains(val, []byte(":")) {
						f.schema = string(val)
					}
				}
			}
			// 提取 Id: xxx 或 Thread_id: xxx（手写解析数字）
			if f.sessionId == "" {
				f.sessionId = extractSessionId(line)
			}
		} else {
			// 非注释行：提取 use xxx; 和 SET timestamp=xxx;
			if f.usedDB == "" {
				f.usedDB = extractUseDB(line)
			}
			if !f.hasSetTs {
				if ts, ok := extractSetTimestamp(line); ok {
					f.setTs = ts
					f.hasSetTs = true
				}
			}
		}
	}
	return f
}

// extractSessionId 从注释行中提取 Id: 或 Thread_id: 后面的数字
func extractSessionId(line []byte) string {
	// 尝试 "Id:" 和 "Thread_id:"
	for _, key := range [][]byte{[]byte("Id:"), []byte("Thread_id:")} {
		idx := bytes.Index(line, key)
		if idx < 0 {
			continue
		}
		rest := line[idx+len(key):]
		rest = bytes.TrimLeft(rest, " \t")
		// 扫描连续数字
		end := 0
		for end < len(rest) && rest[end] >= '0' && rest[end] <= '9' {
			end++
		}
		if end > 0 {
			return string(rest[:end])
		}
	}
	return ""
}

// extractUseDB 从行中提取 use xxx; 语句的数据库名（大小写不敏感）
func extractUseDB(line []byte) string {
	// 检查是否以 "use " 或 "USE " 开头（简化的大小写不敏感检查）
	var rest []byte
	if bytes.HasPrefix(line, usePrefix) {
		rest = line[4:]
	} else if bytes.HasPrefix(line, UsePrefix) {
		rest = line[4:]
	} else if len(line) >= 4 && (line[0] == 'u' || line[0] == 'U') &&
		(line[1] == 's' || line[1] == 'S') && (line[2] == 'e' || line[2] == 'E') &&
		(line[3] == ' ' || line[3] == '\t') {
		rest = line[4:]
	} else {
		return ""
	}
	// 去掉末尾分号
	rest = bytes.TrimSpace(rest)
	if len(rest) == 0 {
		return ""
	}
	if rest[len(rest)-1] == ';' {
		rest = rest[:len(rest)-1]
	}
	rest = bytes.TrimSpace(rest)
	if len(rest) == 0 {
		return ""
	}
	// 去掉反引号
	return strings.Trim(string(rest), "`")
}

// extractSetTimestamp 从行中提取 SET timestamp=xxx; 中的时间戳
func extractSetTimestamp(line []byte) (int64, bool) {
	var rest []byte
	if bytes.HasPrefix(line, SetTimestampPrefix) {
		rest = line[len(SetTimestampPrefix):]
	} else if bytes.HasPrefix(line, SetTimestampPrefixUpper) {
		rest = line[len(SetTimestampPrefixUpper):]
	} else {
		// 更宽松的匹配：SET timestamp = xxx（中间可能有空格）
		lower := bytes.ToLower(line)
		if !bytes.HasPrefix(lower, []byte("set")) {
			return 0, false
		}
		idx := bytes.Index(lower, []byte("timestamp"))
		if idx < 0 {
			return 0, false
		}
		eqIdx := bytes.IndexByte(line[idx+9:], '=')
		if eqIdx < 0 {
			return 0, false
		}
		rest = line[idx+9+eqIdx+1:]
	}
	// 扫描连续数字
	rest = bytes.TrimLeft(rest, " \t")
	end := 0
	for end < len(rest) && rest[end] >= '0' && rest[end] <= '9' {
		end++
	}
	if end == 0 {
		return 0, false
	}
	ts, err := strconv.ParseInt(string(rest[:end]), 10, 64)
	if err != nil {
		return 0, false
	}
	return ts, true
}

// rewriteSeg 使用已收集的 segFields 和 segBuf/segRanges 写入段内容
// 利用 firstBodyLineIdx 分两段写入（header + inject + body），避免逐行判断
func (c *SlowlogReport) rewriteSeg() error {
	f := &c.segF

	// 更新内存中的 currentDB（磁盘持久化延迟到 Run() 结束时统一写入）
	if f.usedDB != "" {
		c.currentDB = f.usedDB
	}

	// 更新内存中的 commentHeadTime（磁盘持久化延迟到 Run() 结束时统一写入）
	if f.hasTime {
		c.commentHeadTime = f.timeStr
		// 同步解析并缓存 timestamp
		ts, err := parseTimeToTimestamp(f.timeStr)
		if err == nil {
			c.commentHeadTs = ts
			c.commentHeadTsCached = true
		} else {
			c.commentHeadTsCached = false
		}
	}

	// 计算 Query_start_ts
	var queryStartTs int64
	var hasValidQueryStartTs bool
	if f.hasSetTs && c.commentHeadTsCached {
		commentTs := c.commentHeadTs
		if commentTs == f.setTs {
			if f.hasQT {
				queryStartTs = f.setTs - int64(f.queryTime)
				hasValidQueryStartTs = true
			}
		} else {
			// mysql 8.0.14 之后， SET timestamp 是 sql 开始时间
			queryStartTs = f.setTs
			hasValidQueryStartTs = true
		}
	}

	// 确定 DB_name：优先使用段内已有的 Schema 信息，如果没有则使用上下文记录的 currentDB
	schemaToWrite := c.currentDB
	if f.schema != "" {
		schemaToWrite = f.schema
	}

	// 构建注入行内容：使用 strings.Builder 减少分配
	var b strings.Builder
	b.Grow(64 + len(schemaToWrite) + len(f.sessionId))
	b.WriteString("# Db_name: ")
	b.WriteString(schemaToWrite)
	if hasValidQueryStartTs {
		b.WriteString("  Query_start_ts: ")
		b.WriteString(strconv.FormatInt(queryStartTs, 10))
	}
	if f.sessionId != "" {
		b.WriteString("  Session_id: ")
		b.WriteString(f.sessionId)
	}
	b.WriteByte('\n')
	injectLine := b.String()

	// 确定注入位置
	bodyIdx := c.firstBodyLineIdx
	if bodyIdx < 0 {
		bodyIdx = len(c.segRanges) // 全是注释行，注入到末尾
	}

	// 写入 header 部分（# 注释行）
	for i := 0; i < bodyIdx; i++ {
		r := c.segRanges[i]
		n, err := c.writer.Write(c.segBuf[r.offset : r.offset+r.length])
		if err != nil {
			return err
		}
		c.writtenBytes += int64(n)
		n, err = c.writer.WriteString("\n")
		if err != nil {
			return err
		}
		c.writtenBytes += int64(n)
	}

	// 写入注入行
	n, err := c.writer.WriteString(injectLine)
	if err != nil {
		return err
	}
	c.writtenBytes += int64(n)

	// 写入 body 部分（SQL 行）
	for i := bodyIdx; i < len(c.segRanges); i++ {
		r := c.segRanges[i]
		n, err := c.writer.Write(c.segBuf[r.offset : r.offset+r.length])
		if err != nil {
			return err
		}
		c.writtenBytes += int64(n)
		n, err = c.writer.WriteString("\n")
		if err != nil {
			return err
		}
		c.writtenBytes += int64(n)
	}

	// 每段写完后检查是否需要轮转
	return c.rotateIfNeeded()
}

func (c *SlowlogReport) loadCommentHeadTimeFromDisk() error {
	val, err := loadStringFromDisk(c.commentHeadTimeRegFilePath)
	if err != nil {
		return err
	}
	c.commentHeadTime = val
	// 加载时同步缓存 timestamp
	if val != "" {
		ts, err := parseTimeToTimestamp(val)
		if err == nil {
			c.commentHeadTs = ts
			c.commentHeadTsCached = true
		}
	}
	return nil
}

// persistState 将内存中的状态统一持久化到磁盘
// 仅在所有段处理成功后调用，保证状态文件与 slowlog 输出一致
func (c *SlowlogReport) persistState() error {
	if c.currentDB != "" {
		if err := os.WriteFile(c.currentDBRegFilePath, []byte(c.currentDB), 0644); err != nil {
			return err
		}
	}
	if c.commentHeadTime != "" {
		if err := os.WriteFile(c.commentHeadTimeRegFilePath, []byte(c.commentHeadTime), 0644); err != nil {
			return err
		}
	}
	return nil
}

func (c *SlowlogReport) Name() string {
	return reporterName
}

func NewSlowlogReport(db *sqlx.DB) *SlowlogReport {
	r := &SlowlogReport{
		// SlowLogFile: "",
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
	c := NewSlowlogReport(cc.MySqlDB)
	opts := cc.GetCustomOptions(reporterName)
	if len(opts) > 0 {
		if err := mapstructure.Decode(opts, c); err != nil {
			slog.Warn("decode custom options failed, use defaults", slog.String("error", err.Error()))
		}
	}
	return c
}

func RegisterSlowlogRewrite() (string, monitoriteminterface.MonitorItemConstructorFuncType) {
	return reporterName, NewSlowlogReportItem
}

// parseTimeToTimestamp 将三种不同格式的时间字符串转换为时间戳
// 格式1: "260127  2:05:24" (YYMMDD  H:MM:SS，中间可能有多个空格)
// 格式2: "2026-01-27T01:58:55.960323+08:00" (RFC3339Nano 带时区)
// 格式3: "2026-01-24T19:03:14.039913Z" (RFC3339Nano UTC时区)
func parseTimeToTimestamp(timeStr string) (int64, error) {
	// 根据格式特征快速分发解析路径，避免多次失败试探
	if strings.Contains(timeStr, "T") {
		// RFC3339Nano 格式（包含纯 RFC3339）
		t, err := time.Parse(time.RFC3339Nano, timeStr)
		if err == nil {
			return t.Unix(), nil
		}
		// 回退尝试不带纳秒的 RFC3339
		t, err = time.Parse(time.RFC3339, timeStr)
		if err == nil {
			return t.Unix(), nil
		}
		return 0, fmt.Errorf("无法解析时间格式: %s", timeStr)
	}

	// 旧格式: "260127  2:05:24" (YYMMDD + 多个空格 + H:MM:SS)
	// 用 strings.Fields 规整空格，替代正则
	parts := strings.Fields(timeStr)
	if len(parts) == 2 {
		normalized := parts[0] + " " + parts[1]
		t, err := time.ParseInLocation("060102 15:04:05", normalized, time.Local)
		if err == nil {
			return t.Unix(), nil
		}
	}

	return 0, fmt.Errorf("无法解析时间格式: %s", timeStr)
}

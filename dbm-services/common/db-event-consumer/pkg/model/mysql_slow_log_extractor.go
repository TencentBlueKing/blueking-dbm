package model

import (
	"regexp"
	"strconv"
	"strings"
	"time"

	"dbm-services/mysql/slow-query-parser-service/pkg/mysql"
)

// 以下正则对齐 percona/go-mysql log/slow/parser.go

// slowLogTimeRe 匹配旧格式时间行: # Time: 060102 15:04:05
var slowLogTimeRe = regexp.MustCompile(`Time: (\S+\s{1,2}\S+)`)

// slowLogTimeNewRe 匹配新格式时间行: # Time: 2006-01-02T15:04:05.000000Z
var slowLogTimeNewRe = regexp.MustCompile(`Time:\s+(\d{4}-\d{2}-\d{2}\S+)`)

// slowLogUserRe 匹配 User@Host 行，提取用户名和客户端 IP
// 示例: # User@Host: igame[igame] @  [1.2.3.4]  Id: 86728544
var slowLogUserRe = regexp.MustCompile(`User@Host: ([^\[]+|\[[^[]+\]).*?@ (\S*) \[(.*)\]`)

// slowLogSchemaRe 匹配 Schema 行
// 示例: # Schema: mydb   Last_errno: 0  Killed: 0
var slowLogSchemaRe = regexp.MustCompile(`Schema: +(.*?) +Last_errno:`)

// slowLogHeaderRe 判断是否是 header 行（以 # 开头且后跟大写字母）
var slowLogHeaderRe = regexp.MustCompile(`^#\s+[A-Z]`)

// slowLogMetricsRe 匹配 key: value 格式的指标
var slowLogMetricsRe = regexp.MustCompile(`(\w+): (\S+|\z)`)

// slowLogAdminRe 匹配 admin command 行
var slowLogAdminRe = regexp.MustCompile(`command: (.+)`)

// slowLogSetRe 匹配需要跳过的 SET 语句
var slowLogSetRe = regexp.MustCompile(`^SET (?:last_insert_id|insert_id|timestamp)`)

// slowLogUseRe 匹配 USE db 语句
var slowLogUseRe = regexp.MustCompile(`^(?i)use `)

// parseOneSlowLog 解析一段慢日志文本（单条慢查询），返回 SlowLog 结构体。
// 对齐 https://github.com/percona/go-mysql/blob/main/log/slow/parser.go 的全部 header 解析逻辑。
//
// data 示例:
//
//	# Time: 2025-03-10T12:57:05.123456Z
//	# User@Host: igame[igame] @  [1.2.3.4]  Id: 86728544
//	# Schema: mydb  Last_errno: 0  Killed: 0
//	# Query_time: 1.216848  Lock_time: 0.000076  Rows_sent: 20  Rows_examined: 357580  Rows_affected: 0
//	# Bytes_sent: 3818
//	SET timestamp=1773131225;
//	select * from t where id=1;
func parseOneSlowLog(data string, digest bool) (*SlowLog, error) {
	result := &SlowLog{}

	lines := strings.Split(data, "\n")
	var queryLines []string
	inHeader := false
	inQuery := false

	for _, rawLine := range lines {
		lineLen := len(rawLine)
		if lineLen == 0 {
			continue
		}
		line := strings.TrimRight(rawLine, "\r")

		// 过滤 mysqld 启动 meta 行（对齐 percona parser）
		if lineLen >= 20 && ((line[0] == '/' && strings.HasSuffix(line, "with:")) ||
			strings.HasPrefix(line, "Time ") ||
			strings.HasPrefix(line, "Tcp ") ||
			strings.HasPrefix(line, "TCP ")) {
			continue
		}

		// 过滤空注释行和 MariaDB explain 行
		if line == "#" || strings.HasPrefix(line, "# explain:") {
			continue
		}

		if inHeader {
			if !slowLogHeaderRe.MatchString(line) {
				// header 结束，转入 query 区域
				inHeader = false
				inQuery = true
				// 当前行已属于 query，继续走 query 逻辑
			} else {
				parseSlowLogHeader(line, result)
				continue
			}
		} else if !inQuery && slowLogHeaderRe.MatchString(line) {
			inHeader = true
			inQuery = false
			parseSlowLogHeader(line, result)
			continue
		}

		// query 区域
		if inQuery || (!inHeader && !slowLogHeaderRe.MatchString(line)) {
			// admin command 行（# admin command: xxx）
			if strings.HasPrefix(line, "# admin") {
				if m := slowLogAdminRe.FindStringSubmatch(line); len(m) == 2 {
					result.QueryCommand = "admin"
					result.QueryString = strings.TrimSuffix(m[1], ";")
					result.QueryLength = len(result.QueryString)
				}
				continue
			}
			// 下一个事件的 header 开始（data 包含多条时）
			if slowLogHeaderRe.MatchString(line) {
				break
			}
			// 跳过 SET last_insert_id / insert_id / timestamp（但提取 timestamp 值）
			if slowLogSetRe.MatchString(line) {
				// 提取 SET timestamp=xxx
				if idx := strings.Index(line, "timestamp="); idx >= 0 {
					valStr := strings.TrimRight(line[idx+len("timestamp="):], ";")
					if v, err := strconv.ParseUint(valStr, 10, 64); err == nil {
						result.SqlTimestamp = uint(v)
					}
				}
				continue
			}
			// USE db 语句
			if isUse := slowLogUseRe.FindString(line); isUse != "" {
				db := strings.TrimPrefix(line, isUse)
				db = strings.TrimRight(db, ";")
				db = strings.Trim(db, "`")
				result.Schema = strings.TrimSpace(db)
				// 若还没有真正的 SQL，先把 use 语句作为 query（对齐 percona 行为）
				if len(queryLines) == 0 {
					queryLines = append(queryLines, line)
				}
				continue
			}
			// 真正的 SQL 行：若之前只有 use 语句，替换掉它
			if len(queryLines) == 1 && slowLogUseRe.MatchString(queryLines[0]) {
				queryLines = []string{line}
			} else {
				queryLines = append(queryLines, line)
			}
		}
	}

	// 拼接 SQL
	result.QueryString = strings.TrimSuffix(strings.Join(queryLines, "\n"), ";")
	result.QueryLength = len(result.QueryString)

	if digest {
		digestResp, err := mysql.AnalyzeSql(result.Schema, result.QueryString)
		if err != nil {
			return nil, err
		}
		result.QueryDigestMd5 = digestResp.QueryDigestMd5
		result.QueryDigestText = digestResp.QueryDigestText
		result.QueryCommand = digestResp.Command
		result.TableNames = digestResp.TableReferences.String()
		result.QueryDbName = digestResp.DbName
		result.QueryString = digestResp.QueryString // 已格式化
	}
	return result, nil
}

// parseSlowLogHeader 解析单行 header，将结果写入 result。
// 对齐 percona SlowLogParser.parseHeader 逻辑。
func parseSlowLogHeader(line string, result *SlowLog) {
	switch {
	case strings.HasPrefix(line, "# Time"):
		// 旧格式: # Time: 060102 15:04:05
		if m := slowLogTimeRe.FindStringSubmatch(line); len(m) == 2 {
			if ts, err := time.ParseInLocation("060102 15:04:05", m[1], time.Local); err == nil {
				result.SqlTimestamp = uint(ts.Unix())
			}
		} else if m = slowLogTimeNewRe.FindStringSubmatch(line); len(m) == 2 {
			// 新格式: # Time: 2006-01-02T15:04:05.000000Z
			if ts, err := time.Parse(time.RFC3339Nano, m[1]); err == nil {
				result.SqlTimestamp = uint(ts.Unix())
			}
		}
		// # Time 行有时也包含 User@Host（bad format），一并解析
		if slowLogUserRe.MatchString(line) {
			parseSlowLogUser(line, result)
		}

	case strings.HasPrefix(line, "# User"):
		parseSlowLogUser(line, result)

	case strings.HasPrefix(line, "# admin"):
		// admin command 出现在 header 区域时
		if m := slowLogAdminRe.FindStringSubmatch(line); len(m) == 2 {
			result.QueryCommand = "admin"
			result.QueryString = strings.TrimSuffix(m[1], ";")
			result.QueryLength = len(result.QueryString)
		}

	default:
		// Schema 行
		if submatch := slowLogSchemaRe.FindStringSubmatch(line); len(submatch) == 2 {
			if schemaName := strings.TrimSpace(submatch[1]); schemaName != "" {
				result.Schema = schemaName
			}
		}

		// 通用 key: value 指标解析（对齐 percona metricsRe 逻辑）
		for _, smv := range slowLogMetricsRe.FindAllStringSubmatch(line, -1) {
			key, val := smv[1], smv[2]
			switch {
			case strings.HasSuffix(key, "_time") || strings.HasSuffix(key, "_wait"):
				// 浮点时间指标
				v, _ := strconv.ParseFloat(val, 64)
				switch key {
				case "Query_time":
					result.QueryTime = float32(v)
				case "Lock_time":
					result.LockTime = float32(v)
				case "Query_start_ts":
					result.QueryStartTs = uint(v)
				}
			case val == "Yes" || val == "No":
				// 布尔指标，暂不存储
			case key == "Schema" && val != "":
				result.Schema = val
			case key == "Db_name" && val != "":
				result.DbName = val
			default:
				// 整数指标
				v, _ := strconv.ParseUint(val, 10, 64)
				switch key {
				case "Rows_examined":
					result.RowsExamined = int(v)
				case "Rows_sent":
					result.RowsSent = int(v)
				case "Session_id":
					result.SessionId = int64(v)
				}
			}
		}
		if result.Schema == "" {
			result.Schema = result.DbName
		}
	}
}

// parseSlowLogUser 从 User@Host 行提取用户名和客户端 IP
func parseSlowLogUser(line string, result *SlowLog) {
	m := slowLogUserRe.FindStringSubmatch(line)
	if len(m) < 3 {
		return
	}
	// m[1] 可能是 "igame[igame] " 或 "[igame]"，取 [ 之前的部分作为用户名
	user := strings.TrimSpace(m[1])
	if idx := strings.Index(user, "["); idx >= 0 {
		user = strings.TrimSpace(user[:idx])
	}
	result.Username = user
	// m[2] 是 hostname（可能为空），m[3] 是 IP
	clientHost := strings.TrimSpace(m[2])
	if clientHost == "" {
		clientHost = strings.TrimSpace(m[3])
	}
	result.ClientHost = clientHost
}

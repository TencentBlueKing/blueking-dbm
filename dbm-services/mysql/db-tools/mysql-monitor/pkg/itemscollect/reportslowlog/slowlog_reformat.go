package reportslowlog

import (
	"bytes"
	"encoding/json"
	"strconv"
	"strings"
)

// ReformatSeg 将段的注释元数据格式化为 JSON header + SQL body
// 输出格式:
//
//	# {"db_name":"xxx","query_start_ts":"123","time":"...","query_time":"17.5",...}
//	SQL body
//
// 注释行中所有 KEY: VALUE 对都会被提取进 dict，然后按重写逻辑补充新字段（db_name, query_start_ts, session_id）
// 返回格式化后的完整字符串（含末尾换行）
func (c *SlowlogReport) ReformatSeg() (string, error) {
	f := &c.segF

	// 更新内存中的 currentDB
	if f.usedDB != "" {
		c.currentDB = f.usedDB
	}

	// 更新内存中的 commentHeadTime
	if f.hasTime {
		c.commentHeadTime = f.timeStr
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
			queryStartTs = f.setTs
			hasValidQueryStartTs = true
		}
	}

	// 确定 DB_name
	schemaToWrite := c.currentDB
	if f.schema != "" {
		schemaToWrite = f.schema
	}

	// 通用解析：从注释行中提取所有 KEY: VALUE 对
	meta := make(map[string]string, 16)
	bodyStart := c.firstBodyLineIdx
	if bodyStart < 0 {
		bodyStart = len(c.segRanges)
	}
	for i := 0; i < bodyStart; i++ {
		r := c.segRanges[i]
		line := strings.TrimLeft(string(c.segBuf[r.offset:r.offset+r.length]), " \t")
		if len(line) < 2 || line[0] != '#' {
			continue
		}
		// 去掉 "# " 前缀
		content := strings.TrimLeft(line[1:], " \t")
		if len(content) == 0 {
			continue
		}
		// 特殊行：# Time: 后面整体作为值（可能含空格和特殊字符）
		if strings.HasPrefix(content, "Time:") {
			val := strings.TrimSpace(content[5:])
			if val != "" {
				meta["Time"] = val
			}
			continue
		}
		// 特殊行：# User@Host: 后面整体作为值（含用户名、IP等复杂格式）
		if strings.HasPrefix(content, "User@Host:") {
			val := strings.TrimSpace(content[10:])
			if val != "" {
				meta["User@Host"] = val
			}
			continue
		}
		// 通用解析：按空格分隔的 KEY: VALUE 对
		// 格式如: "Query_time: 17.5  Lock_time: 0.0  Rows_sent: 12"
		parseKeyValuePairs(content, meta)
	}

	// 按重写逻辑补充新字段（覆盖或新增）
	if schemaToWrite != "" {
		meta["db_name"] = schemaToWrite
	}
	if hasValidQueryStartTs {
		meta["query_start_ts"] = strconv.FormatInt(queryStartTs, 10)
	}
	if f.sessionId != "" {
		meta["session_id"] = f.sessionId
	}
	if f.hasSetTs {
		meta["set_timestamp"] = strconv.FormatInt(f.setTs, 10)
	}

	// 提取 SQL body
	// - firstBodyLineIdx 之前的行全部是注释/元数据，跳过
	// - firstBodyLineIdx 及之后的行属于 SQL body，仅跳过 use xxx; 和 SET timestamp= 行
	//   其余行（包括以 # 开头的 SQL 内容行）全部保留
	var sqlBody strings.Builder
	for i := bodyStart; i < len(c.segRanges); i++ {
		r := c.segRanges[i]
		line := c.segBuf[r.offset : r.offset+r.length]
		if len(line) == 0 {
			continue
		}
		trimmedLine := bytes.TrimLeft(line, " \t")
		// 跳过 use xxx; 行
		if isUseDBLine(trimmedLine) {
			continue
		}
		// 跳过 SET timestamp= 行
		if isSetTimestampLine(trimmedLine) {
			continue
		}
		// SQL body 行（包括以 # 开头的合法 SQL 内容）
		if sqlBody.Len() > 0 {
			sqlBody.WriteByte('\n')
		}
		sqlBody.Write(line)
	}

	// 序列化 JSON
	jsonBytes, err := json.Marshal(meta)
	if err != nil {
		return "", err
	}

	// 组装最终输出: # {json}\nsql\n
	var out strings.Builder
	out.Grow(2 + len(jsonBytes) + 1 + sqlBody.Len() + 1)
	out.WriteString("# ")
	out.Write(jsonBytes)
	out.WriteByte('\n')
	out.WriteString(sqlBody.String())
	out.WriteByte('\n')

	return out.String(), nil
}

// parseKeyValuePairs 从注释行内容中解析所有 KEY: VALUE 对
// 格式: "Query_time: 17.5  Lock_time: 0.0  Rows_sent: 12"
// 规则: 以 "XXX:" 为 key（冒号紧跟在单词后），冒号后的空格分隔值直到下一个 key 或行尾
func parseKeyValuePairs(content string, meta map[string]string) {
	// 按空格分割为 tokens
	tokens := strings.Fields(content)
	if len(tokens) == 0 {
		return
	}

	var currentKey string
	var currentVals []string

	for _, tok := range tokens {
		if strings.HasSuffix(tok, ":") && len(tok) > 1 {
			// 遇到新 key：先保存上一个 key-value
			if currentKey != "" && len(currentVals) > 0 {
				meta[currentKey] = strings.Join(currentVals, " ")
			} else if currentKey != "" {
				// key 存在但无值（如 "Schema:" 后面紧跟下一个 key）
				meta[currentKey] = ""
			}
			currentKey = tok[:len(tok)-1] // 去掉末尾冒号
			currentVals = currentVals[:0]
		} else {
			// 当前 token 是值的一部分
			if currentKey != "" {
				currentVals = append(currentVals, tok)
			}
			// 如果还没遇到 key，忽略（不应该发生在正常 slowlog 中）
		}
	}
	// 保存最后一个 key-value
	if currentKey != "" {
		if len(currentVals) > 0 {
			meta[currentKey] = strings.Join(currentVals, " ")
		} else {
			meta[currentKey] = ""
		}
	}
}

// ReformatSegToWriter 将段的注释元数据格式化为 JSON header + SQL body，直接写入 writer
// 与 rewriteSeg 类似，但输出格式为 # {json}\nsql body\n
func (c *SlowlogReport) ReformatSegToWriter() error {
	result, err := c.ReformatSeg()
	if err != nil {
		return err
	}

	n, err := c.writer.WriteString(result)
	if err != nil {
		return err
	}
	c.writtenBytes += int64(n)

	return c.rotateIfNeeded()
}

// isUseDBLine 判断行是否为 use xxx; 语句
func isUseDBLine(line []byte) bool {
	if len(line) < 4 {
		return false
	}
	// 大小写不敏感检查 "use " 前缀
	if (line[0] == 'u' || line[0] == 'U') &&
		(line[1] == 's' || line[1] == 'S') &&
		(line[2] == 'e' || line[2] == 'E') &&
		(line[3] == ' ' || line[3] == '\t') {
		return true
	}
	return false
}

// isSetTimestampLine 判断行是否为 SET timestamp=xxx; 语句
func isSetTimestampLine(line []byte) bool {
	if len(line) < len(SetTimestampPrefix) {
		return false
	}
	// 检查常见前缀
	if len(line) >= len(SetTimestampPrefix) {
		match := true
		prefix := SetTimestampPrefix
		for i := 0; i < len(prefix); i++ {
			if line[i] != prefix[i] {
				match = false
				break
			}
		}
		if match {
			return true
		}
	}
	// 检查大写前缀
	if len(line) >= len(SetTimestampPrefixUpper) {
		match := true
		prefix := SetTimestampPrefixUpper
		for i := 0; i < len(prefix); i++ {
			if line[i] != prefix[i] {
				match = false
				break
			}
		}
		if match {
			return true
		}
	}
	return false
}

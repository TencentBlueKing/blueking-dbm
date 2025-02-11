package redisreply

import (
	"encoding/json"
	"strconv"
	"strings"
)

// FormatReplyRaw  redis-cli.c cliFormatReplyRaw
// 无法区分string和status
func FormatReplyRaw(isStatusOut bool, cmdRet interface{}, prefix string) string {
	var strBuilder strings.Builder
	switch v := cmdRet.(type) {
	case int64:
		strBuilder.WriteString(strconv.FormatInt(v, 10))
		strBuilder.WriteString("\n")

	case string:
		if isStatusOut {
			strBuilder.WriteString(v)
		} else {
			strBuilder.WriteString(catrepr(v))
		}
		strBuilder.WriteString("\n")
	case []string:
		if len(v) == 0 {
			strBuilder.WriteString("\n")
		} else {
			for _, item := range v {
				tmp := FormatReplyRaw(isStatusOut, item, "")
				strBuilder.WriteString(tmp)
			}
		}

	case []interface{}:
		if len(v) == 0 {
			strBuilder.WriteString("\n")
		} else {
			for _, item := range v {
				tmp := FormatReplyRaw(isStatusOut, item, "")
				strBuilder.WriteString(tmp)
			}
		}

	default:
		byte01, _ := json.Marshal(cmdRet)
		strBuilder.WriteString("(unknown format)")
		strBuilder.WriteString(string(byte01))
		strBuilder.WriteString("\n")
	}
	return strBuilder.String()
}

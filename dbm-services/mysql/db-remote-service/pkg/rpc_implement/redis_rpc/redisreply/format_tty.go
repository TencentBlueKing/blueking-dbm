package redisreply

import (
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
)

func isPrint(c byte) bool {
	return c >= 0x20 && c <= 0x7e
}
func printString(p string, raw bool) string {
	if raw {
		return catrepr(p)
	}
	var strBuilder strings.Builder
	// strBuilder.WriteString("\"")
	for _, c := range []byte(p) {
		// fmt.Printf("idx %d c: %c\n", i, c)
		switch c {
		case '\\', '"':
			strBuilder.WriteString(fmt.Sprintf("\\%c", c))
		case '\n':
			strBuilder.WriteString("\\n")
		case '\r':
			strBuilder.WriteString("\\r")
		case '\t':
			strBuilder.WriteString("\\t")
		case '\a':
			strBuilder.WriteString("\\a")
		case '\b':
			strBuilder.WriteString("\\b")
		default:
			if isPrint(c) {
				strBuilder.WriteByte(c)
			} else {
				strBuilder.WriteString(fmt.Sprintf("\\x%02x", c))
			}
		}
	}
	// strBuilder.WriteString("\"")
	return fmt.Sprintf(`"%s"`, strBuilder.String())
}

func catrepr(s string) string {
	return fmt.Sprintf(`"%s"`, s)
}

func getCharWidth(i int) int {
	w := 0
	for {
		w++
		i /= 10
		if i == 0 {
			break
		}
	}
	return w
}

// FormatReplyTTY
// 无法区分string和status
// status 有 OK, PONG 等值.
// raw:true  输出utf8字符串
// raw:false 输出十六进制值
func FormatReplyTTY(isStatusOut bool, cmdRet interface{}, prefix string, raw bool) string {
	var strBuilder strings.Builder
	switch v := cmdRet.(type) {
	case int64:
		strBuilder.WriteString("(integer) ")
		strBuilder.WriteString(strconv.FormatInt(v, 10))
		strBuilder.WriteString("\n")

	case string:
		if isStatusOut {
			strBuilder.WriteString(v)
		} else {
			strBuilder.WriteString(printString(v, raw))
		}
		strBuilder.WriteString("\n")
	case []string:
		if len(v) == 0 {
			strBuilder.WriteString("(empty list or set)\n")
		} else {
			// 获得宽度
			charWidth := getCharWidth(len(v))
			_prefixfmt := fmt.Sprintf("%%%dd) ", charWidth)
			_prefix := strings.Repeat(" ", charWidth+2)
			for i, item := range v {
				// item = printString(item)
				if i == 0 {
					strBuilder.WriteString(fmt.Sprintf(_prefixfmt, i+1))
					strBuilder.WriteString(FormatReplyTTY(isStatusOut, item, _prefix, raw))
				} else {
					strBuilder.WriteString(prefix)
					strBuilder.WriteString(fmt.Sprintf(_prefixfmt, i+1))
					strBuilder.WriteString(FormatReplyTTY(isStatusOut, item, _prefix, raw))
				}
			}
		}

	case []interface{}:
		if len(v) == 0 {
			strBuilder.WriteString("(empty list or set)\n")
		} else {
			// 获得宽度
			charWidth := getCharWidth(len(v))
			_prefixfmt := fmt.Sprintf("%%%dd) ", charWidth)
			_prefix := strings.Repeat(" ", charWidth+2)
			for i, item := range v {
				if i == 0 {
					strBuilder.WriteString(fmt.Sprintf(_prefixfmt, i+1))
					strBuilder.WriteString(FormatReplyTTY(isStatusOut, item, _prefix+prefix, raw))
				} else {
					strBuilder.WriteString(prefix)
					strBuilder.WriteString(fmt.Sprintf(_prefixfmt, i+1))
					strBuilder.WriteString(FormatReplyTTY(isStatusOut, item, _prefix+prefix, raw))
				}
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

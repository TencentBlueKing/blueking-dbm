package redis_rpc

import (
	"context"
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
	"time"

	"github.com/go-redis/redis/v8"
	"github.com/pkg/errors"
)

// RedisCli Do command(auto switch db)
// AUTH, PING, SET -> 返回 isStatusCmd
func RedisCli(address, redisPass, cmd string, dbNum int) (interface{}, error) {
	conn, err := NewRedisClientWithTimeout(address, redisPass, dbNum, time.Second*2)
	if err != nil {
		return nil, errors.Wrap(err, fmt.Sprintf("connect to %s failed", address))
	}
	cmdFields := strings.Fields(cmd)
	var dstCmds []interface{}
	for _, v := range cmdFields {
		dstCmds = append(dstCmds, v)
	}
	cmder := conn.InstanceClient.Do(context.TODO(), dstCmds...)
	if ret, err := cmder.Result(); err != nil {
		if errors.Is(err, redis.Nil) {
			return "(nil)\n", nil
		} else {
			return "(error) " + err.Error() + "\n", nil
		}
	} else {
		return cliFormatReplyTTY(isStatusCmd(cmdFields[0]), ret, ""), nil
	}

}

// cliFormatReplyTTY 以redis-cli的方式格式化输出
func cliFormatReplyTTY(isStatusOut bool, cmdRet interface{}, prefix string) string {
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
			strBuilder.WriteString(fmt.Sprintf(`"%s"`, v))
		}
		strBuilder.WriteString("\n")
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
					strBuilder.WriteString(cliFormatReplyTTY(isStatusOut, item, _prefix+prefix))
				} else {
					strBuilder.WriteString(prefix)
					strBuilder.WriteString(fmt.Sprintf(_prefixfmt, i+1))
					strBuilder.WriteString(cliFormatReplyTTY(isStatusOut, item, _prefix+prefix))
				}
			}
		}
	default:
		o, _ := json.Marshal(cmdRet)
		strBuilder.WriteString(fmt.Sprintf("(unknown format) %T, value: %q", cmdRet, o))
		strBuilder.WriteString("\n")
	}
	return strBuilder.String()
}

// getCharWidth 位数
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

// isStatusCmd 返回结果为状态类输出的命令，这里只需要处理只读类的几个.
// 完整的列表见这里: grep StatusCmd github.com/go-redis/redis/v8@v8.11.5/commands.go
func isStatusCmd(cmd string) bool {
	var readOnlyStatusCmdList = []string{"select", "ping", "quit", "type", "set", "setex", "mset", "lset", "lrem"}
	for _, v := range readOnlyStatusCmdList {
		if strings.EqualFold(cmd, v) {
			return true
		}
	}
	return false
}

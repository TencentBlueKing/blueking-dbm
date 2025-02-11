package redis_rpc

import (
	"context"
	"dbm-services/mysql/db-remote-service/pkg/rpc_implement/redis_rpc/redisreply"
	"fmt"
	"strings"
	"time"

	"github.com/go-redis/redis/v8"
	"github.com/pkg/errors"
)

// isStatusCmd 返回结果为状态类输出的命令，这里只需要处理只读类的几个.
//
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

// doCommand Do command(auto switch db)
// AUTH, PING, SET -> 返回 isStatusCmd
func doCommand(db *redis.Client, cmdArgv []string) (bool, interface{}, error) {
	var dstCmds []interface{}
	for _, v := range cmdArgv {
		dstCmds = append(dstCmds, v)
	}
	cmd := db.Do(context.TODO(), dstCmds...)
	ret, err := cmd.Result()
	return isStatusCmd(cmdArgv[0]), ret, err
}

// RedisCli Do command(auto switch db)
// AUTH, PING, SET -> 返回 isStatusCmd
// rawMode 为 true : 输出utf8字符串; 为 false: 输出十六进制值
func RedisCli(address, redisPass, cmd string, dbNum int, rawMode bool) (interface{}, error) {
	conn, err := NewRedisClientWithTimeout(address, redisPass, dbNum, time.Second*2)
	if err != nil {
		return nil, errors.Wrap(err, fmt.Sprintf("connect to %s failed", address))
	}
	cmdFields := strings.Fields(cmd)

	isStatusCmd, cmdRet, err := doCommand(conn.InstanceClient, cmdFields)
	if err != nil {
		if errors.Is(err, redis.Nil) {
			return "(nil)\n", nil
		} else {
			return "(error) " + err.Error() + "\n", nil
		}
	}
	return redisreply.FormatReplyTTY(isStatusCmd, cmdRet, "", rawMode), nil
}

// Package redis_rpc TODO
package redis_rpc

import (
	"fmt"
	"log/slog"
	"strings"

	"github.com/gin-gonic/gin"
)

// RedisRPCEmbed redis 实现
type RedisRPCEmbed struct {
}

// WebConsoleMode webconsole mode, using redis-cli to execute command
const WebConsoleMode = "webconsole"

// NewRedisRPCEmbed TODO
func NewRedisRPCEmbed() *RedisRPCEmbed {
	return &RedisRPCEmbed{}
}

// IsAdminCommand 是否为admin类的指令
// 也许应该放开cluster nodes, info 之类.
func (r *RedisRPCEmbed) IsAdminCommand(cmdArgs []string) bool {
	if len(cmdArgs) == 0 {
		return false
	}
	cmd := strings.ToLower(cmdArgs[0])
	if _, ok := RedisCommandTable[cmd]; !ok {
		return false
	}
	return strings.Contains(RedisCommandTable[cmd].Sflags, adminFlag)
}

// IsQueryCommand redis 解析命令
func (r *RedisRPCEmbed) IsQueryCommand(cmdArgs []string) bool {
	if len(cmdArgs) == 0 {
		return false
	}
	cmd := strings.ToLower(cmdArgs[0])
	if len(cmdArgs) >= 2 {
		if cmdArgs[0] == "cluster" && cmdArgs[1] == "nodes" {
			return true
		}
		if cmdArgs[0] == "cluster" && cmdArgs[1] == "info" {
			return true
		}
		if cmdArgs[0] == "cluster" && cmdArgs[1] == "slots" {
			return true
		}
		if cmdArgs[0] == "cluster" && cmdArgs[1] == "keyslot" {
			return true
		}
		if cmdArgs[0] == "cluster" && cmdArgs[1] == "getkeysinslot" {
			return true
		}
		if cmdArgs[0] == "cluster" && cmdArgs[1] == "countkeysinslot" {
			return true
		}
		if cmdArgs[0] == "getserver" {
			return true
		}
		if (cmdArgs[0] == "confxx" || cmdArgs[0] == "config") && cmdArgs[1] == "get" {
			return true
		}
	}
	if _, ok := RedisCommandTable[cmd]; !ok {
		return false
	}
	return strings.Contains(RedisCommandTable[cmd].Sflags, readOnlyFlag)
}

// IsExecuteCommand 不允许执行写命令
func (r *RedisRPCEmbed) IsExecuteCommand() bool {
	return false
}

// DoCommand 执行redis命令
func (r *RedisRPCEmbed) DoCommand(c *gin.Context) {
	// 获取参数
	var param RedisQueryParams
	err := c.BindJSON(&param)
	if err != nil {
		slog.Error("RedisRPCEmbed bind json", err)
		SendResponse(c, 1, err.Error(), nil)
		return
	}
	slog.Info("RedisRPCEmbed request data", slog.String("param", param.StringWithoutPasswd()))

	// WebConsoleMode 使用 DoCommandForWebConsole
	if param.ClientType == WebConsoleMode {
		r.DoCommandForWebConsole(c, &param)
		return
	}

	// 格式化并检查命令
	formatCmd, err := FormatName(param.Command)
	if err != nil {
		slog.Error("RedisRPCEmbed format name", err, slog.String("command", param.Command))
		SendResponse(c, 1, err.Error(), nil)
		return
	}
	cmdArgs := strings.Fields(formatCmd)
	if !r.IsQueryCommand(cmdArgs) {
		slog.Error("RedisRPCEmbed is query command, not support", slog.String("command", formatCmd))
		SendResponse(c, 1, fmt.Sprintf("non-support redis command:'%s'", formatCmd), nil)
		return
	}

	genErrInfo := func(isString bool, valueSize, maxLen int) string {
		name := "Member Count"
		if isString {
			name = "Value Size"
		}
		return fmt.Sprintf("ERR: 该查询返回的%s为%d，超过了阀值%d。\n", name, valueSize, maxLen)
	}

	// 执行命令
	var respData []CmdResult
	var maxLen int
	password := param.Password
	for _, address := range param.Addresses {
		valueSize, isString, err := GetValueSize(address, password, formatCmd, param.DbNum)
		if isString {
			maxLen = 1 * 1024 * 1024
		} else {
			maxLen = 1000
		}
		if err != nil {
			slog.Error("RedisRPCEmbed get value size", err, slog.String("command", formatCmd))
			SendResponse(c, 1, err.Error(), nil)
			return
		} else if valueSize > maxLen {
			slog.Error("RedisRPCEmbed get value size",
				genErrInfo(isString, valueSize, maxLen),
				slog.String("command", formatCmd))
			SendResponse(c, 1, genErrInfo(isString, valueSize, maxLen), nil)
			return
		}

		var ret string
		ret, err = DoRedisCmdNew(address, password, formatCmd, param.DbNum)

		if err != nil {
			slog.Error("RedisRPCEmbed execute command", err,
				slog.String("address", address),
				slog.String("command", formatCmd),
				slog.Int("dbNum", param.DbNum))
			SendResponse(c, 1, err.Error(), nil)
			return
		}
		respData = append(respData, CmdResult{Address: address, Result: ret})
	}
	SendResponse(c, 0, "", respData)
	return
}

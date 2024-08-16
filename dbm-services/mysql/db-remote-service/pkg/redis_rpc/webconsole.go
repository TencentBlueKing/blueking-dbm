package redis_rpc

import (
	"fmt"
	"log/slog"
	"strings"

	"github.com/gin-gonic/gin"
)

// DoCommandForWebConsole
// 1. cmd语法错误时使用，使用code 0返回.
// 2. 模拟redis-cli输出格式
func (r *RedisRPCEmbed) DoCommandForWebConsole(c *gin.Context, param *RedisQueryParams) {
	// 获取参数
	respHandle := NewRespHandle(c, param)
	slog.Info("RedisRPCEmbed request data", slog.String("param", param.StringWithoutPasswd()))

	if len(param.Addresses) == 0 {
		SendResponse(c, 1, "bad param, empty Addresses", nil)
		return
	}

	// 格式化并检查命令
	formatCmd, err := FormatName(param.Command)
	if err != nil {
		respHandle.SendWarn(err.Error())
		return
	}

	cmdArgs := strings.Fields(formatCmd)
	if !r.IsQueryCommand(cmdArgs) {
		respHandle.SendWarn(webConsolenonSupportCmd(formatCmd))
		return
	}
	if r.IsAdminCommand(cmdArgs) {
		respHandle.SendWarn(webConsolenonSupportCmd(formatCmd))
		return
	}

	// 执行命令
	var respData []CmdResult
	password := param.Password
	for _, address := range param.Addresses {
		if _, _, err = GetValueSize(address, password, formatCmd, param.DbNum); err != nil {
			if strings.Contains(err.Error(), "ERR DB index is out of range") {
				respHandle.SendWarn(fmt.Sprintf("ERR DB index is out of range, db:%d", param.DbNum))
			} else {
				respHandle.SendWarn(err.Error())
			}

			return
		}

		ret, err := RedisCli(address, password, formatCmd, param.DbNum)
		if err != nil {
			slog.Error("RedisRPCEmbed execute command", err,
				slog.String("address", address),
				slog.String("command", formatCmd),
				slog.Int("dbNum", param.DbNum))
			respHandle.SendError(err.Error())
			return
		}
		respData = append(respData, CmdResult{Address: address, Result: ret})
	}
	respHandle.SendResp(respData)
	return
}

// webConsolenonSupportCmd 返回nonSupportCmd字样
func webConsolenonSupportCmd(cmd string) string {
	return fmt.Sprintf("commands not supported by webconsole:%q", cmd)
}

func buildErrorResp(param *RedisQueryParams, errMsg string) []CmdResult {
	ret := make([]CmdResult, 0)
	for _, addr := range param.Addresses {
		ret = append(ret, CmdResult{
			Address: addr,
			Result:  fmt.Sprintf("(error) %s", errMsg),
		})
	}
	return ret
}

type RespHandle struct {
	c     *gin.Context
	param *RedisQueryParams
}

// SendResp send a resp with code 0
func (r *RespHandle) SendResp(data []CmdResult) {
	SendResponse(r.c, 0, "", data)
}

// SendWarn send errmsg with prefix (error)
func (r *RespHandle) SendWarn(errMsg string) {
	data := buildErrorResp(r.param, fmt.Sprintf("webconsole error: %s", errMsg))
	r.SendResp(data)
}

// SendError send a resp with code 1
func (r *RespHandle) SendError(errMsg string) {
	SendResponse(r.c, 1, errMsg, nil)
}

func NewRespHandle(c *gin.Context, param *RedisQueryParams) *RespHandle {
	return &RespHandle{
		c:     c,
		param: param,
	}
}

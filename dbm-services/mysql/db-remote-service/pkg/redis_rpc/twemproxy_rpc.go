package redis_rpc

import (
	"fmt"
	"log/slog"

	"github.com/gin-gonic/gin"
)

// TwemproxyRPCEmbed TODO
// RedisRPCEmbed redis 实现
type TwemproxyRPCEmbed struct {
}

// NewTwemproxyRPCEmbed TODO
func NewTwemproxyRPCEmbed() *TwemproxyRPCEmbed {
	return &TwemproxyRPCEmbed{}
}

// IsProxyQueryCommand proxy命令 需要走nc协议。暂时先不限制，都可以执行
func (r *TwemproxyRPCEmbed) IsProxyQueryCommand(cmd string) bool {
	return true
}

// DoCommand 执行redis命令
func (r *TwemproxyRPCEmbed) DoCommand(c *gin.Context) {
	// 获取参数
	var param RedisQueryParams
	err := c.BindJSON(&param)
	if err != nil {
		slog.Error("TwemproxyRPCEmbed bind json", err)
		SendResponse(c, 1, err.Error(), nil)
		return
	}

	slog.Info("TwemproxyRPCEmbed request data", slog.String("param", param.StringWithoutPasswd()))

	// 格式化并检查命令
	formatCmd, err := FormatName(param.Command)
	if err != nil {
		slog.Error("TwemproxyRPCEmbed format name", err, slog.String("command", param.Command))
		SendResponse(c, 1, err.Error(), nil)
		return
	}
	if !r.IsProxyQueryCommand(formatCmd) {
		slog.Error("TwemproxyRPCEmbed isProxyQueryCommand, not support", slog.String("cmdName", formatCmd))
		SendResponse(c, 1, fmt.Sprintf("non-support twemproxy admin command:'%s'", formatCmd), nil)
		return
	}

	// 执行命令
	var respData []CmdResult
	for _, address := range param.Addresses {
		ret, err := TcpClient01(address, formatCmd)
		if err != nil {
			slog.Error("TwemproxyRPCEmbed execute command", err,
				slog.String("address", address),
				slog.String("command", formatCmd))
			SendResponse(c, 1, err.Error(), nil)
			return
		}

		respData = append(respData, CmdResult{Address: address, Result: ret})
	}
	SendResponse(c, 0, "", respData)
	return
}

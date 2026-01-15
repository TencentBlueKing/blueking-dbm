// Package proxycmd TODO
/*
 * @Description: dbactuator proxy restore-proxy-whitelist 入口函数
 * 用于 Proxy 救援流程，从 Master 的 infodba_schema.proxy_user_list 表恢复白名单
 */
package proxycmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql_proxy"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// RestoreProxyWhitelistAct 从 Master 恢复 Proxy 白名单的 Act
// extend payload（与 RestoreProxyWhitelistParam 一致，支持批量目标 Proxy）
/*
{
	"master_host": "127.0.0.1",
	"master_port": 20000,
	"target_proxies": [
		{"host": "127.0.0.2", "port": 10000},
		{"host": "127.0.0.3", "port": 10000}
	]
}
*/
type RestoreProxyWhitelistAct struct {
	*subcmd.BaseOptions
	Service mysql_proxy.RestoreProxyWhitelistComp
}

// NewRestoreProxyWhitelistCommand 创建 restore-proxy-whitelist 命令
func NewRestoreProxyWhitelistCommand() *cobra.Command {
	act := RestoreProxyWhitelistAct{
		BaseOptions: subcmd.GBaseOptions,
		Service: mysql_proxy.RestoreProxyWhitelistComp{
			Params: &mysql_proxy.RestoreProxyWhitelistParam{},
		},
	}
	cmd := &cobra.Command{
		Use:   "restore-proxy-whitelist",
		Short: "restore proxy whitelist from master",
		Example: fmt.Sprintf(
			`dbactuator proxy restore-proxy-whitelist %s %s `,
			subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Service.Example()),
		),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Init 初始化
func (r *RestoreProxyWhitelistAct) Init() (err error) {
	if err = r.Deserialize(&r.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	r.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

// Validate 参数校验
func (r *RestoreProxyWhitelistAct) Validate() (err error) {
	return r.BaseOptions.Validate()
}

// Run 执行恢复白名单流程
func (r *RestoreProxyWhitelistAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "初始化连接",
			Func:    r.Service.Init,
		},
		{
			FunName: "从 Master 恢复 Proxy 白名单",
			Func:    r.Service.RestoreWhitelistFromMaster,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}

	logger.Info("restore proxy whitelist from master successfully")
	return nil
}

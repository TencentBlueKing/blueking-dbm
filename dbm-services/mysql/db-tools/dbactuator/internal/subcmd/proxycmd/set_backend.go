// Package proxycmd TODO
/*
 * @Description:  dbactuator proxy set-backend 入口函数
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

// SetBackendAct TODO
// extend payload
/*
{
    "host": "127.0.0.1",
    "port": 10000,
    "backend_host": "127.0.0.1",
    "backend_port": 20000
}
*/
type SetBackendAct struct {
	*subcmd.BaseOptions
	Service mysql_proxy.ProxySetBackendCom
}

// NewSetBackendsCommand TODO
func NewSetBackendsCommand() *cobra.Command {
	act := SetBackendAct{
		BaseOptions: subcmd.GBaseOptions,
		Service: mysql_proxy.ProxySetBackendCom{
			Params: mysql_proxy.ProxySetBackendParam{},
		},
	}
	cmd := &cobra.Command{
		Use:   "set-backend",
		Short: "proxy set backends",
		Example: fmt.Sprintf(
			`dbactuator proxy set-backend %s %s `,
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

// Init TODO
func (c *SetBackendAct) Init() (err error) {
	if err = c.Deserialize(&c.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return
}

// Validate TODO
func (c *SetBackendAct) Validate() (err error) {
	return c.BaseOptions.Validate()
}

// Run TODO
func (c *SetBackendAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    c.Service.Init,
		},
		{
			FunName: "Set backends",
			Func:    c.Service.SetBackend,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}

	logger.Info("set proxy backends successfully")
	return nil
}

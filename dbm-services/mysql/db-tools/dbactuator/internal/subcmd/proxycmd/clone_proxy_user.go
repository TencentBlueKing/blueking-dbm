// Package proxycmd TODO
/*
 * @Description:  dbactuator proxy clone_proxy_user 入口函数

 */
package proxycmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql_proxy"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

// CloneProxyUserAct TODO
// extend payload
/*
 {
		 "source_proxy_host": "1.1.1.1",
		 "source_proxy_port"  10000,
		 "target_proxy_host"  "2.2.2.2",
		 "target_proxy_port"  10000

 }
*/
type CloneProxyUserAct struct {
	*subcmd.BaseOptions
	Service mysql_proxy.CloneProxyUserComp
}

// NewCloneProxyUserCommand TODO
func NewCloneProxyUserCommand() *cobra.Command {
	act := CloneProxyUserAct{
		BaseOptions: subcmd.GBaseOptions,
		Service: mysql_proxy.CloneProxyUserComp{
			Params: &mysql_proxy.CloneProxyUserParam{},
		},
	}
	cmd := &cobra.Command{
		Use:   "clone-proxy-user",
		Short: "proxy clone user",
		Example: fmt.Sprintf(
			`dbactuator proxy clone-proxy-user %s %s `,
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
func (c *CloneProxyUserAct) Init() (err error) {
	if err = c.Deserialize(&c.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return
}

// Validate TODO
func (c *CloneProxyUserAct) Validate() (err error) {
	return c.BaseOptions.Validate()
}

// Run TODO
func (c *CloneProxyUserAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    c.Service.Init,
		},
		{
			FunName: "Clone proxy user",
			Func:    c.Service.CloneProxyUser,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}

	logger.Info("clone proxy user successfully")
	return nil
}

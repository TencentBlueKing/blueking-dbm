package mysqlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/cutover"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

// CutOverToSlaveAct TODO
type CutOverToSlaveAct struct {
	*subcmd.BaseOptions
	Service cutover.CutOverToSlaveComp
}

// NewCutOverToSlaveCommnad TODO
func NewCutOverToSlaveCommnad() *cobra.Command {
	act := CutOverToSlaveAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "set-backend-toward-slave",
		Short: "切换Proxy后端指向Slave",
		Example: fmt.Sprintf(
			`dbactuator mysql set-backend-toward-slave %s %s`,
			subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Service.Example()),
		),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			if act.RollBack {
				util.CheckErr(act.Rollback())
				return
			}
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Init TODO
func (d *CutOverToSlaveAct) Init() (err error) {
	logger.Info("CutOverToSlaveAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return
}

// Run TODO
func (d *CutOverToSlaveAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "[未切换] Init",
			Func:    d.Service.Init,
		},
		{
			FunName: "[未切换] 预检查",
			Func:    d.Service.PreCheck,
		},
		{
			FunName: "[切换中] 切换",
			Func: func() error {
				postion, err := d.Service.CutOver()
				if err != nil {
					return err
				}
				d.OutputCtx(postion)
				return nil
			},
		},
		{
			FunName: "[已切换成功] 断开同步",
			Func:    d.Service.StopAndResetSlave,
		},
		{
			FunName: "[已切换成功] 剩余操作",
			Func: func() error {
				if d.Service.Params.GrantRepl {
					if err := d.Service.GrantRepl(); err != nil {
						logger.Error("授权Repl账户失败", err.Error())
					}
				}
				if d.Service.Params.LockedSwitch {
					switchUser := d.Service.Params.Cluster.MasterIns.SwitchTmpAccount.User
					host := d.Service.Params.Host
					if err := d.Service.Params.Cluster.MasterIns.DropSwitchUser(
						fmt.Sprintf(
							"%s@%s",
							switchUser,
							host,
						),
					); err != nil {
						logger.Error("删除临时用户失败%s", err.Error())
					}
				}
				return nil
			},
		},
	}
	if err := steps.Run(); err != nil {
		logger.Error(" Run set-backend-toward-slave Failed: %s", err.Error())
		return err
	}

	logger.Info("set-backend-toward-slave successfully")
	return nil
}

// Rollback TODO
func (d *CutOverToSlaveAct) Rollback() (err error) {
	return
}

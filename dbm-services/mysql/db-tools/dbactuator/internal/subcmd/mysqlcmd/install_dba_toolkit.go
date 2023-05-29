package mysqlcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// InstallDBAToolkitAct TODO
type InstallDBAToolkitAct struct {
	*subcmd.BaseOptions
	Service mysql.InstallDBAToolkitComp
}

// CommandInstallDBAToolkit TODO
const CommandInstallDBAToolkit = "install-dbatoolkit"

// NewInstallDBAToolkitCommand godoc
//
// @Summary      部署DBA工具箱
// @Description  部署 /home/mysql/dba_toolkit，覆盖
// @Tags         mysql
// @Accept       json
// @Param        body body      mysql.InstallDBAToolkitComp  true  "short description"
// @Router       /mysql/install-dbatoolkit [post]
func NewInstallDBAToolkitCommand() *cobra.Command {
	act := InstallDBAToolkitAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   CommandInstallDBAToolkit,
		Short: "部署 rotate_binlog",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`, CommandInstallDBAToolkit,
			subcmd.CmdBaseExampleStr,
			subcmd.ToPrettyJson(act.Service.Example()),
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
func (d *InstallDBAToolkitAct) Init() (err error) {
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	return nil
}

// Run TODO
func (d *InstallDBAToolkitAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "init",
			Func:    d.Service.Init,
		},
		{
			FunName: "预检查",
			Func:    d.Service.PreCheck,
		},
		{
			FunName: "部署二进制",
			Func:    d.Service.DeployBinary,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("install dba-toolkit successfully~")
	return nil
}

// Rollback TODO
func (d *InstallDBAToolkitAct) Rollback() (err error) {
	return
}

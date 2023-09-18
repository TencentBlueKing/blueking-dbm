package tbinlogdumpercmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/tbinlogdumper"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// UnInstallTbinlogDumperAct TODO
type UnInstallTbinlogDumperAct struct {
	*subcmd.BaseOptions
	Service tbinlogdumper.UnInstallTbinlogDumperComp
}

// NewUnInstallTbinlogDumperCommand TODO
//
// @Summary      卸载 tbinlogdumper 实例
// @Description  卸载 tbinlogdumper 实例说明
// @Tags         tbinlogdumper
// @Accept       json
// @Param        body body      tbinlogdumper.UnInstallTbinlogDumperComp  true  "short description"
// @Router       /tbinlogdumper/uninstall [post]
func NewUnInstallTbinlogDumperCommand() *cobra.Command {
	act := UnInstallTbinlogDumperAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "uninstall",
		Short:   "下架tbinlogdumper",
		Example: fmt.Sprintf(`dbactuator tbinlogdumper uninstall %s`, subcmd.CmdBaseExampleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			if act.RollBack {
				return
			}
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Init TODO
func (d *UnInstallTbinlogDumperAct) Init() (err error) {
	logger.Info("UnInstallMysqlAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return d.Service.Init()
}

// Run TODO
func (d *UnInstallTbinlogDumperAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "预检查",
			Func:    d.Service.PreCheck,
		},
		{
			FunName: "停止数据库实例",
			Func:    d.Service.ShutDownMySQLD,
		},
		{
			FunName: "清理机器数据&日志目录",
			Func:    d.Service.TbinlogDumperClearDir,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("uninstall tbinlogdumper successfully")
	return nil
}

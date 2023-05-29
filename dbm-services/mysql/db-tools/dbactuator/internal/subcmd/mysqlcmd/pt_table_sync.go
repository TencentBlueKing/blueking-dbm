package mysqlcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// PtTableSync TODO
const PtTableSync = "pt-table-sync"

// PtTableSyncAct TODO
type PtTableSyncAct struct {
	*subcmd.BaseOptions
	Service mysql.PtTableSyncComp
}

// PtTableSyncCommand TODO
func PtTableSyncCommand() *cobra.Command {
	act := PtTableSyncAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   PtTableSync,
		Short: "数据修复",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`,
			PtTableSync, subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Service.Example()),
		),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Validate TODO
func (d *PtTableSyncAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init TODO
func (d *PtTableSyncAct) Init() (err error) {
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return
}

// Run TODO
func (d *PtTableSyncAct) Run() (err error) {
	// subcmd.Steps 顺序执行，某个步骤error，剩下步骤不执行
	defer d.Service.DropSyncUser()
	defer d.Service.DropTempTable()
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    d.Service.Init,
		},
		{
			FunName: "预检查",
			Func:    d.Service.Precheck,
		},
		{
			FunName: "执行pt-table-sync工具",
			Func:    d.Service.ExecPtTableSync,
		},
	}
	if err = steps.Run(); err != nil {
		return err
	}
	logger.Info("数据修复任务完成")
	return nil
}

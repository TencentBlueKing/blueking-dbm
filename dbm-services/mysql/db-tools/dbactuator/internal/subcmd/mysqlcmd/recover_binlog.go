package mysqlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/restore"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	_ "dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil" // mysqlutil TODO
	"fmt"

	"github.com/spf13/cobra"
)

// RecoverBinlogAct TODO
type RecoverBinlogAct struct {
	*subcmd.BaseOptions
	Payload restore.RecoverBinlogComp
}

// RecoverBinlogCommand godoc
//
// @Summary  导入 binlog
// @Description  通过 `mysqlbinlog xxx | mysql` 导入 binlog
// @Tags         mysql
// @Accept       json
// @Param        body body      restore.RecoverBinlogComp  true  "short description"
// @Router       /mysql/recover-binlog [post]
func RecoverBinlogCommand() *cobra.Command {
	act := RecoverBinlogAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "recover-binlog",
		Short: "导入binlog",
		Example: fmt.Sprintf(
			"dbactuator mysql recover-binlog %s %s",
			subcmd.CmdBaseExampleStr,
			subcmd.ToPrettyJson(act.Payload.Example()),
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
func (d *RecoverBinlogAct) Init() (err error) {
	if err = d.BaseOptions.Validate(); err != nil {
		return err
	}
	if err = d.Deserialize(&d.Payload.Params); err != nil {
		logger.Error("Deserialize err %s", err.Error())
		return err
	}
	d.Payload.GeneralParam = subcmd.GeneralRuntimeParam
	return
}

// Validate TODO
func (d *RecoverBinlogAct) Validate() error {
	return nil
}

// Run TODO
func (d *RecoverBinlogAct) Run() (err error) {
	defer util.LoggerErrorStack(logger.Error, err)
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    d.Payload.Params.Init,
		},
		{
			FunName: "预检查",
			Func:    d.Payload.Params.PreCheck,
		},
		{
			FunName: "恢复binlog",
			Func:    d.Payload.Params.Start,
		},
		{
			FunName: "等待导入binlog",
			Func:    d.Payload.Params.WaitDone,
		},
		{
			FunName: "恢复 binlog 完成",
			Func:    d.Payload.Params.PostCheck,
		},
	}
	if err = steps.Run(); err != nil {
		return err
	}
	logger.Info("import binlog successfully")
	return nil
}

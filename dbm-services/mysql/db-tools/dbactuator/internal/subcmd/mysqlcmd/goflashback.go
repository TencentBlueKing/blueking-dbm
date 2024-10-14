package mysqlcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/rollback"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	_ "dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil" // mysqlutil TODO

	"github.com/spf13/cobra"
)

// GoFlashbackBinlogAct TODO
type GoFlashbackBinlogAct struct {
	*subcmd.BaseOptions
	Payload rollback.GoFlashbackComp
}

// GoFlashbackBinlogCommand godoc
//
// @Summary  导入 binlog
// @Description  通过 `mysqlbinlog --flashback xxx | mysql` 导入 binlog
// @Tags         mysql
// @Accept       json
// @Param        body body      rollback.GoFlashbackComp  true  "short description"
// @Router       /mysql/flashback-binlog [post]
func GoFlashbackBinlogCommand() *cobra.Command {
	act := GoFlashbackBinlogAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "goflashback-binlog",
		Short: "导入binlog",
		Example: fmt.Sprintf(
			"dbactuator mysql goflashback-binlog %s %s",
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
func (d *GoFlashbackBinlogAct) Init() (err error) {
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
func (d *GoFlashbackBinlogAct) Validate() error {
	return nil
}

// Run TODO
func (d *GoFlashbackBinlogAct) Run() (err error) {
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
			FunName: "开始 flashback binlog",
			Func:    d.Payload.Params.Start,
		},
	}
	if err = steps.Run(); err != nil {
		return err
	}
	logger.Info("import binlog successfully")
	return nil
}

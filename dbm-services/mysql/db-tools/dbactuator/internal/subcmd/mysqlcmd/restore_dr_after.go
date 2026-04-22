package mysqlcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/restore"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// RestoreDRAfterAct restore-dr-after 子命令
type RestoreDRAfterAct struct {
	*subcmd.BaseOptions
	Payload restore.RestoreDRAfterComp
}

// RestoreDRAfterCommand godoc
//
// @Summary  物理恢复后操作
// @Description  物理备份恢复后的 PostLoad 操作（repairAndStart），独立于 restore-dr 执行
// ./dbactuator  mysql restore-dr
//
//	增加了 skip_after_load 参数，控制是否跳过数据恢复后的收尾工作。默认 false 不跳过
//
// ./dbactuator  mysql restore-dr-after
//
//	当 restore-dr 使用 skip_after_load 参数跳过了收尾工作，需要使用 restore-dr-after 子命令单独收尾
//	restore-dr-after 命令参数是 restore-dr  的子集
//
// @Tags         mysql
// @Accept       json
// @Router       /mysql/restore-dr-after [post]
func RestoreDRAfterCommand() *cobra.Command {
	act := RestoreDRAfterAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "restore-dr-after",
		Short: "物理恢复后操作",
		Example: fmt.Sprintf(
			"dbactuator mysql restore-dr-after %s %s",
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
func (d *RestoreDRAfterAct) Init() (err error) {
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
func (d *RestoreDRAfterAct) Validate() error {
	return nil
}

// Run TODO
func (d *RestoreDRAfterAct) Run() (err error) {
	defer util.LoggerErrorStack(logger.Error, err)
	steps := subcmd.Steps{
		{
			FunName: "环境初始化",
			Func:    d.Payload.Init,
		},
		{
			FunName: "执行恢复后操作(repairAndStart)",
			Func:    d.Payload.Start,
		},
	}
	if err = steps.Run(); err != nil {
		return err
	}
	logger.Info("restore-dr-after successfully")
	return nil
}

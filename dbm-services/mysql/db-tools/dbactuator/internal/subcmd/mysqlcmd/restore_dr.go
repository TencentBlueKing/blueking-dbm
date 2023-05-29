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

// RestoreDRAct TODO
type RestoreDRAct struct {
	*subcmd.BaseOptions
	Payload restore.RestoreDRComp
}

// RestoreDRCommand godoc
//
// @Summary  备份恢复
// @Description  物理备份、逻辑备份恢复
// @Tags         mysql
// @Accept       json
// @Param        body body      restore.RestoreDRComp  true  "short description"
// @Success      200  {object}  mysqlutil.ChangeMaster
// @Router       /mysql/restore-dr [post]
func RestoreDRCommand() *cobra.Command {
	act := RestoreDRAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "restore-dr",
		Short: "备份恢复",
		Example: fmt.Sprintf(
			"dbactuator mysql restore-dr %s %s\n"+
				"\nOutput examples:\n%s",
			subcmd.CmdBaseExampleStr,
			subcmd.ToPrettyJson(act.Payload.Example()),
			subcmd.ToPrettyJson(act.Payload.ExampleOutput()),
		),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
			util.CheckErr(act.Next())
		},
	}
	return cmd
}

// Init TODO
func (d *RestoreDRAct) Init() (err error) {
	if err = d.BaseOptions.Validate(); err != nil { // @todo 应该在一开始就validate
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
func (d *RestoreDRAct) Validate() error {
	return nil
}

// Run TODO
func (d *RestoreDRAct) Run() (err error) {
	defer util.LoggerErrorStack(logger.Error, err)
	if err = d.Payload.ChooseType(); err != nil {
		// logger.Error("%+v", err)
		return err
	}
	steps := subcmd.Steps{
		{
			FunName: "环境初始化",
			Func:    d.Payload.Init,
		},
		{
			FunName: "恢复预检查",
			Func:    d.Payload.PreCheck,
		},
		{
			FunName: "恢复",
			Func:    d.Payload.Start,
		},
		{
			FunName: "等待恢复完成",
			Func:    d.Payload.WaitDone,
		},
		{
			FunName: "完成校验",
			Func:    d.Payload.PostCheck,
		},
		{
			FunName: "输出位点",
			Func:    d.Payload.OutputCtx,
		},
	}
	if err = steps.Run(); err != nil {
		return err
	}
	logger.Info("backup restore successfully")
	return nil
}

// Next 运行下一个 component
func (d *RestoreDRAct) Next() error {
	logger.Info("run next: change-master")
	if comp := d.Payload.BuildChangeMaster(); comp != nil {
		act := BuildMsRelationAct{
			BaseOptions: d.BaseOptions,
			Payload:     *comp,
		}
		// comp.GeneralParam = subcmd.GeneralRuntimeParam
		return act.Run()
	}
	return nil
}

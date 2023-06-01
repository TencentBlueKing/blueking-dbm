package mysqlcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// FindLocalBackupAct TODO
type FindLocalBackupAct struct {
	*subcmd.BaseOptions
	Payload mysql.FindLocalBackupComp
}

// FindLocalBackupCommand godoc
//
// @Summary      查找本地备份
// @Description  查找本地备份
// @Tags         mysql
// @Accept       json
// @Param        body body      mysql.FindLocalBackupParam  true  "short description"
// @Success      200  {object}  mysql.FindLocalBackupResp
// @Router       /mysql/find-local-backup [post]
func FindLocalBackupCommand() *cobra.Command {
	act := FindLocalBackupAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "find-local-backup",
		Short: "查找本地备份",
		Example: fmt.Sprintf(
			`dbactuator mysql find-local-backup %s %s`,
			subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Payload.Example()),
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
func (d *FindLocalBackupAct) Init() (err error) {
	if err = d.BaseOptions.Validate(); err != nil { // @todo 应该在一开始就validate
		return err
	}
	if err = d.Deserialize(&d.Payload.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	return
}

// Validate TODO
func (d *FindLocalBackupAct) Validate() error {
	return nil
}

// Run TODO
func (d *FindLocalBackupAct) Run() (err error) {
	defer util.LoggerErrorStack(logger.Error, err)
	steps := subcmd.Steps{
		{
			FunName: "组件初始化",
			Func:    d.Payload.Params.Init,
		},
		{
			FunName: "预检查",
			Func:    d.Payload.Params.PreCheck,
		},
		{
			FunName: "开始查找备份",
			Func:    d.Payload.Params.Start,
		},
		{
			FunName: "输出备份信息",
			Func:    d.Payload.Params.OutputCtx,
		},
	}
	if err = steps.Run(); err != nil {
		return err
	}
	logger.Info("find local backups done")
	return nil
}

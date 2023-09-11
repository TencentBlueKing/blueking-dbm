package mysqlcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// OSCmdRunAct TODO
type OSCmdRunAct struct {
	*subcmd.BaseOptions
	Payload mysql.OSCmdRunComp
}

// OSCmdRunCommand godoc
//
// @Summary      执行os简单命令
// @Description  执行os简单命令
// @Tags         mysql
// @Accept       json
// @Param        body body      mysql.OSCmds  true  "short description"
// @Success      200  {object}  mysql.OSCmdRunResp
// @Router       /mysql/oscmd-run [post]
func OSCmdRunCommand() *cobra.Command {
	act := OSCmdRunAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "oscmd-run",
		Short: "执行os简单命令",
		Example: fmt.Sprintf(
			`dbactuator mysql oscmd-run %s %s`,
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
func (d *OSCmdRunAct) Init() (err error) {
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
func (d *OSCmdRunAct) Validate() error {
	return nil
}

// Run TODO
func (d *OSCmdRunAct) Run() (err error) {
	defer util.LoggerErrorStack(logger.Error, err)
	steps := subcmd.Steps{
		{
			FunName: "执行命令集",
			Func:    d.Payload.Start,
		},
	}
	if err = steps.Run(); err != nil {
		return err
	}
	logger.Info("oscmd-run done")
	return nil
}

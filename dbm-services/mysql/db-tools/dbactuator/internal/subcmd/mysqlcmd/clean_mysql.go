package mysqlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

// CleanMysqlAct TODO
type CleanMysqlAct struct {
	*subcmd.BaseOptions
	Payload mysql.CleanMysqlComp
}

// CleanMysqlCommand godoc
//
// @Summary      清空实例，高危
// @Description  清空本地实例，保留系统库
// @Tags         mysql
// @Accept       json
// @Produce      json
// @Param        body body      mysql.CleanMysqlComp  true  "description"
// @Router       /mysql/clean-mysql [post]
func CleanMysqlCommand() *cobra.Command {
	act := CleanMysqlAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "clean-mysql",
		Short: "清空实例",
		Example: fmt.Sprintf(
			`dbactuator mysql clean-mysql %s %s`,
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
func (d *CleanMysqlAct) Init() (err error) {
	if err = d.BaseOptions.Validate(); err != nil { // @todo 应该在一开始就validate
		return err
	}
	if err = d.Deserialize(&d.Payload.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	logger.Warn("params %+v", d.Payload.Params)
	d.Payload.GeneralParam = subcmd.GeneralRuntimeParam
	return
}

// Validate TODO
func (d *CleanMysqlAct) Validate() error {
	return nil
}

// Run TODO
func (d *CleanMysqlAct) Run() (err error) {
	defer util.LoggerErrorStack(logger.Error, err)
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    d.Payload.Init,
		},
		{
			FunName: "预检查",
			Func:    d.Payload.PreCheck,
		},
		{
			FunName: "清空实例",
			Func:    d.Payload.Start,
		},
	}

	if err = steps.Run(); err != nil {
		return err
	}

	logger.Info("clean mysql instance successfully")
	return nil
}

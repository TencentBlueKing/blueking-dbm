package mysqlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

// MycnfChangeAct TODO
type MycnfChangeAct struct {
	*subcmd.BaseOptions
	Payload mysql.MycnfChangeComp
}

// MycnfChangeCommand godoc
//
// @Summary      修改mysql配置
// @Description  修改mysql配置
// @Tags         mysql
// @Accept       json
// @Produce      json
// @Param        body body      mysql.MycnfChangeComp  true  "description"
// @Router       /mysql/mycnf-change [post]
func MycnfChangeCommand() *cobra.Command {
	act := MycnfChangeAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "mycnf-change",
		Short: "修改mysql配置",
		Example: fmt.Sprintf(
			`dbactuator mysql mycnf-change %s %s`,
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
func (d *MycnfChangeAct) Init() (err error) {
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
func (d *MycnfChangeAct) Validate() error {
	return nil
}

// Run TODO
func (d *MycnfChangeAct) Run() (err error) {
	defer util.LoggerErrorStack(logger.Error, err)
	steps := subcmd.Steps{
		{
			FunName: "加载配置文件",
			Func:    d.Payload.Params.Init,
		},
		{
			FunName: "预检查",
			Func:    d.Payload.Params.PreCheck,
		},
		{
			FunName: "修改配置",
			Func:    d.Payload.Params.Start,
		},
	}

	if err = steps.Run(); err != nil {
		return err
	}

	logger.Info("change my.cnf successfully")
	return nil
}

package mysqlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

// MycnfCloneAct TODO
type MycnfCloneAct struct {
	*subcmd.BaseOptions
	Payload mysql.MycnfCloneComp
}

// MycnfCloneCommand godoc
//
// @Summary      从源实例克隆 my.cnf 部分参数到目标实例
// @Description  用于 slave 重建或迁移，保持新实例与 my.cnf 实例关键参数相同的场景
// @Description  默认 clone 参数:
// @Tags         mysql
// @Accept       json
// @Produce      json
// @Param        body body      mysql.MycnfCloneComp  true  "description"
// @Router       /mysql/mycnf-clone [post]
func MycnfCloneCommand() *cobra.Command {
	act := MycnfCloneAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "mycnf-clone",
		Short: "克隆mysql配置",
		Example: fmt.Sprintf(
			`dbactuator mysql mycnf-clone %s %s`,
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
func (d *MycnfCloneAct) Init() (err error) {
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
func (d *MycnfCloneAct) Validate() error {
	return nil
}

// Run TODO
func (d *MycnfCloneAct) Run() (err error) {
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
	logger.Info("clone my.cnf successfully")
	return nil
}

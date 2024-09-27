package mysqlcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// ChangeServerIdAct TODO
type ChangeServerIdAct struct {
	*subcmd.BaseOptions
	Payload mysql.ChangeServerIdComp
}

// ChangeServerIdCommand godoc
//
// @Summary      修改 server-id
// @Description  如果是 5.7，同时会修改 server_uuid
// @Tags         mysql
// @Accept       json
// @Produce      json
// @Param        body body      mysql.ChangeServerIdComp  true  "description"
// @Router       /mysql/change-server-id[post]
func ChangeServerIdCommand() *cobra.Command {
	act := ChangeServerIdAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "change-server-id",
		Short: "修改mysql配置",
		Example: fmt.Sprintf(
			`dbactuator mysql change-server-id %s %s`,
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
func (d *ChangeServerIdAct) Init() (err error) {
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
func (d *ChangeServerIdAct) Validate() error {
	return nil
}

// Run TODO
func (d *ChangeServerIdAct) Run() (err error) {
	defer util.LoggerErrorStack(logger.Error, err)
	steps := subcmd.Steps{
		{
			FunName: "加载配置文件",
			Func:    d.Payload.Init,
		},
		{
			FunName: "预检查",
			Func:    d.Payload.PreCheck,
		},
		{
			FunName: "修改server-id",
			Func:    d.Payload.Start,
		},
	}

	if err = steps.Run(); err != nil {
		return err
	}

	logger.Info("change server-id successfully")
	return nil
}

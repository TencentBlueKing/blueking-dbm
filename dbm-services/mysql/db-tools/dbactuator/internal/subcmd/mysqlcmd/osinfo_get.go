package mysqlcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// OSInfoGetAct TODO
type OSInfoGetAct struct {
	*subcmd.BaseOptions
	Payload mysql.OSInfoGetComp
}

// OSInfoGetCommand godoc
//
// @Summary      获取 os 内存、cpu、目录/磁盘 信息
// @Description  获取 os 内存、cpu、目录/磁盘 信息
// @Tags         mysql
// @Accept       json
// @Param        body body      mysql.OSInfoGetComp  true  "short description"
// @Success      200  {object}  mysql.OSInfoResult
// @Router       /mysql/osinfo-get [post]
func OSInfoGetCommand() *cobra.Command {
	act := OSInfoGetAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "osinfo-get",
		Short: "获取 os 内存、cpu、目录/磁盘 信息",
		Example: fmt.Sprintf(
			`dbactuator mysql osinfo-get %s %s`,
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
func (d *OSInfoGetAct) Init() (err error) {
	if len(d.BaseOptions.Payload) == 0 {
		return nil
	}
	if err = d.Deserialize(&d.Payload.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	return
}

// Validate TODO
func (d *OSInfoGetAct) Validate() error {
	return nil
}

// Run TODO
func (d *OSInfoGetAct) Run() (err error) {
	defer util.LoggerErrorStack(logger.Error, err)
	steps := subcmd.Steps{
		{
			FunName: "采集信息",
			Func:    d.Payload.Start,
		},
		{
			FunName: "输出信息",
			Func:    d.Payload.OutputCtx,
		},
	}
	if err = steps.Run(); err != nil {
		return err
	}
	logger.Info("osinfo-get done")
	return nil
}

package mysqlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	_ "dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil" // mysqlutil TODO
	"fmt"

	"github.com/spf13/cobra"
)

// ParseBinlogTimeAct TODO
type ParseBinlogTimeAct struct {
	*subcmd.BaseOptions
	Payload mysql.BinlogTimeComp
}

// ParseBinlogTimeCommand godoc
//
// @Summary  获取 binlog 的开始和结束时间
// @Description 获取 binlog FileDescriptionFormat 和 RotateEvent 事件
// @Tags         mysql
// @Accept       json
// @Param        body body      mysql.BinlogTimeComp  true  "short description"
// @Router       /mysql/parse-binlog-time [post]
func ParseBinlogTimeCommand() *cobra.Command {
	act := ParseBinlogTimeAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "parse-binlog-time",
		Short: "获取 binlog 起止时间",
		Example: fmt.Sprintf(
			"dbactuator mysql parse-binlog-time %s %s",
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
func (d *ParseBinlogTimeAct) Init() (err error) {
	if err = d.BaseOptions.Validate(); err != nil {
		return err
	}
	if err = d.Deserialize(&d.Payload.Params); err != nil {
		logger.Error("Deserialize err %s", err.Error())
		return err
	}
	return
}

// Validate TODO
func (d *ParseBinlogTimeAct) Validate() error {
	return nil
}

// Run TODO
func (d *ParseBinlogTimeAct) Run() (err error) {
	defer util.LoggerErrorStack(logger.Error, err)
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    d.Payload.Init,
		},
		{
			FunName: "开始获取",
			Func:    d.Payload.Start,
		},
	}
	if err = steps.Run(); err != nil {
		return err
	}
	logger.Info("get binlog start and stop datetime successfully")
	return nil
}

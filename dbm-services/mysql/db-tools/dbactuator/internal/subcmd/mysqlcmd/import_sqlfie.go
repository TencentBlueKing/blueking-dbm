package mysqlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

// ExecSQLFileAct TODO
type ExecSQLFileAct struct {
	*subcmd.BaseOptions
	Payload mysql.ExcuteSQLFileComp
}

const (
	// ImportSQLFile TODO
	ImportSQLFile = "import-sqlfile"
)

// NewExecSQLFileCommand TODO
func NewExecSQLFileCommand() *cobra.Command {
	act := ExecSQLFileAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   ImportSQLFile,
		Short: "SQL导入",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`,
			ImportSQLFile,
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

// Validate TODO
func (d *ExecSQLFileAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init TODO
func (d *ExecSQLFileAct) Init() (err error) {
	if err = d.Deserialize(&d.Payload.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	d.Payload.GeneralParam = subcmd.GeneralRuntimeParam
	return
}

// Run TODO
func (d *ExecSQLFileAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "Init",
			Func:    d.Payload.Init,
		}, {
			FunName: "执行前预处理",
			Func: func() error {
				if d.Payload.Params.IsSpider {
					return d.Payload.OpenDdlExecuteByCtl()
				}
				logger.Info("无需预处理，跳过")
				return nil
			},
		},
		{
			FunName: "执行导入SQL文件",
			Func:    d.Payload.Excute,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}

	logger.Info("import sqlfile successfully")
	return nil
}

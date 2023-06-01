package mysqlcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// ExecPartitionSQLAct TODO
type ExecPartitionSQLAct struct {
	*subcmd.BaseOptions
	Payload mysql.ExcutePartitionSQLComp
}

const (
	// ImportPartitionSQL TODO
	ImportPartitionSQL = "import-partitionsql"
)

// NewExecPartitionSQLCommand TODO
func NewExecPartitionSQLCommand() *cobra.Command {
	act := ExecPartitionSQLAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   ImportPartitionSQL,
		Short: "分区",
		Example: fmt.Sprintf(
			`dbactuator mysql deploy-monitor  %s %s`,
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
func (d *ExecPartitionSQLAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init TODO
func (d *ExecPartitionSQLAct) Init() (err error) {
	if err = d.Deserialize(&d.Payload.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	d.Payload.GeneralParam = subcmd.GeneralRuntimeParam
	return
}

// Run TODO
func (d *ExecPartitionSQLAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "Init",
			Func:    d.Payload.Init,
		},
		{
			FunName: "执行分区",
			Func:    d.Payload.Excute,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}

	logger.Info("import partition sql successfully")
	return nil
}

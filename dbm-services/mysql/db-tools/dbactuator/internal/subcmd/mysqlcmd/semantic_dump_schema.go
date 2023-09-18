package mysqlcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// SenmanticDumpSchemaAct TODO
type SenmanticDumpSchemaAct struct {
	*subcmd.BaseOptions
	Service mysql.SemanticDumpSchemaComp
}

// NewSenmanticDumpSchemaCommand godoc
//
// @Summary      运行语义检查
// @Description  运行语义检查
// @Tags         mysql
// @Accept       json
// @Produce      json
// @Param        body body      mysql.SemanticDumpSchemaComp  true  "short description"
// @Router       /mysql/semantic-dumpschema [post]
func NewSenmanticDumpSchemaCommand() *cobra.Command {
	act := SenmanticDumpSchemaAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "semantic-dumpschema",
		Short: "运行导出表结构",
		Example: fmt.Sprintf(
			`dbactuator mysql senmantic-check %s %s`,
			subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Service.Example()),
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
func (d *SenmanticDumpSchemaAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init TODO
func (d *SenmanticDumpSchemaAct) Init() (err error) {
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

// Run TODO
func (d *SenmanticDumpSchemaAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "precheck",
			Func:    d.Service.Precheck,
		}, {
			FunName: "init",
			Func:    d.Service.Init,
		},
		{
			FunName: "运行导出表结构",
			Func:    d.Service.DumpSchema,
		},
		{
			FunName: "上传表结构",
			Func:    d.Service.Upload,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}

	logger.Info("导出表结构成功")
	return nil
}

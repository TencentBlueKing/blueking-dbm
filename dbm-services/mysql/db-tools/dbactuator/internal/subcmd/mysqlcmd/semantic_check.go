package mysqlcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// SenmanticCheckAct TODO
type SenmanticCheckAct struct {
	*subcmd.BaseOptions
	Payload mysql.SemanticCheckComp
	Clean   bool
}

// NewSenmanticCheckCommand godoc
//
// @Summary      运行语义检查
// @Description  运行语义检查
// @Tags         mysql
// @Accept       json
// @Produce      json
// @Param        body body      mysql.SemanticCheckComp  true  "short description"
// @Router       /mysql/semantic-check [post]
func NewSenmanticCheckCommand() *cobra.Command {
	act := SenmanticCheckAct{
		BaseOptions: subcmd.GBaseOptions,
		Payload:     mysql.SemanticCheckComp{},
	}
	cmd := &cobra.Command{
		Use:   "semantic-check",
		Short: "运行语义检查",
		Example: fmt.Sprintf(
			`dbactuator mysql senmantic-check %s %s`,
			subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Payload.Example()),
		),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			if act.RollBack {
				util.CheckErr(act.Rollback())
				return
			}
			util.CheckErr(act.Init())
			if act.Clean {
				util.CheckErr(act.Payload.Clean())
				return
			}
			util.CheckErr(act.Run())
		},
	}
	cmd.Flags().BoolVarP(&act.Clean, "clean", "c", act.Clean, "清理语义检查实例")
	return cmd
}

// Validate TODO
func (d *SenmanticCheckAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init TODO
func (d *SenmanticCheckAct) Init() (err error) {
	if err = d.Deserialize(&d.Payload.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Payload.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

// Rollback TODO
func (d *SenmanticCheckAct) Rollback() (err error) {
	return
}

// Run TODO
func (d *SenmanticCheckAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "precheck",
			Func:    d.Payload.Precheck,
		}, {
			FunName: "init",
			Func: func() error {
				return d.Payload.Init(d.Uid)
			},
		},
		{
			FunName: "运行语义分析",
			Func:    d.Payload.Run,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}

	logger.Info("运行语义检查成功")
	return nil
}

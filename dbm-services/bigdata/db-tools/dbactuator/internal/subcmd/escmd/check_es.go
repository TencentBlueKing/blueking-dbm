package escmd

import (
	"dbm-services/bigdata/db-tools/dbactuator/internal/subcmd"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components/elasticsearch"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"
	"encoding/json"
	"fmt"

	"github.com/spf13/cobra"
)

// CheckEsHealthAct TODO
type CheckEsHealthAct struct {
	*subcmd.BaseOptions
	Service elasticsearch.CheckEsHealthComp
}

// CheckEsHealthCommand TODO
func CheckEsHealthCommand() *cobra.Command {
	act := CheckEsHealthAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "check_es",
		Short:   "检查es节点状态",
		Example: fmt.Sprintf(`dbactuator es check_es %s`, subcmd.CmdBaseExapmleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			if act.RollBack {
				util.CheckErr(act.Rollback())
				return
			}
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Validate TODO
func (d *CheckEsHealthAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init TODO
func (d *CheckEsHealthAct) Init() (err error) {
	logger.Info("CheckEsHealthAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return d.Service.Init()
}

// Rollback TODO
//
//	@receiver d
//	@return err
func (d *CheckEsHealthAct) Rollback() (err error) {
	var r rollback.RollBackObjects
	if err = d.DeserializeAndValidate(&r); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	err = r.RollBack()
	if err != nil {
		logger.Error("roll back failed %s", err.Error())
	}
	return
}

// Run TODO
func (d *CheckEsHealthAct) Run() (err error) {
	steps := subcmd.Steps{
		/* Todo
		{
			FunName: "预检查",
			Func:    d.Service.PreCheck,
		},
		*/
		{
			FunName: "es节点健康检查",
			Func:    d.Service.CheckEsHealth,
		},
	}

	if err := steps.Run(); err != nil {
		rollbackCtxb, rerr := json.Marshal(d.Service.RollBackContext)
		if rerr != nil {
			logger.Error("json Marshal %s", err.Error())
			fmt.Printf("<ctx>Can't RollBack<ctx>\n")
		}
		fmt.Printf("<ctx>%s<ctx>\n", string(rollbackCtxb))
		return err
	}

	logger.Info("check_es successfully")
	return nil
}

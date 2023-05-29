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

// InstallEsHotAct TODO
type InstallEsHotAct struct {
	*subcmd.BaseOptions
	Service elasticsearch.InstallEsComp
}

// InstallEsHotCommand TODO
func InstallEsHotCommand() *cobra.Command {
	act := InstallEsHotAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "install_hot",
		Short:   "部署hot实例",
		Example: fmt.Sprintf(`dbactuator es install_hot %s`, subcmd.CmdBaseExapmleStr),
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
func (d *InstallEsHotAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init TODO
func (d *InstallEsHotAct) Init() (err error) {
	logger.Info("DeployEsHotAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return d.Service.InitDefaultParam()
}

// Rollback TODO
//
//	@receiver d
//	@return err
func (d *InstallEsHotAct) Rollback() (err error) {
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
func (d *InstallEsHotAct) Run() (err error) {
	steps := subcmd.Steps{
		/* Todo
		{
			FunName: "预检查",
			Func:    d.Service.PreCheck,
		},
		*/
		{
			FunName: "部署Hot",
			Func:    d.Service.InstallHot,
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

	logger.Info("install_Hot successfully")
	return nil
}

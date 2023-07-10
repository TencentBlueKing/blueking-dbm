package escmd

import (
	"encoding/json"
	"fmt"

	"dbm-services/bigdata/db-tools/dbactuator/internal/subcmd"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components/elasticsearch"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/spf13/cobra"
)

// GenCertificateAct struct
type GenCertificateAct struct {
	*subcmd.BaseOptions
	Service elasticsearch.GenCerComp
}

// GenCerCommand function
// Usage: dbactuator es gen_certificate xxxxxx
// For 7.10.2, use openssl to generate
// For 7.14.2, use elasticsearch-cerutil
// Finally, it will output the tar.gz package in /tmp, named es_cerfiles.tar.gz
func GenCerCommand() *cobra.Command {
	act := GenCertificateAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "gen_certificate",
		Short:   "生成证书",
		Example: fmt.Sprintf(`dbactuator es gen_certificate %s`, subcmd.CmdBaseExapmleStr),
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

// Validate cetificate
func (d *GenCertificateAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init  cmd
func (d *GenCertificateAct) Init() (err error) {
	logger.Info("GenCertificateAct Init")
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
func (d *GenCertificateAct) Rollback() (err error) {
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

// Run cetificate
func (d *GenCertificateAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "es证书生成",
			Func:    d.Service.GenCer,
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

	logger.Info("gen_certificate successfully")
	return nil
}

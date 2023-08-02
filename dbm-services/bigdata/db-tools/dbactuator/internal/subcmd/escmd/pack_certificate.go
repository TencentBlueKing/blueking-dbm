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

// PackCertificateAct TODO
type PackCertificateAct struct {
	*subcmd.BaseOptions
	Service elasticsearch.PackCerComp
}

// PackCerCommand function
// Usage: dbactuator es pack_certificate xxxxxx
// For 7.10.2, copy key files and elasticsearch.yml.append  to  /tmp/
// For 7.14.2, copy key files and elasticsearch.yml.append  to  /tmp/
// Finally, it will output the tar.gz package in /tmp, named es_cerfiles.tar.gz
// And the transfer files to other nodes
func PackCerCommand() *cobra.Command {
	act := PackCertificateAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "pack_certificate",
		Short:   "打包证书",
		Example: fmt.Sprintf(`dbactuator es pack_certificate %s`, subcmd.CmdBaseExapmleStr),
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

// Validate function
func (d *PackCertificateAct) Validate() (err error) {
	return d.BaseOptions.Validate()
}

// Init function
func (d *PackCertificateAct) Init() (err error) {
	logger.Info("GenCertificateAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return d.Service.Init()
}

// Rollback function
// Not complete now
//
//	@receiver d
//	@return err
func (d *PackCertificateAct) Rollback() (err error) {
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

// Run function
func (d *PackCertificateAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "es证书打包",
			Func:    d.Service.PackCer,
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

	logger.Info("pack_certificate successfully")
	return nil
}

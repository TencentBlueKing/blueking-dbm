package sysinitcmd

import (
	"fmt"

	"dbm-services/bigdata/db-tools/dbactuator/internal/subcmd"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components/sysinit"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/spf13/cobra"
)

// SysInitAct TODO
type SysInitAct struct {
	*subcmd.BaseOptions
	Service sysinit.SysInitParam
}

// NewSysInitCommand TODO
func NewSysInitCommand() *cobra.Command {
	act := SysInitAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "sysinit",
		Short:   "Exec sysinit_mysql.sh,Init mysql default os user,password",
		Example: `dbactuator sysinit -p eyJ1c2VyIjoiIiwicHdkIjoiIn0=`,
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Init TODO
func (d *SysInitAct) Init() (err error) {
	if err = d.DeserializeAndValidate(&d.Service); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	return
}

// Run TODO
func (s *SysInitAct) Run() (err error) {
	steps := []subcmd.StepFunc{
		{
			FunName: "执行sysInit脚本",
			Func:    s.Service.SysInitMachine,
		},
		{
			FunName: fmt.Sprintf("重置%sOS密码", s.Service.OsMysqlUser),
			Func:    s.Service.SetOsPassWordForMysql,
		},
	}
	logger.Info("start sysinit ...")
	for idx, f := range steps {
		if err = f.Func(); err != nil {
			logger.Error("step <%d>, run [%s] occur %v", idx, f.FunName, err)
			return err
		}
		logger.Info("step <%d>, run [%s] successfully", idx, f.FunName)
	}
	logger.Info("sysinit successfully")
	return
}

package sysinitcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/riak/db-tools/dbactuator/internal/subcmd"
	"dbm-services/riak/db-tools/dbactuator/pkg/components/sysinit"
	"dbm-services/riak/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// SysInitAct TODO
type SysInitAct struct {
	*subcmd.BaseOptions
}

// NewSysInitCommand TODO
func NewSysInitCommand() *cobra.Command {
	act := SysInitAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "sysinit-riak",
		Short:   "Exec sysinit_riak.sh",
		Example: `dbactuator sysinit-riak -p eyJ1c2VyIjoiIiwicHdkIjoiIn0=`,
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Run TODO
func (s *SysInitAct) Run() (err error) {
	steps := []subcmd.StepFunc{
		{
			FunName: "执行sysInit脚本",
			Func:    sysinit.ExecSysInitScript,
		},
	}
	if s.IsExternal() {
		steps = append(
			steps, subcmd.StepFunc{
				FunName: "安装Perl以及相关依赖",
				Func:    sysinit.InitExternal,
			},
		)
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

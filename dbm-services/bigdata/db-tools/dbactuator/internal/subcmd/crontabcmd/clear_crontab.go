package crontabcmd

import (
	"fmt"

	"dbm-services/bigdata/db-tools/dbactuator/internal/subcmd"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components/crontab"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/spf13/cobra"
)

// ClearCrontabAct TODO
type ClearCrontabAct struct {
	*subcmd.BaseOptions
	Service crontab.ClearCrontabParam
}

// ClearCrontabCommand TODO
func ClearCrontabCommand() *cobra.Command {
	act := ClearCrontabAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "clear-crontab",
		Short:   "清理crontab",
		Example: fmt.Sprintf(`dbactuator clear-crontab %s`, subcmd.CmdBaseExampleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Init TODO
func (d *ClearCrontabAct) Init() (err error) {
	if err = d.DeserializeAndValidate(&d.Service); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	return
}

// Run TODO
func (s *ClearCrontabAct) Run() (err error) {
	steps := []subcmd.StepFunc{
		{
			FunName: "清理机器的crontab",
			Func:    s.Service.CleanCrontab,
		},
	}
	logger.Info("start clean crontab ...")
	for idx, f := range steps {
		if err = f.Func(); err != nil {
			logger.Error("step <%d>, run [%s] occur %v", idx, f.FunName, err)
			return err
		}
		logger.Info("step <%d>, run [%s] successfully", idx, f.FunName)
	}
	logger.Info("clean crontab successfully")
	return
}

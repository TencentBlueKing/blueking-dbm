package mysqlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/computil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// StartMysqlAct TODO
type StartMysqlAct struct {
	*subcmd.BaseOptions
	Payload computil.StartMySQLParam
}

// NewStartMysqlCommand TODO
func NewStartMysqlCommand() *cobra.Command {
	act := StartMysqlAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "start",
		Short: "启动MySQL实例",
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Init TODO
func (s *StartMysqlAct) Init() (err error) {
	if err = s.DeserializeAndValidate(&s.Payload); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	return
}

// Run TODO
func (s *StartMysqlAct) Run() (err error) {
	defer util.LoggerErrorStack(logger.Error, err)
	if _, err = s.Payload.StartMysqlInstance(); err != nil {
		logger.Error("start %s:%d failed,err:%s", s.Payload.Host, s.Payload.Port, err.Error())
		return err
	}
	return
}

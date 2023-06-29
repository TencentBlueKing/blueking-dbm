package riakcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/riak/db-tools/dbactuator/internal/subcmd"
	"dbm-services/riak/db-tools/dbactuator/pkg/components/riak"
	"dbm-services/riak/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// CheckConnectionsAct 搬迁数据进度riak dbactor参数
type CheckConnectionsAct struct {
	*subcmd.BaseOptions
	Payload riak.CheckConnectionsComp
}

// NewCheckConnectionsCommand riak搬迁数据进度
func NewCheckConnectionsCommand() *cobra.Command {
	act := CheckConnectionsAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "check-connections",
		Short:   "检查连接",
		Example: fmt.Sprintf("dbactuator riak check-connections %s", subcmd.CmdBaseExampleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validator())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Validator TODO
func (d *CheckConnectionsAct) Validator() error {
	return d.BaseOptions.Validate()
}

// Init 反序列化并检查
func (d *CheckConnectionsAct) Init() error {
	if err := d.DeserializeAndValidate(&d.Payload); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	return nil
}

// Run 运行
func (d *CheckConnectionsAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "检查是否有业务连接",
			Func:    d.Payload.CheckConnections,
		},
	}
	// 有连接，检查失败
	if err := steps.Run(); err != nil {
		return err
	}
	//	没有连接，检查成功
	logger.Info("no connections")
	return nil
}

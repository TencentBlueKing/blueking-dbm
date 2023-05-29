package riakcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/riak/db-tools/dbactuator/internal/subcmd"
	"dbm-services/riak/db-tools/dbactuator/pkg/components/riak"
	"dbm-services/riak/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// TransferAct 搬迁数据进度riak dbactor参数
type TransferAct struct {
	*subcmd.BaseOptions
	Payload riak.TransferComp
}

// NewTransferCommand riak搬迁数据进度
func NewTransferCommand() *cobra.Command {
	act := TransferAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "transfer",
		Short:   "数据搬迁进度",
		Example: fmt.Sprintf("dbactuator riak transfer %s", subcmd.CmdBaseExampleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validator())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Validator TODO
func (d *TransferAct) Validator() error {
	return d.BaseOptions.Validate()
}

// Init 反序列化并检查
func (d *TransferAct) Init() error {
	if err := d.DeserializeAndValidate(&d.Payload); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	return nil
}

// Run 运行
func (d *TransferAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "搬迁数据进度",
			Func:    d.Payload.Transfer,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("transfer data check success")
	return nil
}

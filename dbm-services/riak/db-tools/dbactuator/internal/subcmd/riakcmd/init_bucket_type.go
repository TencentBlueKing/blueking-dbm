package riakcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/riak/db-tools/dbactuator/internal/subcmd"
	"dbm-services/riak/db-tools/dbactuator/pkg/components/riak"
	"dbm-services/riak/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// InitBucketAct 安装riak dbactor参数
type InitBucketAct struct {
	*subcmd.BaseOptions
	Payload riak.InitBucketComp
}

// NewInitBucketCommand 部署riak节点
func NewInitBucketCommand() *cobra.Command {
	act := InitBucketAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "init-bucket-type",
		Short:   "初始化bucket-type",
		Example: fmt.Sprintf("dbactuator riak init-bucket-type %s", subcmd.CmdBaseExampleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validator())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Validator TODO
func (d *InitBucketAct) Validator() error {
	return d.BaseOptions.Validate()
}

// Init 反序列化并检查
func (d *InitBucketAct) Init() error {
	if err := d.DeserializeAndValidate(&d.Payload); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	return nil
}

// Run 运行
func (d *InitBucketAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "初始化bucket type",
			Func:    d.Payload.InitBucketType,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("init bucket type success")
	return nil
}

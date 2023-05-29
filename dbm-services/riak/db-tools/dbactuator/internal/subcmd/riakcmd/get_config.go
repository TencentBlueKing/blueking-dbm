package riakcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/riak/db-tools/dbactuator/internal/subcmd"
	"dbm-services/riak/db-tools/dbactuator/pkg/components/riak"
	"dbm-services/riak/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// GetConfigAct 安装riak dbactor参数
type GetConfigAct struct {
	*subcmd.BaseOptions
	Payload riak.GetConfigComp
}

// NewGetConfigCommand 获取riak配置
func NewGetConfigCommand() *cobra.Command {
	act := GetConfigAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "get-config",
		Short:   "获取riak配置",
		Example: fmt.Sprintf("dbactuator riak get-config %s", subcmd.CmdBaseExampleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validator())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Validator TODO
func (d *GetConfigAct) Validator() error {
	return d.BaseOptions.Validate()
}

// Init 反序列化并检查
func (d *GetConfigAct) Init() error {
	if err := d.DeserializeAndValidate(&d.Payload); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	return nil
}

// Run 执行
func (d *GetConfigAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "获取配置",
			Func:    d.Payload.GetConfig,
		},
		{
			FunName: "输出配置",
			Func:    d.Payload.OutputConfigInfo,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	// 获取riak配置参数成功
	logger.Info("get config success")
	return nil
}

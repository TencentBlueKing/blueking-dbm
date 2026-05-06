package clone_grants_from_file

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/clone_grants_from_file/spider"
	"fmt"

	"github.com/spf13/cobra"
)

type CloneGrantsDumpPrivAct struct {
	*subcmd.BaseOptions
	Service spider.DumpPrivComponent
}

const CloneGrantsDumpPrivCmd = `clone-grants-dump-priv`

func NewCloneGrantsDumpPrivCommand() *cobra.Command {
	act := &CloneGrantsDumpPrivAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   CloneGrantsDumpPrivCmd,
		Short: "dump priv component",
		Example: fmt.Sprintf(
			`dbactuator spider %s %s %s`,
			CloneGrantsDumpPrivCmd,
			subcmd.CmdBaseExampleStr,
			subcmd.ToPrettyJson(act.Service.Example()),
		),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

func (c *CloneGrantsDumpPrivAct) Validate() error {
	return c.BaseOptions.Validate()
}

func (c *CloneGrantsDumpPrivAct) Init() error {
	if err := c.Deserialize(&c.Service.Params); err != nil {
		logger.Error("DeserializerAndValidate err %s", err.Error())
		return err
	}
	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	logger.Info("extend params: %s", c.Service.Params)
	return nil
}

func (c *CloneGrantsDumpPrivAct) Run() (err error) {
	defer util.LoggerErrorStack(logger.Error, err)
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    c.Service.Init,
		},
		{
			FunName: "生成备份配置",
			Func:    c.Service.GenerateBackupConfig,
		},
		{
			FunName: "终止残留备份进程",
			Func:    c.Service.KillLegacyBackup,
		},
		{
			FunName: "执行备份",
			Func:    c.Service.DoBackup,
		},
		{
			FunName: "复制权限文件",
			Func:    c.Service.RenamePrivFile,
		},
	}

	if err = steps.Run(); err != nil {
		return err
	}

	logger.Info("权限导出完成")
	return nil
}

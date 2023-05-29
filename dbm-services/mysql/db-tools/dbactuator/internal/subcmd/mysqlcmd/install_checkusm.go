package mysqlcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// InstallMySQLChecksumAct 安装数据校验
type InstallMySQLChecksumAct struct {
	*subcmd.BaseOptions
	Service mysql.InstallMySQLChecksumComp
}

// InstallMySQLChecksum 安装数据校验子命令名称
const InstallMySQLChecksum = "install-checksum"

// NewInstallMySQLChecksumCommand godoc
//
// @Summary     安装mysql校验
// @Description  安装mysql校验
// @Tags         mysql
// @Accept       json
// @Param        body body      mysql.InstallMySQLChecksumComp  true  "short description"
// @Router       /mysql/install-checksum [post]
func NewInstallMySQLChecksumCommand() *cobra.Command {
	act := InstallMySQLChecksumAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   InstallMySQLChecksum,
		Short: "安装mysql校验",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`,
			InstallMySQLChecksum,
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

// Validate 基本校验
func (c *InstallMySQLChecksumAct) Validate() (err error) {
	return c.BaseOptions.Validate()
}

// Init 初始化子命令
func (c *InstallMySQLChecksumAct) Init() (err error) {
	if err = c.Deserialize(&c.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	logger.Info("extend params: %s", c.Service.Params)
	return nil
}

// Run 执行子命令
func (c *InstallMySQLChecksumAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    c.Service.Init,
		},
		{
			FunName: "执行前检查",
			Func:    c.Service.Precheck,
		},
		{
			FunName: "部署二进制程序",
			Func:    c.Service.DeployBinary,
		},
		{
			FunName: "生成二进制程序配置",
			Func:    c.Service.GenerateBinaryConfig,
		},
		// {
		//	FunName: "生成 wrapper 文件",
		//	Func:    c.Service.BuildWrapper,
		// },
		{
			FunName: "注册 crond 任务",
			Func:    c.Service.AddToCrond,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("部署mysql校验完成")
	return nil
}

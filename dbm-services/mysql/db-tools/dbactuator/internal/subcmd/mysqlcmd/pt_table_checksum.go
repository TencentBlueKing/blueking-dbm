package mysqlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

// PtTableChecksumAct 校验基本结构
type PtTableChecksumAct struct {
	*subcmd.BaseOptions
	Service mysql.PtTableChecksumComp
}

const (
	// PtTableChecksum 命令名
	PtTableChecksum = "pt-table-checksum"
)

// NewPtTableChecksumCommand godoc
//
// @Summary 数据校验
// @Description 数据校验
// @Tags mysql
// @Accept json
// @Param body body mysql.PtTableChecksumComp true "description"
// @Router /mysql/pt-table-checksum [post]
func NewPtTableChecksumCommand() *cobra.Command {
	act := PtTableChecksumAct{
		BaseOptions: subcmd.GBaseOptions,
	}

	cmd := &cobra.Command{
		Use:   PtTableChecksum,
		Short: "数据校验",
		Example: fmt.Sprintf(
			`dbactuator mysql pt-table-checksum %s %s`,
			subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Service.Example()),
		),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Validate 基本验证
func (c *PtTableChecksumAct) Validate() (err error) {
	return c.BaseOptions.Validate()
}

// Init 初始化
func (c *PtTableChecksumAct) Init() (err error) {
	if err = c.Deserialize(&c.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	logger.Info("extend params: %s", c.Service.Params)
	return nil
}

// Run 执行序列
func (c *PtTableChecksumAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func: func() error {
				return c.Service.Init(c.Uid)
			},
		},
		{
			FunName: "执行前检查",
			Func:    c.Service.Precheck,
		},
		{
			FunName: "生成配置文件",
			Func:    c.Service.GenerateConfigFile,
		},
		{
			FunName: "执行校验",
			Func:    c.Service.DoChecksum,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("校验完成")
	return nil
}

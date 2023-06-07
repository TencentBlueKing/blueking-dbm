package mysqlcmd

//import (
//	"fmt"
//
//	"dbm-services/common/go-pubpkg/logger"
//	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
//	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
//	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
//
//	"github.com/spf13/cobra"
//)
//
//// FullBackup 命令常量
//const FullBackup = "full-backup"
//
//// FullBackupAct 命令结构
//type FullBackupAct struct {
//	*subcmd.BaseOptions
//	Service mysql.FullBackupComp
//}
//
//// NewFullBackupCommand 新建命令
//func NewFullBackupCommand() *cobra.Command {
//	act := FullBackupAct{
//		BaseOptions: subcmd.GBaseOptions,
//	}
//
//	cmd := &cobra.Command{
//		Use:   FullBackup,
//		Short: "全库备份",
//		Example: fmt.Sprintf(
//			`dbactuator mysql full-backup %s %s`,
//			subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Service.Example()),
//		),
//		Run: func(cmd *cobra.Command, args []string) {
//			util.CheckErr(act.Validate())
//			util.CheckErr(act.Init())
//			util.CheckErr(act.Run())
//		},
//	}
//	return cmd
//}
//
//// Validate 校验
//func (c *FullBackupAct) Validate() (err error) {
//	return c.BaseOptions.Validate()
//}
//
//// Init 初始化
//func (c *FullBackupAct) Init() (err error) {
//	if err = c.Deserialize(&c.Service.Params); err != nil {
//		logger.Error("DeserializeAndValidate err %s", err.Error())
//		return err
//	}
//	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
//	logger.Info("extend params: %s", c.Service.Params)
//	return nil
//}
//
//// Run 执行
//func (c *FullBackupAct) Run() (err error) {
//	steps := subcmd.Steps{
//		{
//			FunName: "初始化",
//			Func: func() error {
//				return c.Service.Init(c.Uid)
//			},
//		},
//		{
//			FunName: "执行前检查",
//			Func:    c.Service.Precheck,
//		},
//		{
//			FunName: "生成配置文件",
//			Func:    c.Service.GenerateConfigFile,
//		},
//		{
//			FunName: "执行备份",
//			Func:    c.Service.DoBackup,
//		},
//		{
//			FunName: "输出报告",
//			Func:    c.Service.OutputBackupInfo,
//		},
//	}
//
//	if err = steps.Run(); err != nil {
//		return err
//	}
//	logger.Info("备份成功")
//	return nil
//}

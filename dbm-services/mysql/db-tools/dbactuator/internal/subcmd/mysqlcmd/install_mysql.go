package mysqlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/rollback"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"encoding/json"
	"fmt"

	"github.com/spf13/cobra"
)

// DeployMySQLAct TODO
type DeployMySQLAct struct {
	*subcmd.BaseOptions
	Service mysql.InstallMySQLComp
}

// NewDeployMySQLInstanceCommand godoc
//
// @Summary      部署 mysql 实例
// @Description  部署 mysql 实例说明
// @Tags         mysql
// @Accept       json
// @Param        body body      mysql.InstallMySQLComp  true  "short description"
// @Router       /mysql/deploy [post]
func NewDeployMySQLInstanceCommand() *cobra.Command {
	act := DeployMySQLAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "deploy",
		Short: "部署MySQL实例",
		Example: fmt.Sprintf(
			`dbactuator mysql deploy %s %s`,
			subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Service.Example()),
		),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			if act.RollBack {
				util.CheckErr(act.Rollback())
				return
			}
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Init TODO
func (d *DeployMySQLAct) Init() (err error) {
	logger.Info("DeployMySQLAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return d.Service.InitDefaultParam()
}

// Rollback TODO
//
//	@receiver d
//	@return err
func (d *DeployMySQLAct) Rollback() (err error) {
	var r rollback.RollBackObjects
	if err = d.DeserializeAndValidate(&r); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	err = r.RollBack()
	if err != nil {
		logger.Error("roll back failed %s", err.Error())
	}
	return
}

// Run TODO
func (d *DeployMySQLAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "预检查",
			Func:    d.Service.PreCheck,
		},
		{
			FunName: "渲染my.cnf配置",
			Func:    d.Service.GenerateMycnf,
		},
		{
			FunName: "初始化mysqld相关目录",
			Func:    d.Service.InitInstanceDirs,
		},
		{
			FunName: "下载并且解压安装包",
			Func:    d.Service.DecompressMysqlPkg,
		},
		{
			FunName: "初始化mysqld系统库表",
			Func:    d.Service.Install,
		},
		{
			FunName: "启动mysqld",
			Func:    d.Service.Startup,
		},
		{
			FunName: "执行初始化系统基础权限、库表SQL",
			Func:    d.Service.InitDefaultPrivAndSchema,
		},
		{
			FunName: "生成exporter配置文件",
			Func:    d.Service.CreateExporterCnf,
		},

		{
			FunName: "输出系统的时区设置",
			Func: func() error {
				d.OutputCtx(fmt.Sprintf("{\"time_zone\": \"%s\"}", d.Service.TimeZone))
				return nil
			},
		},
	}

	if err := steps.Run(); err != nil {
		rollbackCtxb, rerr := json.Marshal(d.Service.RollBackContext)
		if rerr != nil {
			logger.Error("json Marshal %s", err.Error())
			fmt.Printf("<ctx>Can't RollBack<ctx>\n")
		}
		fmt.Printf("<ctx>%s<ctx>\n", string(rollbackCtxb))
		return err
	}

	logger.Info("install_mysql successfully")
	return nil
}

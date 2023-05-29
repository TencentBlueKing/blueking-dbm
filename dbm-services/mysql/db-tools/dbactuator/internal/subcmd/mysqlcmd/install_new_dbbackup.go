package mysqlcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// InstallNewDbBackupAct TODO
type InstallNewDbBackupAct struct {
	*subcmd.BaseOptions
	Service mysql.InstallNewDbBackupComp
}

// NewInstallNewDbBackupCommand godoc
//
// @Summary      部署备份程序
// @Description  部署GO版本备份程序
// @Tags         mysql
// @Accept       json
// @Param        body body      mysql.InstallNewDbBackupComp  true  "short description"
// @Router       /mysql/deploy-dbbackup [post]
func NewInstallNewDbBackupCommand() *cobra.Command {
	act := InstallNewDbBackupAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "deploy-dbbackup",
		Short: "部署GO版本备份程序",
		Example: fmt.Sprintf(
			`dbactuator mysql deploy-dbbackup %s %s`, subcmd.CmdBaseExampleStr,
			subcmd.ToPrettyJson(act.Service.Example()),
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
func (d *InstallNewDbBackupAct) Init() (err error) {
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return nil
}

// Run TODO
func (d *InstallNewDbBackupAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "init",
			Func:    d.Service.Init,
		},
		{
			FunName: "初始化待渲染配置",
			Func:    d.Service.InitRenderData,
		},
		{
			FunName: "初始化备份数据目录",
			Func:    d.Service.InitBackupDir,
		},
		{
			FunName: "备份原备份程序",
			Func:    d.Service.BackupBackupIfExist,
		},
		{
			FunName: "初始化备份程序用户",
			Func:    d.Service.InitBackupUserPriv,
		},
		{
			FunName: "解压备份程序压缩包",
			Func:    d.Service.DecompressPkg,
		},
		{
			FunName: "生成配置",
			Func:    d.Service.GenerateDbbackupConfig,
		},
		{
			FunName: "更改安装路径所属用户组",
			Func:    d.Service.ChownGroup,
		},
		{
			FunName: "添加系统crontab",
			Func:    d.Service.AddCrontab,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("install new dbbackup successfully~")
	return nil
}

// Rollback TODO
func (d *InstallNewDbBackupAct) Rollback() (err error) {
	return
}

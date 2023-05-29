package commoncmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/backup_download"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

// IBSRecoverAct TODO
type IBSRecoverAct struct {
	*subcmd.BaseOptions
	Payload backup_download.IBSRecoverComp
}

// CommandIBSRecover godoc
//
// @Summary      从 ieg 备份系统下载文件
// @Description  提供 task_id，从 ieg 备份系统下载文件
// @Description task_files_wild: 模糊搜索文件并下载, task_files: 精确文件查询并下载
// @Description task_files_wild, task_files 二选一
// @Description 启用 skip_local_exists=true 时，如果目标目录已存在要下载的文件，会自动跳过
// @Tags         download
// @Accept       json
// @Param        body body      backup_download.IBSRecoverComp  true  "short description"
// @Success      200  {object}  backup_download.IBSRecoverTask
// @Router       /download/ibs-recover [post]
func CommandIBSRecover() *cobra.Command {
	act := IBSRecoverAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "ibs-recover",
		Short: "从 ieg 备份系统下载文件",
		Example: fmt.Sprintf(
			`dbactuator download ibs-recover %s %s`,
			subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Payload.Example()),
		),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Init TODO
func (d *IBSRecoverAct) Init() (err error) {
	if err = d.BaseOptions.Validate(); err != nil {
		return err
	}
	if err = d.Deserialize(&d.Payload.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	return
}

// Validate TODO
func (d *IBSRecoverAct) Validate() error {
	return nil
}

// Run TODO
func (d *IBSRecoverAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    d.Payload.Init,
		},
		{
			FunName: "下载预检查",
			Func:    d.Payload.PreCheck,
		},
		{
			FunName: "开始下载",
			Func:    d.Payload.Start,
		},
		{
			FunName: "等待下载完成",
			Func:    d.Payload.WaitDone,
		},
		{
			FunName: "后置检查",
			Func:    d.Payload.PostCheck,
		},
		{
			FunName: "输出下载结果",
			Func:    d.Payload.OutputCtx,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}

	logger.Info("download files from ieg backup system successfully")
	return nil
}

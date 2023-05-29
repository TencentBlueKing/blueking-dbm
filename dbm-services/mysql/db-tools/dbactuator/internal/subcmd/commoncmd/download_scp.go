package commoncmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/backup_download"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

// DownloadScpAct TODO
type DownloadScpAct struct {
	*subcmd.BaseOptions
	Payload backup_download.DFScpComp
}

// CommandDownloadScp godoc
//
// @Summary      scp下载文件
// @Description  支持限速
// @Tags         download
// @Accept       json
// @Param        body body      backup_download.DFScpParam  true  "short description"
// @Router       /download/scp [post]
func CommandDownloadScp() *cobra.Command {
	act := DownloadScpAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "scp",
		Short: "scp下载文件",
		Example: fmt.Sprintf(
			`dbactuator download scp %s %s`,
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
func (d *DownloadScpAct) Init() (err error) {
	if err = d.BaseOptions.Validate(); err != nil { // @todo 应该在一开始就validate
		return err
	}
	if err = d.Deserialize(&d.Payload.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	return
}

// Validate TODO
func (d *DownloadScpAct) Validate() error {
	return nil
}

// Run TODO
func (d *DownloadScpAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "测试目标连接性",
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
			FunName: "完成校验",
			Func:    d.Payload.PostCheck,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("download files successfully")
	return nil
}

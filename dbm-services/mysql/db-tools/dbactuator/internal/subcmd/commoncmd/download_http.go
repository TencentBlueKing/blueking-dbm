package commoncmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/backup_download"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// DownloadHttpAct TODO
type DownloadHttpAct struct {
	*subcmd.BaseOptions
	Payload backup_download.DFHttpComp
}

// CommandDownloadHttp godoc
//
// @Summary      http下载文件
// @Description  支持限速、basicAuth 认证. 一般配合 common fileserver 使用
// @Description # server1
// @Description ./dbactuator common file-server \
// @Description --payload-format raw \
// @Description --payload '{"extend":{"bind_address":":8082","mount_path":"/data/dbbak","user":"xiaog","password":"xxxx","proc_maxidle_duration":"60s"}}'
// @Description
// @Description # server2
// @Description curl -u 'xiaog:xxxx' 'http://server1:8082/datadbbak8082/dbactuator' -o dbactuator.bin --limit-rate 10k
// @Tags         download
// @Accept       json
// @Param        body body      backup_download.DFHttpParam  true  "short description"
// @Router       /download/http [post]
func CommandDownloadHttp() *cobra.Command {
	act := DownloadHttpAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "http",
		Short: "http下载文件",
		Example: fmt.Sprintf(
			`dbactuator download http %s %s`,
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
func (d *DownloadHttpAct) Init() (err error) {
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
func (d *DownloadHttpAct) Validate() error {
	return nil
}

// Run TODO
func (d *DownloadHttpAct) Run() error {
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

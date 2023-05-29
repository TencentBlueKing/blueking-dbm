package commoncmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/fileserver"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// FileServerAct TODO
type FileServerAct struct {
	*subcmd.BaseOptions
	Payload fileserver.FileServerComp
}

// CommandFileServer godoc
//
// @Summary      简单文件服务
// @Description  通过 http 暴露指定目录可用于下载，可用于在重建备库时，从其它机器下载备份
// @Description 在 OS 不允许 ssh 登录（scp/sftp）时，可以临时启动该服务来获取备份文件
// @Tags         common
// @Accept       json
// @Param        body body      fileserver.FileServerComp  true  "short description"
// @Router       /common/file-server [post]
func CommandFileServer() *cobra.Command {
	act := FileServerAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "file-server",
		Short: "启动文件服务",
		Example: fmt.Sprintf(
			`dbactuator file-server %s %s`,
			subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Payload.Example()),
		),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Init TODO
func (d *FileServerAct) Init() (err error) {
	if err = d.BaseOptions.Validate(); err != nil { // @todo 应该在一开始就validate
		return err
	}
	if err = d.Deserialize(&d.Payload.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	// d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return
}

// Run TODO
func (d *FileServerAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "初始化参数",
			Func:    d.Payload.Params.New,
		},
		{
			FunName: "启动fileserver",
			Func:    d.Payload.Params.Start,
		},
		{
			FunName: "等待结束",
			Func:    d.Payload.Params.WaitDone,
		},
		{
			FunName: "是否打印download 信息",
			Func:    d.Payload.Params.OutputCtx,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}
	// logger.Info("fileserver start successfully")
	return nil
}

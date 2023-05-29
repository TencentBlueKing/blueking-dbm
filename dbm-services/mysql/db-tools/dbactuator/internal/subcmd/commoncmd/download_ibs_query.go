package commoncmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/backup_download"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// IBSQueryAct TODO
type IBSQueryAct struct {
	*subcmd.BaseOptions
	Payload backup_download.IBSQueryComp
}

// CommandIBSQuery godoc
//
// @Summary      从 ieg 备份系统查询文件
// @Description  filename 会进行模糊匹配，返回 task_id 用于下载
// @Tags         download
// @Accept       json
// @Param        body body      backup_download.IBSQueryComp  true  "short description"
// @Success      200  {object}  backup_download.IBSQueryResult
// @Router       /download/ibs-query [post]
func CommandIBSQuery() *cobra.Command {
	act := IBSQueryAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "ibs-query",
		Short: "从 ieg 备份系统查询",
		Example: fmt.Sprintf(
			`dbactuator download ibs-query %s %s`,
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
func (d *IBSQueryAct) Init() (err error) {
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
func (d *IBSQueryAct) Validate() error {
	return nil
}

// Run TODO
func (d *IBSQueryAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    d.Payload.Init,
		},
		{
			FunName: "查询预检查",
			Func:    d.Payload.PreCheck,
		},
		{
			FunName: "查询备份文件",
			Func:    d.Payload.Start,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}

	logger.Info("query files from ieg backup system successfully")
	return nil
}

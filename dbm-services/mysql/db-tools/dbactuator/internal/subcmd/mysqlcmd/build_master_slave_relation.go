package mysqlcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// BuildMsRelationAct TODO
type BuildMsRelationAct struct {
	*subcmd.BaseOptions
	Payload mysql.BuildMSRelationComp
}

// NewBuildMsRelatioCommand godoc
//
// @Summary      建立主从关系
// @Description  执行 change master to
// @Tags         mysql
// @Accept       json
// @Param        body body      mysql.BuildMSRelationComp  true  "short description"
// @Router       /mysql/change-master [post]
func NewBuildMsRelatioCommand() *cobra.Command {
	act := BuildMsRelationAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "change-master",
		Short: "建立主从关系",
		Example: fmt.Sprintf(
			`dbactuator mysql change-master %s %s`,
			subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Payload.Example()),
		),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	// logger.Info("%s[%s]", cmd.Short, cmd.Use)
	return cmd
}

// Init TODO
func (b *BuildMsRelationAct) Init() (err error) {
	if err = b.Deserialize(&b.Payload.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	b.Payload.GeneralParam = subcmd.GeneralRuntimeParam
	return
}

// Validate TODO
func (b *BuildMsRelationAct) Validate() (err error) {
	return b.BaseOptions.Validate()
}

// Run TODO
func (b *BuildMsRelationAct) Run() (err error) {
	defer util.LoggerErrorStack(logger.Error, err)
	steps := subcmd.Steps{
		{
			FunName: "初始化本地db连接",
			Func:    b.Payload.Init,
		},
		{
			FunName: "当时实例检查",
			Func:    b.Payload.CheckCurrentSlaveStatus,
		},
		{
			FunName: "主从版本检查",
			Func:    b.Payload.CheckMSVersion,
		},
		{
			FunName: "主从字符集检查",
			Func:    b.Payload.CheckCharSet,
		},
		{
			FunName: "建立主从关系",
			Func:    b.Payload.BuildMSRelation,
		},
		{
			FunName: "检查是否关系建立正常",
			Func:    b.Payload.CheckBuildOk,
		},
	}
	if err = steps.Run(); err != nil {
		return err
	}

	logger.Info("build master slave relation successfully")
	return nil
}

package mysqlcmd

import (
	"fmt"

	"github.com/spf13/cobra"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
)

type AdoptScrTendbHAStorageAct struct {
	*subcmd.BaseOptions
	Payload mysql.AdoptScrTenDBHAStorageComp
}

const (
	AdoptTendbHAStorage = "adopt-tendbha-storage"
)

func NewAdoptScrTendbHAStorageCommand() *cobra.Command {
	act := AdoptScrTendbHAStorageAct{
		BaseOptions: subcmd.GBaseOptions,
	}

	cmd := &cobra.Command{
		Use:   AdoptTendbHAStorage,
		Short: "接管 tendbha 存储层",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`,
			AdoptTendbHAStorage, subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Payload.Example())),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}

	return cmd
}

func (c *AdoptScrTendbHAStorageAct) Validate() (err error) {
	return c.BaseOptions.Validate()
}

func (c *AdoptScrTendbHAStorageAct) Init() (err error) {
	if err = c.Deserialize(&c.Payload.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	c.Payload.GeneralParam = subcmd.GeneralRuntimeParam
	logger.Info("extend params: %s", c.Payload.Params)
	return nil
}

func (c *AdoptScrTendbHAStorageAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    c.Payload.Init,
		},
		{
			FunName: "清理旧系统crontab",
			Func:    c.Payload.ClearOldCrontab,
		},
		{
			FunName: "清理旧系统帐号",
			Func:    c.Payload.DropOldAccounts,
		},
		{
			FunName: "初始化帐号库表",
			Func:    c.Payload.InitDefaultPrivAndSchema,
		},
	}
	if err := steps.Run(); err != nil {
		logger.Error("run adopt scr tendbha storage failed: %s", err.Error())
		return err
	}
	logger.Info("接管tendbha存储层完成")
	return nil
}

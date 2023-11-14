// Package main 总入口
/*
 * @Description: dbactuator 入口函数，主要实现数据侧一些操作的命令，比如安装mssql(sqlserver)等等一系列的操作集合
 * @Useage: dbactuator --help
 */
package main

import (
	"fmt"
	"os"
	"runtime/debug"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/sqlserver/db-tools/dbactuator/internal/subcmd"
	"dbm-services/sqlserver/db-tools/dbactuator/internal/subcmd/checkcmd"
	"dbm-services/sqlserver/db-tools/dbactuator/internal/subcmd/sqlservercmd"
	"dbm-services/sqlserver/db-tools/dbactuator/internal/subcmd/sysinitcmd"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/sqlserver/db-tools/dbactuator/pkg/util/templates"

	"github.com/spf13/cobra"
)

const (
	// CMD actor入口
	CMD = "dbactuator"
)

var (
	buildstamp, githash, version, external string
)

// @title           dbactuator API
// @version         0.0.1
// @description     This is a dbactuator command collection.
// @termsOfService  http://swagger.io/terms/
// @Schemes        http
// @contact.name   API Support
// @contact.url    http://www.swagger.io/support
// @contact.email  support@swagger.io

// @license.name  Apache 2.0
// @license.url   http://www.apache.org/licenses/LICENSE-2.0.html

// @host            ./dbactuator
// @BasePath  /

// main godoc
func main() {
	defer func() {
		if err := recover(); err != nil {
			fmt.Println(err)
			logger.Error("panic goroutine inner error!%v;%s", err, string(debug.Stack()))
			os.Exit(1)
			return
		}
	}()
	if err := NewDbActuatorCommand().Execute(); err != nil {
		fmt.Fprint(os.Stderr, err.Error())
		logger.Error("NewDbActuatorCommand run failed:%s", err.Error())
		os.Exit(1)
	}
}

// NewDbActuatorCommand 新建命令
func NewDbActuatorCommand() *cobra.Command {
	cmds := &cobra.Command{
		Use: CMD,
		Short: fmt.Sprintf(`Db Operation Command Line Interface
Version: %s 
Githash: %s
External: %s 
Buildstamp:%s`, version, githash, strings.ToUpper(external), buildstamp),
		Args: cobra.OnlyValidArgs,
		PersistentPreRun: func(cmd *cobra.Command, args []string) {
			if !cmd.IsAvailableCommand() {
				runHelp(cmd, args)
				return
			}
			subcmd.SetLogger(cmd, subcmd.GBaseOptions)
			if subcmd.PrintSubCommandHelper(cmd, subcmd.GBaseOptions) {
				runHelp(cmd, args)
			}
			// 定时输出标准心跳输出
			startHeartbeat(10 * time.Second)
		},
		Run:        runHelp,
		SuggestFor: []string{CMD},
	}
	groups := templates.CommandGroups{
		{
			Message: "sysinit operation sets",
			Commands: []*cobra.Command{
				sysinitcmd.NewSysInitCommand(),
			},
		},
		{
			Message: "sqlserver operation sets",
			Commands: []*cobra.Command{
				sqlservercmd.NewSQLserverCommand(),
			},
		},
		{
			Message: "check operation sets",
			Commands: []*cobra.Command{
				checkcmd.CheckCommand(),
			},
		},
	}
	groups.Add(cmds)
	// 标志可以是 "persistent" 的，这意味着该标志将可用于分配给它的命令以及该命令下的每个命令。对于全局标志，将标志分配为根上的持久标志。
	// 默认每个subcomand 都默认带这些参数
	cmds.PersistentFlags().StringVarP(&subcmd.GBaseOptions.Payload, "payload", "p", subcmd.GBaseOptions.Payload,
		"command payload <base64>")
	cmds.PersistentFlags().StringVarP(&subcmd.GBaseOptions.PayloadFormat, "payload-format", "m",
		subcmd.GBaseOptions.PayloadFormat, "command payload format, default base64, value_allowed: base64|raw")
	cmds.PersistentFlags().StringVarP(&subcmd.GBaseOptions.Uid, "uid", "U", subcmd.GBaseOptions.Uid, "单据id")
	cmds.PersistentFlags().StringVarP(&subcmd.GBaseOptions.RootId, "root_id", "R", subcmd.GBaseOptions.NodeId, "流程id")
	cmds.PersistentFlags().StringVarP(&subcmd.GBaseOptions.NodeId, "node_id", "N", subcmd.GBaseOptions.NodeId, "节点id")
	cmds.PersistentFlags().StringVarP(&subcmd.GBaseOptions.VersionId, "version_id", "V", subcmd.GBaseOptions.NodeId,
		"运行版本id")
	cmds.PersistentFlags().BoolVarP(&subcmd.GBaseOptions.RollBack, "rollback", "r", subcmd.GBaseOptions.RollBack, "回滚任务")
	cmds.PersistentFlags().BoolVarP(&subcmd.GBaseOptions.Helper, "helper", "E", subcmd.GBaseOptions.Helper, "payload参数说明")
	subcmd.GBaseOptions.External = external
	// @todo add --daemon mode to serve http to call subcmd/components
	return cmds
}

func runHelp(cmd *cobra.Command, args []string) {
	cmd.Help()
	os.Exit(1)
}

// startHeartbeat 定時输出日志
func startHeartbeat(period time.Duration) {
	go func() {
		ticker := time.NewTicker(period)
		defer ticker.Stop()
		var hearbeatTime string
		for {
			select {
			case <-ticker.C:
				hearbeatTime = time.Now().Local().Format(cst.TIMELAYOUT)
				fmt.Fprintf(os.Stdin, "["+hearbeatTime+"]hearbeating ...\n")
			}
		}
	}()
}

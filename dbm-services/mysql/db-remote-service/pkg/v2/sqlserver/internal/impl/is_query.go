package impl

import "strings"

// CommandClassifier 按角色区分的命令白名单。
//
// v1 的问题 (代码位于 pkg/rpc_implement/sqlserver_rpc/):
//
//	v1 的 SqlserverDataReadRPCEmbed 和 SqlserverSySReadRPCEmbed 通过 Go struct embedding
//	嵌入了 SqlserverRPCEmbed, 并各自覆写了 InitQueryParseCommands() / InitExecuteParseCommands()
//	试图缩小只读角色的命令白名单 (只保留 show/select, 去掉 restore/insert/alter 等).
//
//	但 Go 的 embedding 不是继承: 被 promote 的 IsQueryCommand / IsExecuteCommand 方法
//	(定义在 SqlserverRPCEmbed 上, 见 sqlserver_rpc.go:85-106) 调用的是
//	SqlserverRPCEmbed.InitQueryParseCommands(), 不是子结构体覆写的版本.
//	所以 DataRead 和 SySRead 的 InitQueryParseCommands 覆写实际上从未生效,
//	三个角色在 v1 里用的是同一套 Admin 级别的命令白名单.
//
//	v2 改用 CommandClassifier 实例化不同的命令集, 让 DataRead/SySRead 的白名单收窄真正生效.
//	Admin 用 AdminCommands (完整命令集), DataRead/SySRead 用 ReadOnlyCommands (仅 show/select).
type CommandClassifier struct {
	queryCmds   []string
	executeCmds []string
}

// AdminCommands admin 角色的完整命令集, 与 v1 SqlserverRPCEmbed 的命令列表完全一致
var AdminCommands = &CommandClassifier{
	queryCmds: []string{
		"show",
		"select",
		"restore filelistonly",
		"restore headeronly",
	},
	executeCmds: []string{
		"use",
		"insert",
		"exec msdb.dbo.sp_update_job",
		"drop login",
		"alter login",
		"create login",
		"create user",
		"drop user",
		"alter authorization",
		"exec sp_addrolemember",
	},
}

// ReadOnlyCommands DataRead / SySRead 只读角色的命令集.
// 对应 v1 SqlserverDataReadRPCEmbed / SqlserverSySReadRPCEmbed 中
// InitQueryParseCommands 和 InitExecuteParseCommands 的覆写意图 (见 data_read.go / sys_read.go),
// 即只允许 show/select, 不允许任何写操作.
var ReadOnlyCommands = &CommandClassifier{
	queryCmds: []string{
		"show",
		"select",
	},
	executeCmds: []string{},
}

func (cc *CommandClassifier) IsQueryCommand(command string) bool {
	lower := strings.ToLower(strings.TrimSpace(command))
	for _, prefix := range cc.queryCmds {
		if strings.HasPrefix(lower, prefix) {
			return true
		}
	}
	return false
}

func (cc *CommandClassifier) IsExecuteCommand(command string) bool {
	lower := strings.ToLower(strings.TrimSpace(command))
	for _, prefix := range cc.executeCmds {
		if strings.HasPrefix(lower, prefix) {
			return true
		}
	}
	return false
}

func (cc *CommandClassifier) IsSupportedCommand(command string) bool {
	return cc.IsQueryCommand(command) || cc.IsExecuteCommand(command)
}

package consts

import (
	"fmt"
	"strings"
)

const (
	// ModeWrite TODO
	ModeWrite = "write"
	// ModeRead TODO
	ModeRead = "read"
	// ModeAdmin TODO
	ModeAdmin = "admin"
)

// RedisModuleCmdItem TODO
type RedisModuleCmdItem struct {
	Command string `json:"command"`
	Mode    string `json:"mode"`
	MinArgs int    `json:"min_args"`
	MaxArgs int    `json:"max_args"`
}

// ToString TODO
func (item *RedisModuleCmdItem) ToString() string {
	return fmt.Sprintf(`
    %s {
		Mode %s
		MinArgs %d
		MaxArgs %d
	}
	`, strings.ToLower(item.Command), item.Mode, item.MinArgs, item.MaxArgs)
}

// RedisBloomCmdItems TODO
var RedisBloomCmdItems = []RedisModuleCmdItem{
	{Command: "BF.ADD", Mode: ModeWrite, MinArgs: 3, MaxArgs: 3},
	{Command: "BF.MADD", Mode: ModeWrite, MinArgs: 3, MaxArgs: 9999},
	{Command: "BF.EXISTS", Mode: ModeRead, MinArgs: 3, MaxArgs: 3},
	{Command: "BF.MEXISTS", Mode: ModeRead, MinArgs: 3, MaxArgs: 9999},
	{Command: "BF.SCANDUMP", Mode: ModeWrite, MinArgs: 3, MaxArgs: 3},
	{Command: "BF.LOADCHUNK", Mode: ModeWrite, MinArgs: 4, MaxArgs: 4},
	{Command: "BF.INFO", Mode: ModeRead, MinArgs: 2, MaxArgs: 3},
	{Command: "BF.RESERVE", Mode: ModeWrite, MinArgs: 4, MaxArgs: 6},
	{Command: "BF.CARD", Mode: ModeRead, MinArgs: 2, MaxArgs: 2},
	{Command: "BF.INSERT", Mode: ModeWrite, MinArgs: 4, MaxArgs: 9999},
}

// RedisJsonCmdItems TODO
var RedisJsonCmdItems = []RedisModuleCmdItem{
	{Command: "JSON.ARRAPPEND", Mode: ModeWrite, MinArgs: 4, MaxArgs: 9999},
	{Command: "JSON.ARRINDEX", Mode: ModeRead, MinArgs: 4, MaxArgs: 5},
	{Command: "JSON.ARRINSERT", Mode: ModeWrite, MinArgs: 5, MaxArgs: 9999},
	{Command: "JSON.ARRLEN", Mode: ModeRead, MinArgs: 3, MaxArgs: 3},
	{Command: "JSON.ARRPOP", Mode: ModeWrite, MinArgs: 2, MaxArgs: 4},
	{Command: "JSON.ARRTRIM", Mode: ModeWrite, MinArgs: 5, MaxArgs: 5},
	{Command: "JSON.CLEAR", Mode: ModeWrite, MinArgs: 3, MaxArgs: 3},
	{Command: "JSON.DEBUG", Mode: ModeAdmin, MinArgs: 2, MaxArgs: 5},
	{Command: "JSON.DEL", Mode: ModeWrite, MinArgs: 2, MaxArgs: 3},
	{Command: "JSON.FORGET", Mode: ModeWrite, MinArgs: 2, MaxArgs: 3},
	{Command: "JSON.GET", Mode: ModeRead, MinArgs: 2, MaxArgs: 9999},
	{Command: "JSON.MERGE", Mode: ModeWrite, MinArgs: 4, MaxArgs: 4},
	{Command: "JSON.MGET", Mode: ModeRead, MinArgs: 3, MaxArgs: 9999},
	{Command: "JSON.MSET", Mode: ModeWrite, MinArgs: 4, MaxArgs: 9999},
	{Command: "JSON.NUMINCRBY", Mode: ModeWrite, MinArgs: 4, MaxArgs: 4},
	{Command: "JSON.NUMMULTBY", Mode: ModeWrite, MinArgs: 4, MaxArgs: 4},
	{Command: "JSON.OBJKEYS", Mode: ModeRead, MinArgs: 2, MaxArgs: 3},
	{Command: "JSON.OBJLEN", Mode: ModeRead, MinArgs: 2, MaxArgs: 3},
	{Command: "JSON.RESP", Mode: ModeAdmin, MinArgs: 2, MaxArgs: 3},
	{Command: "JSON.SET", Mode: ModeWrite, MinArgs: 4, MaxArgs: 5},
	{Command: "JSON.STRAPPEND", Mode: ModeWrite, MinArgs: 3, MaxArgs: 4},
	{Command: "JSON.STRLEN", Mode: ModeRead, MinArgs: 2, MaxArgs: 3},
	{Command: "JSON.TOGGLE", Mode: ModeWrite, MinArgs: 3, MaxArgs: 3},
	{Command: "JSON.TYPE", Mode: ModeRead, MinArgs: 2, MaxArgs: 3},
}

// RedisCellCmdItems TODO
var RedisCellCmdItems = []RedisModuleCmdItem{
	{Command: "CL.THROTTLE", Mode: ModeWrite, MinArgs: 5, MaxArgs: 6},
}

// GetPredixyModuleCommands 获取predixy模块的命令
func GetPredixyModuleCommands(modules []string) string {
	var builder strings.Builder
	builder.WriteString(`
CustomCommand {
	`)
	cmdItems := []RedisModuleCmdItem{}
	for _, module := range modules {
		module = strings.TrimSpace(module)
		if module == "" {
			continue
		}
		switch module {
		case ModuleRedisBloom:
			cmdItems = append(cmdItems, RedisBloomCmdItems...)
		case ModuleRedisJson:
			cmdItems = append(cmdItems, RedisJsonCmdItems...)
		case ModuleRedisCell:
			cmdItems = append(cmdItems, RedisCellCmdItems...)
		}
	}
	for _, cmdItem := range cmdItems {
		builder.WriteString(cmdItem.ToString())
	}
	builder.WriteString(`
}
	`)
	return builder.String()
}

package impl

import "strings"

var queryCmds = []string{
	"select",
	"show",
}

var executeCmds = []string{
	"refresh_users",
}

func IsQueryCommand(command string) bool {
	lower := strings.ToLower(strings.TrimSpace(command))
	for _, prefix := range queryCmds {
		if strings.HasPrefix(lower, prefix) {
			return true
		}
	}
	return false
}

func IsExecuteCommand(command string) bool {
	lower := strings.ToLower(strings.TrimSpace(command))
	for _, prefix := range executeCmds {
		if strings.HasPrefix(lower, prefix) {
			return true
		}
	}
	return false
}

// IsSupportedCommand query 或 execute 返回 true，否则 false
func IsSupportedCommand(command string) bool {
	return IsQueryCommand(command) || IsExecuteCommand(command)
}

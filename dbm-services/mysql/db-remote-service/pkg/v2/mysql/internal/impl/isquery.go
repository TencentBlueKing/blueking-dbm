package impl

import (
	"regexp"
	"slices"
	"strings"
)

func IsQueryCommand(command string) bool {
	pattern := regexp.MustCompile(`\s+`)
	firstWord := strings.ToLower(pattern.Split(command, -1)[0])
	if firstWord == "tdbctl" {
		return isTDBCTLQuery(command)
	} else {
		return slices.Index(queryCmds, firstWord) >= 0
	}
}

func isTDBCTLQuery(command string) bool {
	splitPattern := regexp.MustCompile(`\s+`)
	secondWord := strings.ToLower(splitPattern.Split(command, -1)[1])
	switch secondWord {
	case "get", "show":
		return true
	case "connect":
		catchPattern := regexp.MustCompile(`(?mi)^.*execute\s+['"](.*)['"]$`)
		executeCmd := catchPattern.FindAllStringSubmatch(command, -1)[0][1]
		return IsQueryCommand(executeCmd)
	default:
		return false
	}
}

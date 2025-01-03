package internal

import (
	"regexp"
	"strconv"
	"strings"

	"golang.org/x/exp/maps"
)

func UniqueStringSlice(s []string) []string {
	t := make(map[string]int)
	for _, v := range s {
		vv := strings.TrimSpace(v)
		if vv != "" {
			t[vv] = 1
		}
	}
	return maps.Keys(t)
}

var mysqlErrPattern *regexp.Regexp

func init() {
	mysqlErrPattern = regexp.MustCompile(`^Error ([0-9]+) \(([0-9]+)\): (.*)$`)
}

func ParseMySQLErrStr(s string) (int, int, string, bool) {
	m := mysqlErrPattern.FindAllStringSubmatch(s, -1)
	if m != nil {
		errNo, err := strconv.Atoi(m[0][1])
		if err != nil {
			return 0, 0, s, false
		}
		sqlStat, err := strconv.Atoi(m[0][2])
		if err != nil {
			return 0, 0, s, false
		}
		errMsg := m[0][3]
		return errNo, sqlStat, errMsg, true
	}
	return 0, 0, "", false
}

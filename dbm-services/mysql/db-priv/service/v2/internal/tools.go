package internal

import (
	"dbm-services/mysql/priv-service/service/v2/internal/drs"
	"fmt"
	"log/slog"
	"regexp"
	"strconv"
	"strings"

	"github.com/pkg/errors"
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
	mysqlErrPattern = regexp.MustCompile(`^Error ([0-9]+) \((.*)\): (.*)$`)
	//mysqlErrPattern = regexp.MustCompile(`^Error ([0-9]+) \(([0-9]+)\): (.*)$`)
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

func QueryMySQLVersion(bkCloudId int64, address string) (int, bool, error) {
	// 返回 55, 56, 57 这样的版本号
	res, err := drs.RPCMySQL(
		bkCloudId,
		[]string{address},
		[]string{`select version() as version`},
		false,
		600,
	)
	if err != nil {
		slog.Error(
			"query mysql version",
			slog.String("address", address),
			slog.String("err", err.Error()),
		)
		return 0, false, err
	}

	if res[0].ErrorMsg != "" {
		slog.Error(
			"query mysql version",
			slog.String("address", address),
			slog.String("err", res[0].ErrorMsg),
		)
		return 0, false, errors.New(res[0].ErrorMsg)
	}

	if res[0].CmdResults[0].ErrorMsg != "" {
		slog.Error(
			"query mysql version",
			slog.String("address", address),
			slog.String("err", res[0].CmdResults[0].ErrorMsg),
		)
		return 0, false, errors.New(res[0].CmdResults[0].ErrorMsg)
	}

	sv := strings.ToLower(res[0].CmdResults[0].TableData[0]["version"].(string))

	if strings.Contains(sv, "tspider") {
		if strings.Contains(sv, "tspider-3") {
			return 57, true, nil
		} else if strings.Contains(sv, "tspider-1") {
			return 55, true, nil
		} else if strings.Contains(sv, "tspider-4") {
			return 80, true, nil
		} else {
			return 0, false, errors.Errorf("invalid tspider version: %s", sv)
		}
	} else {
		splitV := strings.Split(sv, ".")
		v, _ := strconv.Atoi(fmt.Sprintf("%s%s", splitV[0], splitV[1]))
		return v, false, nil
	}

	//v, _ := strconv.Atoi(sv)
	//return v, nil
}

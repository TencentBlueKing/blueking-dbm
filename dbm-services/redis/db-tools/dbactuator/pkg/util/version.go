package util

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbactuator/mylog"
)

func convertVersionToUint(version string) (total uint64, err error) {
	version = strings.TrimSpace(version)
	if version == "" {
		return 0, nil
	}
	list01 := strings.Split(version, ".")
	var billion string
	var thousand string
	var single string
	if len(list01) == 0 {
		err = fmt.Errorf("version:%s format not correct", version)
		mylog.Logger.Error(err.Error())
		return 0, err
	}
	billion = list01[0]
	if len(list01) >= 2 {
		thousand = list01[1]
	}
	if len(list01) >= 3 {
		single = list01[2]
	}

	if billion != "" {
		b, err := strconv.ParseUint(billion, 10, 64)
		if err != nil {
			err = fmt.Errorf("convertVersionToUint strconv.ParseUint fail,err:%v,billion:%s,version:%s", err, billion, version)
			mylog.Logger.Error(err.Error())
			return 0, err
		}
		total += b * 1000000
	}
	if thousand != "" {
		t, err := strconv.ParseUint(thousand, 10, 64)
		if err != nil {
			err = fmt.Errorf("convertVersionToUint strconv.ParseUint fail,err:%v,thousand:%s,version:%s", err, thousand, version)
			mylog.Logger.Error(err.Error())
			return 0, err
		}
		total += t * 1000
	}
	if single != "" {
		s, err := strconv.ParseUint(single, 10, 64)
		if err != nil {
			err = fmt.Errorf("convertVersionToUint strconv.ParseUint fail,err:%v,single:%s,version:%s", err, single, version)
			mylog.Logger.Error(err.Error())
			return 0, err
		}
		total += s
	}
	return total, nil
}

// VersionParse tendis版本解析
/*
 * VersionParse
 * 2.8.17-TRedis-v1.2.20, baseVersion: 2008017,subVersion:1002020
 * 6.2.7,baseVersion: 6002007
 */
func VersionParse(version string) (baseVersion, subVersion uint64, err error) {
	reg01 := regexp.MustCompile(`[\d+.]+`)
	rets := reg01.FindAllString(version, -1)
	if len(rets) == 0 {
		err = fmt.Errorf("TendisVersionParse version:%s format not correct", version)
		mylog.Logger.Error(err.Error())
		return 0, 0, err
	}
	if len(rets) >= 1 {
		baseVersion, err = convertVersionToUint(rets[0])
		if err != nil {
			return 0, 0, err
		}
	}
	if len(rets) >= 2 {
		subVersion, err = convertVersionToUint(rets[1])
		if err != nil {
			return 0, 0, err
		}
	}

	return baseVersion, subVersion, nil
}

// RedisCliVersion redis-cli 的版本解析
func RedisCliVersion(cliBin string) (baseVersion, subVersion uint64, err error) {
	cmd := cliBin + " -v"
	verRet, err := RunBashCmd(cmd, "", nil, 20*time.Second)
	if err != nil {
		return
	}
	baseVersion, subVersion, err = VersionParse(verRet)
	if err != nil {
		return
	}
	return
}

// IsCliSupportedNoAuthWarning redis-cli 是否支持 --no-auth-warning参数
func IsCliSupportedNoAuthWarning(cliBin string) bool {
	bVer, _, err := RedisCliVersion(cliBin)
	if err != nil {
		return false
	}
	if bVer > 6000000 {
		return true
	}
	return false
}

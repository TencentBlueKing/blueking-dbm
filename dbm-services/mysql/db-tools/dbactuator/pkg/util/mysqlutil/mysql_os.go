package mysqlutil

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/osutil"

	"github.com/pkg/errors"
	"github.com/shirou/gopsutil/v3/mem"
)

// GetInstMemByIP 返回的内存单位是 MB
func GetInstMemByIP(instCount uint64) (uint64, error) {
	vMem, err := mem.VirtualMemory()
	if err != nil {
		return 0, err
	}
	kilo := uint64(1024)
	totalMemInMi := vMem.Total / kilo / kilo

	var availMem int64
	switch {
	case totalMemInMi <= 2*kilo:
		if int64(float64(totalMemInMi)*0.3) < 256 {
			availMem = int64(float64(totalMemInMi) * 0.3)
		} else {
			availMem = 256
		}
	case totalMemInMi <= 4*kilo:
		if int64(float64(totalMemInMi)*0.5) < (1024 + 512) {
			availMem = int64(float64(totalMemInMi) * 0.5)
		} else {
			availMem = 1024 + 512
		}
	case totalMemInMi <= 18*kilo:
		availMem = int64(float64(totalMemInMi-1*kilo) * 0.6)
	default:
		availMem = int64(float64(totalMemInMi) * 0.7)
	}
	mysqlTotalMem := float64(availMem) * ratio(instCount)
	return uint64(mysqlTotalMem) / instCount, nil
}

func ratio(instNum uint64) float64 {
	switch {
	case instNum <= 8:
		return 1
	case instNum <= 16:
		return 0.8
	case instNum <= 32:
		return 0.7
	default:
		return 1
	}
}

// IsSudo TODO
func IsSudo() bool {
	result, err := osutil.ExecShellCommand(false, "/usr/bin/id |grep 30019")
	if err != nil {
		logger.Warn("/usr/bin/id |grep 30019 error: %s", err.Error())
		return false
	}
	if strings.Contains(string(result), "30019") {
		return true
	}
	return false
}

// 	return ""
// }

// MySQLVersionParse ():
// input: select version() 获取到的string
// output: 获取tmysql中的mysql前缀版本
// example:
// 5.7.20-tmysql-3.1.5-log ==> 5*1000000 + 7*1000 + 20 ==> 5007020
// 5.1.13 ==>  5*1000000+1*1000+13 ==> 5001013
func MySQLVersionParse(version string) uint64 {
	re := regexp.MustCompile(`([\d]+).?([\d]+)?.?([\d]+)?`)
	return mysqlVersionParse(re, version)
}

// TmysqlVersionParse tmysql version parse
//
//	@receiver mysqlVersion
//	@return uint64
func TmysqlVersionParse(mysqlVersion string) uint64 {
	re := regexp.MustCompile(`tmysql-([\d]+).?([\d]+)?.?([\d]+)?`)
	return mysqlVersionParse(re, mysqlVersion)
}

// GetMajorVerNum TODO
// GetIntMajorVersion
// 获取主版本 int 类型
// 用于版本比较
func GetMajorVerNum(versionNu uint64) uint64 {
	return versionNu / 1000000
}

// VersionCompare TODO
// InsVersionCompare
// 切换主从版本比较
// 现在的版本前置检查条件：不论是mysql 还是 tmysql ，大版本一样都可以进行主从切换
// (mysql:5.5 5.6 5.7  tmysql: 2.2 )
func VersionCompare(masterVer, slaveVer string) (err error) {
	if strings.TrimSpace(masterVer) == "" || strings.TrimSpace(slaveVer) == "" {
		return errors.New("Compare Version Is Empty String!!!")
	}
	masterMajVer := GetMajorVerNum(MySQLVersionParse(masterVer))
	slaveMajVer := GetMajorVerNum(MySQLVersionParse(slaveVer))
	if masterMajVer > slaveMajVer {
		err = fmt.Errorf("master version(%s) must less than or equal to slave version(%s)", masterVer, slaveVer)
		return err
	}
	return nil
}

// GetMajorVersion 获取mysql的大版本号 From MySQL Version Parse 返回的大版本号码
//
//	@receiver versionNu
//	@return MajorVersion
func GetMajorVersion(versionNu uint64) (majorVersion string) {
	first := versionNu / 1000000
	second := (versionNu % 1000000) / 1000
	return fmt.Sprintf("%d.%d", first, second)
}

func mysqlVersionParse(re *regexp.Regexp, mysqlVersion string) uint64 {
	result := re.FindStringSubmatch(mysqlVersion)
	var (
		total    uint64
		billion  string
		thousand string
		single   string
		// 2.1.5  => 2 * 1000000 + 1 * 1000 + 5
	)
	switch len(result) {
	case 0:
		return 0
	case 4:
		billion = result[1]
		thousand = result[2]
		single = result[3]
		if billion != "" {
			b, err := strconv.ParseUint(billion, 10, 64)
			if err != nil {
				// log.Printf("%s", err)
				b = 0
			}
			total += b * 1000000
		}
		if thousand != "" {
			t, err := strconv.ParseUint(thousand, 10, 64)
			if err != nil {
				// log.Printf("%s", err)
				t = 0
			}
			total += t * 1000
		}
		if single != "" {
			s, err := strconv.ParseUint(single, 10, 64)
			if err != nil {
				s = 0
			}
			total += s
		}
	default:
		return 0
	}
	return total
}

// GenMysqlServerId  生成my.cnf 里面的server_id
//
//	@receiver ip
//	@receiver port
//	@return uint64
//	@return error
func GenMysqlServerId(ip string, port int) (uint64, error) {
	var (
		ips   = strings.Split(ip, ".")
		err   error
		first int
	)
	if len(ips) != 4 {
		err = fmt.Errorf("len(ips) is not 4. ips:%+v", ips)
		return 0, err
	}
	firstcol, err := strconv.Atoi(ips[0])
	if err != nil {
		return 0, err
	}
	first = (firstcol % 9) + 1
	first += (port % 10000 % 64) * 4
	two, err := strconv.ParseInt(ips[1], 10, 64)
	if err != nil {
		return 0, err
	}

	three, err := strconv.ParseInt(ips[2], 10, 64)
	if err != nil {
		return 0, err
	}
	four, err := strconv.ParseInt(ips[3], 10, 64)
	if err != nil {
		return 0, err
	}

	logger.Info("one:%d,two:%d,three:%d,four:%d", first, two, three, four)

	serverId := fmt.Sprintf("%08b%08b%08b%08b", first, two, three, four)
	logger.Info("serverID:%s\n", serverId)
	return strconv.ParseUint(serverId, 2, 64)
}

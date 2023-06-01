package redistest

import (
	"encoding/json"
	"fmt"
	"regexp"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/atomjobs/atomredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// RedisBackupTest 安装测试
type RedisBackupTest struct {
	atomredis.RedisBackupParams
	Err error `json:"-"`
}

// SetBkBizID 设置 BkBizID
func (test *RedisBackupTest) SetBkBizID(bkBizID string) *RedisBackupTest {
	if test.Err != nil {
		return test
	}
	if bkBizID == "" {
		bkBizID = "testapp"
	}
	test.BkBizID = bkBizID
	return test
}

// SetDomain set domain,传入为空则填充 cache.hello.testapp.db
func (test *RedisBackupTest) SetDomain(domain string) *RedisBackupTest {
	if test.Err != nil {
		return test
	}
	if domain == "" {
		domain = "cache.hello.testapp.db"
	}
	test.Domain = domain
	return test
}

// SetIP set ip,传入为空则自动获取本地ip
func (test *RedisBackupTest) SetIP(ip string) *RedisBackupTest {
	if test.Err != nil {
		return test
	}
	if ip == "" || ip == "127.0.0.1" {
		ip, test.Err = util.GetLocalIP()
		if test.Err != nil {
			return test
		}
	}
	test.IP = ip
	return test
}

// SetPorts set ports
// 如果ports=[],startPort=0,instNum=0,则默认startPort=40000,instNum=4
func (test *RedisBackupTest) SetPorts(ports []int, startPort, instNum int) *RedisBackupTest {
	if test.Err != nil {
		return test
	}
	if len(ports) == 0 {
		if startPort == 0 {
			startPort = consts.TestTendisPlusMasterStartPort
		}
		if instNum == 0 {
			instNum = 4
		}
		for i := 0; i < instNum; i++ {
			ports = append(ports, startPort+i)
		}
	}
	test.Ports = ports
	test.StartPort = startPort
	test.InstNum = instNum
	return test
}

// SetBackupType 设置备份类型
func (test *RedisBackupTest) SetBackupType(backupType string) *RedisBackupTest {
	if test.Err != nil {
		return test
	}
	if backupType == "" {
		backupType = consts.NormalBackupType
	}
	test.BackupType = backupType
	return test
}

// SetWithoutToBackupSys 是否上传备份系统
func (test *RedisBackupTest) SetWithoutToBackupSys(backupType bool) *RedisBackupTest {
	if test.Err != nil {
		return test
	}
	test.WithoutToBackupSys = backupType
	return test
}

// SetSSDLogCount 设置ssd log-count参数
func (test *RedisBackupTest) SetSSDLogCount(logParam *atomredis.TendisSSDSetLogCount) *RedisBackupTest {
	if test.Err != nil {
		return test
	}
	if logParam == nil {
		return test
	}
	test.SSDLogCount = *logParam
	return test
}

// RunBackup 执行 backup 原子任务
func (test *RedisBackupTest) RunBackup() (backupRetBase64 string) {
	msg := fmt.Sprintf("=========Backup test start============")
	fmt.Println(msg)

	defer func() {
		if test.Err != nil {
			msg = fmt.Sprintf("=========Backup test fail============")
		} else {
			msg = fmt.Sprintf("=========Backup test success============")
		}
		fmt.Println(msg)
	}()

	paramBytes, _ := json.Marshal(test)
	// fmt.Printf("-------payload(raw)--------\n%s\n\n", string(paramBytes))
	// encodeStr := base64.StdEncoding.EncodeToString(paramBytes)
	instllCmd := fmt.Sprintf(consts.ActuatorTestCmd, atomredis.NewRedisBackup().Name(), string(paramBytes))
	fmt.Println(instllCmd)
	backupRetBase64, test.Err = util.RunBashCmd(instllCmd, "", nil, 1*time.Hour)
	if test.Err != nil {
		return
	}
	fmt.Println(backupRetBase64)
	return
}

// Backup Test 备份
func Backup(serverIP string, ports []int, startPort, instNum int, ssdLogCountParam *atomredis.TendisSSDSetLogCount) (
	backupRetBase64 string, err error) {
	backupTest := RedisBackupTest{}
	backupTest.SetBkBizID("testapp").
		SetIP(serverIP).SetPorts(ports, startPort, instNum).
		SetDomain("cache.hello.testapp.db").
		SetBackupType(consts.NormalBackupType).
		SetWithoutToBackupSys(true).
		SetSSDLogCount(ssdLogCountParam)
	if backupTest.Err != nil {
		return
	}
	backupRet := backupTest.RunBackup()
	if backupTest.Err != nil {
		return
	}
	reg := regexp.MustCompile(`<ctx>(?U)(.*)</ctx>`)
	slice01 := reg.FindStringSubmatch(backupRet)
	if len(slice01) != 2 {
		err = fmt.Errorf("backup result not <ctx></ctx>?, backup result:%s", backupRet)
		return
	}
	return slice01[1], backupTest.Err
}

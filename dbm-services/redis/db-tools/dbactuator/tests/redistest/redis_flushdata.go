package redistest

import (
	"encoding/json"
	"fmt"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/atomjobs/atomredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// RedisFlushDataTest  redis清档
type RedisFlushDataTest struct {
	atomredis.RedisFlushDataParams
	Err error `json:"-"`
}

// SetIP set ip,传入为空则自动获取本地ip
func (test *RedisFlushDataTest) SetIP(ip string) *RedisFlushDataTest {
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

// SetDbType db type
func (test *RedisFlushDataTest) SetDbType(dbType string) *RedisFlushDataTest {
	if test.Err != nil {
		return test
	}
	test.DbType = dbType
	return test
}

// SetPorts set port
func (test *RedisFlushDataTest) SetPorts(ports []int, startPort, instNum int) *RedisFlushDataTest {
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
	return test
}

// SetForce 是否强制
func (test *RedisFlushDataTest) SetForce(force bool) *RedisFlushDataTest {
	if test.Err != nil {
		return test
	}
	test.IsForce = force
	return test
}

// SetPwd set pwd
func (test *RedisFlushDataTest) SetPwd(pwd string) *RedisFlushDataTest {
	if test.Err != nil {
		return test
	}
	test.Password = pwd
	return test
}

// SetDbList db list
func (test *RedisFlushDataTest) SetDbList(dbList []int) *RedisFlushDataTest {
	if test.Err != nil {
		return test
	}
	test.DBList = dbList
	return test
}

// SetFlushAll ..
func (test *RedisFlushDataTest) SetFlushAll(flushall bool) *RedisFlushDataTest {
	if test.Err != nil {
		return test
	}
	test.IsFlushAll = flushall
	return test
}

// SetTest set test
func (test *RedisFlushDataTest) SetTest() *RedisFlushDataTest {
	if test.Err != nil {
		return test
	}
	test.Debug = true
	return test
}

// RunRedisFlushData flush data
func (test *RedisFlushDataTest) RunRedisFlushData() {
	msg := fmt.Sprintf("=========RunRedisFlushData start============")
	fmt.Println(msg)

	defer func() {
		if test.Err != nil {
			msg = fmt.Sprintf("=========RunRedisFlushData fail============")
		} else {
			msg = fmt.Sprintf("=========RunRedisFlushData success============")
		}
		fmt.Println(msg)
	}()

	paramBytes, _ := json.Marshal(test)
	cmd := fmt.Sprintf(consts.ActuatorTestCmd, atomredis.NewRedisFlushData().Name(), string(paramBytes))
	fmt.Println(cmd)
	_, test.Err = util.RunBashCmd(cmd, "", nil, 1*time.Hour)
	if test.Err != nil {
		return
	}
	return
}

// FlushData 清理数据
func FlushData(serverIP string, dbType, pwd string, ports []int, startPort, instNum int) (err error) {
	flushTest := RedisFlushDataTest{}
	flushTest.SetIP(serverIP).SetPorts(ports, startPort, instNum).
		SetDbType(dbType).SetForce(true).SetFlushAll(true).
		SetPwd(pwd)
	if flushTest.Err != nil {
		return
	}

	flushTest.RunRedisFlushData()
	return flushTest.Err
}

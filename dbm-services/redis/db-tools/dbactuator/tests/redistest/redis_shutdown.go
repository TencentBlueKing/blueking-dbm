package redistest

import (
	"encoding/json"
	"fmt"
	"sync"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/atomjobs/atomredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// RedisShutDownTest  redis实例下架
type RedisShutDownTest struct {
	atomredis.RedisShutdownParams
	Err error `json:"-"`
}

// SetIP set ip,传入为空则自动获取本地ip
func (test *RedisShutDownTest) SetIP(ip string) *RedisShutDownTest {
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

// SetPorts set port
func (test *RedisShutDownTest) SetPorts(ports []int, startPort, instNum int) *RedisShutDownTest {
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

// SetTest set test
func (test *RedisShutDownTest) SetTest() *RedisShutDownTest {
	if test.Err != nil {
		return test
	}
	test.Debug = true
	return test
}

// RunRedisShutdown redis实例停止
func (test *RedisShutDownTest) RunRedisShutdown() {
	msg := fmt.Sprintf("=========RedisShutDownTest start============")
	fmt.Println(msg)

	defer func() {
		if test.Err != nil {
			msg = fmt.Sprintf("=========RedisShutDownTest fail============")
		} else {
			msg = fmt.Sprintf("=========RedisShutDownTest success============")
		}
		fmt.Println(msg)
	}()

	paramBytes, _ := json.Marshal(test)
	cmd := fmt.Sprintf(consts.ActuatorTestCmd, atomredis.NewRedisShutdown().Name(), string(paramBytes))
	fmt.Println(cmd)
	_, test.Err = util.RunBashCmd(cmd, "", nil, 1*time.Hour)
	if test.Err != nil {
		return
	}
	return
}

// RedisShutdown redis关闭测试
func RedisShutdown(serverIP string, masterStartPort, slaveStartPort, insNum int) (err error) {
	slaveShutdownTest := RedisShutDownTest{}
	slaveShutdownTest.SetIP(serverIP).SetPorts([]int{}, masterStartPort, insNum).SetTest()
	if slaveShutdownTest.Err != nil {
		return slaveShutdownTest.Err
	}

	masterShutdownTest := RedisShutDownTest{}
	masterShutdownTest.SetIP(serverIP).SetPorts([]int{}, slaveStartPort, insNum).SetTest()
	if masterShutdownTest.Err != nil {
		return masterShutdownTest.Err
	}

	wg := sync.WaitGroup{}
	wg.Add(2)
	go func() {
		defer wg.Done()

		slaveShutdownTest.RunRedisShutdown()
	}()
	go func() {
		defer wg.Done()
		masterShutdownTest.RunRedisShutdown()
	}()
	wg.Wait()
	if slaveShutdownTest.Err != nil {
		return slaveShutdownTest.Err
	}

	if masterShutdownTest.Err != nil {
		return masterShutdownTest.Err
	}

	return nil
}

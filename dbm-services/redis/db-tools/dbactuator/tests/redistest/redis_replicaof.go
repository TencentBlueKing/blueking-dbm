package redistest

import (
	"dbm-services/redis/db-tools/dbactuator/pkg/atomjobs/atomredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
	"encoding/json"
	"fmt"
	"time"
)

// RedisReplicaofTest 建立主从关系测试
type RedisReplicaofTest struct {
	BatchPairs []atomredis.ReplicaBatchItem `json:"bacth_pairs" validate:"required"`
	Err        error                        `json:"-"`
}

// SetMasterIP 设置master ip
func (test *RedisReplicaofTest) SetMasterIP(masterIP string) *RedisReplicaofTest {
	if test.Err != nil {
		return test
	}
	if len(test.BatchPairs) == 0 {
		test.BatchPairs = append(test.BatchPairs, atomredis.ReplicaBatchItem{})
	}
	if masterIP == "" {
		test.Err = fmt.Errorf("RedisReplicaofTest masterIP cannot be empty")
		fmt.Println(test.Err.Error())
		return test
	}
	test.BatchPairs[0].MasterIP = masterIP
	return test
}

// SetMasterPorts 设置master start port
func (test *RedisReplicaofTest) SetMasterPorts(startPort, instNum int) *RedisReplicaofTest {
	if test.Err != nil {
		return test
	}
	if startPort == 0 {
		test.Err = fmt.Errorf("RedisReplicaofTest masterStartPort cannot be 0")
		fmt.Println(test.Err.Error())
		return test
	}
	if instNum == 0 {
		test.Err = fmt.Errorf("RedisReplicaofTest masterStartPort cannot be 0")
		fmt.Println(test.Err.Error())
		return test
	}
	if len(test.BatchPairs) == 0 {
		test.BatchPairs = append(test.BatchPairs, atomredis.ReplicaBatchItem{})
	}
	test.BatchPairs[0].MasterStartPort = startPort
	test.BatchPairs[0].MasterInstNum = instNum
	return test
}

// SetMasterAuth 设置masterAuth
func (test *RedisReplicaofTest) SetMasterAuth(masterAuth string) *RedisReplicaofTest {
	if test.Err != nil {
		return test
	}
	if masterAuth == "" {
		test.Err = fmt.Errorf("RedisReplicaofTest masterAuth cannot be empty")
		fmt.Println(test.Err.Error())
		return test
	}
	if len(test.BatchPairs) == 0 {
		test.BatchPairs = append(test.BatchPairs, atomredis.ReplicaBatchItem{})
	}
	test.BatchPairs[0].MasterAuth = masterAuth
	return test
}

// SetSlaveIP 设置slave ip
func (test *RedisReplicaofTest) SetSlaveIP(slaveIP string) *RedisReplicaofTest {
	if test.Err != nil {
		return test
	}
	if slaveIP == "" {
		test.Err = fmt.Errorf("RedisReplicaofTest slaveIP cannot be empty")
		fmt.Println(test.Err.Error())
		return test
	}
	test.BatchPairs[0].SlaveIP = slaveIP
	return test
}

// SetSlavePorts 设置slave start port
func (test *RedisReplicaofTest) SetSlavePorts(startPort, instNum int) *RedisReplicaofTest {
	if test.Err != nil {
		return test
	}
	if startPort == 0 {
		test.Err = fmt.Errorf("RedisReplicaofTest slaveStartPort cannot be 0")
		fmt.Println(test.Err.Error())
		return test
	}
	if instNum == 0 {
		test.Err = fmt.Errorf("RedisReplicaofTest slaveStartPort cannot be 0")
		fmt.Println(test.Err.Error())
		return test
	}
	if len(test.BatchPairs) == 0 {
		test.BatchPairs = append(test.BatchPairs, atomredis.ReplicaBatchItem{})
	}
	test.BatchPairs[0].SlaveStartPort = startPort
	test.BatchPairs[0].SlaveInstNum = instNum
	return test
}

// SetSlaveAuth 设置slaveAuth
func (test *RedisReplicaofTest) SetSlaveAuth(slavePassword string) *RedisReplicaofTest {
	if test.Err != nil {
		return test
	}
	if slavePassword == "" {
		test.Err = fmt.Errorf("RedisReplicaofTest slavePassword cannot be empty")
		fmt.Println(test.Err.Error())
		return test
	}
	if len(test.BatchPairs) == 0 {
		test.BatchPairs = append(test.BatchPairs, atomredis.ReplicaBatchItem{})
	}
	test.BatchPairs[0].SlavePassword = slavePassword
	return test
}

// RunReplicaOf 执行replicaof 原子任务
func (test *RedisReplicaofTest) RunReplicaOf() {
	msg := fmt.Sprintf("=========ReplicaOf test start============")
	fmt.Println(msg)

	defer func() {
		if test.Err != nil {
			msg = fmt.Sprintf("=========ReplicaOf test fail============")
		} else {
			msg = fmt.Sprintf("=========ReplicaOf test success============")
		}
		fmt.Println(msg)
	}()

	paramBytes, _ := json.Marshal(test)
	// fmt.Printf("-------payload(raw)--------\n%s\n\n", string(paramBytes))
	// encodeStr := base64.StdEncoding.EncodeToString(paramBytes)
	instllCmd := fmt.Sprintf(consts.ActuatorTestCmd, atomredis.NewRedisReplicaBatch().Name(), string(paramBytes))
	fmt.Println(instllCmd)
	_, test.Err = util.RunBashCmd(instllCmd, "", nil, 1*time.Hour)
	if test.Err != nil {
		return
	}
	return
}

// CreateReplicaof 建立主从关系
func CreateReplicaof(masterIP string, masterPort int, masterAuth string,
	slaveIP string, slavePort int, slaveAuth string) (err error) {
	replicaOfTest := RedisReplicaofTest{}
	replicaOfTest.SetMasterIP(masterIP).
		SetMasterPorts(masterPort, consts.TestRedisInstanceNum).
		SetMasterAuth(masterAuth).
		SetSlaveIP(slaveIP).
		SetSlavePorts(slavePort, consts.TestRedisInstanceNum).
		SetSlaveAuth(slaveAuth)
	if replicaOfTest.Err != nil {
		return replicaOfTest.Err
	}
	replicaOfTest.RunReplicaOf()
	if replicaOfTest.Err != nil {
		return replicaOfTest.Err
	}
	return nil
}

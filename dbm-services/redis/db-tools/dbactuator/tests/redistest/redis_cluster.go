package redistest

import (
	"dbm-services/redis/db-tools/dbactuator/pkg/atomjobs/atomredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
	"encoding/json"
	"fmt"
	"time"
)

// ClusterMeetTest 测试
type ClusterMeetTest struct {
	atomredis.ClusterMeetSlotsAssignParams
	Err error `json:"-"`
}

// SetPassword 设置密码
func (test *ClusterMeetTest) SetPassword(password string) *ClusterMeetTest {
	if test.Err != nil {
		return test
	}
	if password == "" {
		test.Err = fmt.Errorf("ClusterMeetTest password(%s) cannot be empty", password)
		fmt.Println(test.Err.Error())
		return test
	}
	test.Password = password
	return test
}

// SetSlotAutoAssign set slotAutoAssgin
func (test *ClusterMeetTest) SetSlotAutoAssign(slotAutoAssgin bool) *ClusterMeetTest {
	if test.Err != nil {
		return test
	}
	test.SlotsAutoAssgin = slotAutoAssgin
	return test
}

// SetUseForExpansion set use for expansion
func (test *ClusterMeetTest) SetUseForExpansion(isexpansion bool) *ClusterMeetTest {
	if test.Err != nil {
		return test
	}
	test.UseForExpansion = isexpansion
	return test
}

// SetClusterReplicaPairs set replicaPairs
func (test *ClusterMeetTest) SetClusterReplicaPairs(replicaItems []atomredis.ClusterReplicaItem) *ClusterMeetTest {
	if test.Err != nil {
		return test
	}
	if len(replicaItems) == 0 {
		test.Err = fmt.Errorf("ClusterMeetTest replicaPairs cannot be empty")
		fmt.Println(test.Err.Error())
		return test
	}
	test.ReplicaPairs = replicaItems
	return test
}

// RunClusterMeetAndSlotsAssign 建立集群关系和slots分配
func (test *ClusterMeetTest) RunClusterMeetAndSlotsAssign() {
	msg := fmt.Sprintf("=========ClusterMeetAndSlotsAssign test start============")
	fmt.Println(msg)

	defer func() {
		if test.Err != nil {
			msg = fmt.Sprintf("=========ClusterMeetAndSlotsAssign test fail============")
		} else {
			msg = fmt.Sprintf("=========ClusterMeetAndSlotsAssign test success============")
		}
		fmt.Println(msg)
	}()

	paramBytes, _ := json.Marshal(test)
	// fmt.Printf("-------payload(raw)--------\n%s\n\n", string(paramBytes))
	// encodeStr := base64.StdEncoding.EncodeToString(paramBytes)
	instllCmd := fmt.Sprintf(consts.ActuatorTestCmd, atomredis.NewClusterMeetSlotsAssign().Name(), string(paramBytes))
	fmt.Println(instllCmd)
	_, test.Err = util.RunBashCmd(instllCmd, "", nil, 1*time.Hour)
	if test.Err != nil {
		return
	}
	return
}

// CreateClusterREPL 创建redis cluster
func CreateClusterREPL(serverIP string, masterStartPort, slaveStartPort, instNum int,
	slotAutoAssign, useForExpansion bool) (err error) {
	// 建立cluster 关系
	replicaPairs := make([]atomredis.ClusterReplicaItem, 0, instNum)
	for i := 0; i < instNum; i++ {
		replicaPairs = append(replicaPairs, atomredis.ClusterReplicaItem{
			MasterIP:   serverIP,
			MasterPort: masterStartPort + i,
			SlaveIP:    serverIP,
			SlavePort:  slaveStartPort + i,
		})
	}
	plusClusterTest := ClusterMeetTest{}
	plusClusterTest.SetPassword(consts.RedisTestPasswd).
		SetSlotAutoAssign(slotAutoAssign).
		SetUseForExpansion(useForExpansion).
		SetClusterReplicaPairs(replicaPairs)
	if plusClusterTest.Err != nil {
		return plusClusterTest.Err
	}
	plusClusterTest.RunClusterMeetAndSlotsAssign()
	if plusClusterTest.Err != nil {
		return plusClusterTest.Err
	}
	return nil
}

// CreateRedisClusterREPL 创建redis cluster
func CreateRedisClusterREPL(serverIP string) (err error) {
	return CreateClusterREPL(serverIP,
		consts.TestRedisMasterStartPort,
		consts.TestRedisSlaveStartPort,
		consts.TestRedisInstanceNum, true, false)
}

// CreateTendisplusClusterREPL 创建tendisplus cluster
func CreateTendisplusClusterREPL(serverIP string) (err error) {
	return CreateClusterREPL(serverIP,
		consts.TestTendisPlusMasterStartPort,
		consts.TestTendisPlusSlaveStartPort,
		consts.TestRedisInstanceNum, true, false)
}

// CreateTendisplusREPL 创建主从
func CreateTendisplusREPL(serverIP string, masterStartPort, slaveStartPort, numbers int) (err error) {
	// 建立tendisplus 主从
	replicaPairs := make([]atomredis.ClusterReplicaItem, 0, numbers)
	for i := 0; i < numbers; i++ {
		replicaPairs = append(replicaPairs, atomredis.ClusterReplicaItem{
			MasterIP:   serverIP,
			MasterPort: masterStartPort + i,
			SlaveIP:    serverIP,
			SlavePort:  slaveStartPort + i,
		})
	}
	plusClusterTest := ClusterMeetTest{}
	plusClusterTest.SetPassword(consts.RedisTestPasswd).
		// SetSlotAutoAssign(true).
		// 部署扩容所需节点不分配slot
		SetSlotAutoAssign(false).
		SetUseForExpansion(true).
		SetClusterReplicaPairs(replicaPairs)
	if plusClusterTest.Err != nil {
		return plusClusterTest.Err
	}
	plusClusterTest.RunClusterMeetAndSlotsAssign()
	if plusClusterTest.Err != nil {
		return plusClusterTest.Err
	}
	return nil
}

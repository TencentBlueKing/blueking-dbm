package redistest

import (
	"encoding/json"
	"fmt"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/atomjobs/atomredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// RedisSceneTest 场景需求测试
type RedisSceneTest struct {
	killParam  atomredis.KillDeadParam
	syncParam  atomredis.DoSyncParam
	checkParam atomredis.CheckSyncParam
	Err        error `json:"-"`
}

// SetInatances 可配置 同步参数场景
func (test *RedisSceneTest) SetInatances(srcip, dstip string, startPort, sStartPort, instNum int) {
	if test.Err != nil {
		return
	}
	if srcip == "" || dstip == "" {
		test.Err = fmt.Errorf("bad input for ip[%s,%s]", srcip, dstip)
		return
	}
	if startPort == 0 {
		startPort = consts.TestTendisPlusMasterStartPort
	}

	if instNum == 0 {
		instNum = 4
	}
	for i := 0; i < instNum; i++ {
		port := startPort + i
		sport := sStartPort + i

		test.killParam.Instances = append(test.killParam.Instances, atomredis.InstanceParam{IP: srcip, Port: port})
		test.checkParam.Instances = append(test.checkParam.Instances, atomredis.InstanceParam{IP: dstip, Port: sport})
		test.syncParam.Instances = append(test.syncParam.Instances, atomredis.InstanceSwitchParam{
			MasterInfo: atomredis.InstanceParam{IP: srcip, Port: port},
			SlaveInfo:  atomredis.InstanceParam{IP: dstip, Port: sport}})
	}
}

// SetClusterType TODO
func (test *RedisSceneTest) SetClusterType(t string) {
	if test.Err != nil {
		return
	}

	test.checkParam.ClusterType = t
	test.checkParam.MaxSlaveLastIOSecondsAgo = 60
	test.checkParam.WatchSeconds = 600

	test.killParam.ClusterType = t
	test.killParam.ConnIdleTime = 600

	test.syncParam.ClusterType = t
	test.syncParam.ParamList = []string{"disk-delete-count", "maxmemory", "log-count", "log-keep-count",
		"slave-log-keep-count"}

}

// RunRedisKillConn redis实例停止
func (test *RedisSceneTest) RunRedisKillConn() error {
	msg := fmt.Sprintf("=========RedisKillConnTest start============")
	fmt.Println(msg)

	defer func() {
		if test.Err != nil {
			msg = fmt.Sprintf("=========RedisKillConnTest fail============")
		} else {
			msg = fmt.Sprintf("=========RedisKillConnTest success============")
		}
		fmt.Println(msg)
	}()

	paramBytes, _ := json.Marshal(test.killParam)
	cmd := fmt.Sprintf(consts.ActuatorTestCmd, atomredis.NewRedisSceneKillDeadConn().Name(), string(paramBytes))
	fmt.Println(cmd)
	_, test.Err = util.RunBashCmd(cmd, "", nil, 1*time.Hour)
	return test.Err
}

// RunRedisSyncParams TODO
// RunRedisShutdown redis实例停止
func (test *RedisSceneTest) RunRedisSyncParams() error {
	msg := fmt.Sprintf("=========RedisSyncParamsTest start============")
	fmt.Println(msg)

	defer func() {
		if test.Err != nil {
			msg = fmt.Sprintf("=========RedisSyncParamsTest fail============")
		} else {
			msg = fmt.Sprintf("=========RedisSyncParamsTest success============")
		}
		fmt.Println(msg)
	}()

	paramBytes, _ := json.Marshal(test.syncParam)
	cmd := fmt.Sprintf(consts.ActuatorTestCmd, atomredis.NewRedisSceneSyncPrams().Name(), string(paramBytes))
	fmt.Println(cmd)
	_, test.Err = util.RunBashCmd(cmd, "", nil, 1*time.Hour)
	return test.Err
}

// RunRedisCheckSyncStatus TODO
// RunRedisShutdown redis实例停止
func (test *RedisSceneTest) RunRedisCheckSyncStatus() error {
	msg := fmt.Sprintf("=========RedisCheckSyncStatusTest start============")
	fmt.Println(msg)

	defer func() {
		if test.Err != nil {
			msg = fmt.Sprintf("=========RedisCheckSyncStatusTest fail============")
		} else {
			msg = fmt.Sprintf("=========RedisCheckSyncStatusTest success============")
		}
		fmt.Println(msg)
	}()

	paramBytes, _ := json.Marshal(test.checkParam)
	cmd := fmt.Sprintf(consts.ActuatorTestCmd, atomredis.NewRedisSceneSyncCheck().Name(), string(paramBytes))
	fmt.Println(cmd)
	_, test.Err = util.RunBashCmd(cmd, "", nil, 1*time.Hour)
	return test.Err
}

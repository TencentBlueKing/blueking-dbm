// Package redistest redis切换测试
package redistest

import (
	"encoding/json"
	"fmt"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/atomjobs/atomredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// RedisSwitchTest 集群切换 单元测试
type RedisSwitchTest struct {
	atomredis.SwitchParam
	Err error `json:"-"`
}

/*测试集群架构:
													1.1.a.1:40000          1.1b.1:41000
	1.1.a.1:50000           1.1.a.1:40001          1.1.1.b:41001
                          1.1.1.1:40002          1.1.b.1:41002
--------------------------------------------------------------
													1.1.a.1:42000					 1.1.b.1:43000
													1.1.a.1:42001					 1.1.b.1:43001
*/

// SetDefaultClusterMeta 设置集群元数据
func (test *RedisSwitchTest) SetDefaultClusterMeta(ppass, spass string) *RedisSwitchTest {
	if test.Err != nil {
		return test
	}
	test.ClusterMeta.BkBizID = 119
	test.ClusterMeta.ImmuteDomain = "cache1.hitest.testapp.db"
	test.ClusterMeta.ProxyPassword = ppass
	test.ClusterMeta.StoragePassword = spass
	return test
}

// SetClusterType 设置集群元数据ClusterType
func (test *RedisSwitchTest) SetClusterType(ctp string) *RedisSwitchTest {
	if test.Err != nil {
		return test
	}
	test.ClusterMeta.ClusterType = ctp
	return test
}

// SetProxySet 设置集群元数据ProxySet
func (test *RedisSwitchTest) SetProxySet(proxyAddr string) *RedisSwitchTest {
	if test.Err != nil {
		return test
	}
	test.ClusterMeta.ProxySet = []string{proxyAddr}
	return test
}

// SetMasterSet 设置集群元数据RedisMasterSet
func (test *RedisSwitchTest) SetMasterSet(addrs []string) *RedisSwitchTest {
	if test.Err != nil {
		return test
	}

	test.ClusterMeta.RedisMasterSet = addrs
	return test
}

// SetSlaveSet 设置集群元数据RedisSlaveSet
func (test *RedisSwitchTest) SetSlaveSet(addrs []string) *RedisSwitchTest {
	if test.Err != nil {
		return test
	}
	test.ClusterMeta.RedisSlaveSet = addrs
	return test
}

// SetSwitchInfo 设置集群元数据SwitchRelation
func (test *RedisSwitchTest) SetSwitchInfo(sinfos []atomredis.InstanceSwitchParam) *RedisSwitchTest {
	if test.Err != nil {
		return test
	}
	test.SwitchRelation = sinfos
	return test
}

// SetDefaultSwitchCondition 配置默认切换行为 可选值 [msms|mms]
func (test *RedisSwitchTest) SetDefaultSwitchCondition(stp string) *RedisSwitchTest {
	if test.Err != nil {
		return test
	}
	test.SyncCondition.IsCheckSync = true
	test.SyncCondition.MaxSlaveMasterDiffTime = 61
	test.SyncCondition.MaxSlaveLastIOSecondsAgo = 100
	test.SyncCondition.CanWriteBeforeSwitch = false

	if stp == "" {
		test.SyncCondition.InstanceSyncType = "msms"
	} else {
		test.SyncCondition.InstanceSyncType = stp
	}
	return test
}

// RunTendisSwitch 执行 tendis  切换测试
func (test *RedisSwitchTest) RunTendisSwitch() {
	fmt.Println("=========tendisSwitch test start============")

	defer func() {
		var msg string
		if test.Err != nil {
			msg = "=========tendisSwitch test fail============"
			fmt.Println(test.Err)
		} else {
			msg = "=========tendisSwitch test success============"
		}
		fmt.Println(msg)
	}()

	paramBytes, _ := json.Marshal(test)
	cmd := fmt.Sprintf(consts.ActuatorTestCmd, atomredis.NewRedisSwitch().Name(), string(paramBytes))
	fmt.Println(cmd)
	_, test.Err = util.RunBashCmd(cmd, "", nil, 1*time.Hour)
	if test.Err != nil {
		fmt.Printf("run bash cmd failed :+%+v", test.Err)
		return
	}
}

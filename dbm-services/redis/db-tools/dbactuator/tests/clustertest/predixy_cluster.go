package clustertest

import (
	"fmt"

	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/tests/proxytest"
	"dbm-services/redis/db-tools/dbactuator/tests/redistest"
)

// PredixyTendisplusClusterInstallTest predixy+tendisplus cluster集群安装测试
func PredixyTendisplusClusterInstallTest(serverIP,
	tendisplusPkgName, tendisplusPkgMd5,
	dbtoolsPkgName, dbtoolsPkgMd5,
	predixyPkgName, predixyPkgMd5 string) (err error) {
	// 先清理
	redistest.TendisplusMasterClear(serverIP, consts.TendisTypePredixyTendisplusCluster, true)
	redistest.TendisplusSlaveClear(serverIP, consts.TendisTypePredixyTendisplusCluster, true)
	proxytest.PredixyClear(serverIP, consts.TestPredixyPort, true)
	// 再安装tendisplus
	err = redistest.TendisplusMasterInstall(serverIP, tendisplusPkgName, tendisplusPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5, consts.TendisTypePredixyTendisplusCluster)
	if err != nil {
		return
	}
	err = redistest.TendisplusSlaveInstall(serverIP, tendisplusPkgName, tendisplusPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5, consts.TendisTypePredixyTendisplusCluster)
	if err != nil {
		return
	}

	err = redistest.CreateTendisplusClusterREPL(serverIP)
	if err != nil {
		return
	}

	err = proxytest.PredixyInstall(serverIP, predixyPkgName, predixyPkgMd5,
		consts.TendisTypePredixyTendisplusCluster,
		consts.TestTendisPlusMasterStartPort, consts.TestRedisInstanceNum,
		consts.TestPredixyPort,
	)
	if err != nil {
		return
	}

	// 写入数据
	cmdTest, err := redistest.NewCommandTest(serverIP, consts.TestPredixyPort, consts.ProxyTestPasswd,
		consts.TendisTypeRedisInstance, 0)
	if err != nil {
		return err
	}
	cmdTest.StringTest()
	if cmdTest.Err != nil {
		return cmdTest.Err
	}
	cmdTest.HashTest()
	if cmdTest.Err != nil {
		return cmdTest.Err
	}
	cmdTest.ZsetTest()
	if cmdTest.Err != nil {
		return cmdTest.Err
	}
	cmdTest.ListTest()
	if cmdTest.Err != nil {

		return cmdTest.Err
	}
	return nil
}

// TendisplusScaleNodesInstall tendisplus cluster集群安装测试，扩容节点
func TendisplusScaleNodesInstall(serverIP,
	tendisplusPkgName, tendisplusPkgMd5,
	dbtoolsPkgName, dbtoolsPkgMd5,
	predixyPkgName, predixyPkgMd5 string,
	masterStartPort, slaveStartPort, numbers int) (err error) {
	fmt.Println("=========TendisplusScaleNodesInstall============")
	// 不清理
	redistest.TendisplusClear(serverIP, consts.TendisTypePredixyTendisplusCluster,
		true, masterStartPort, numbers)
	redistest.TendisplusClear(serverIP, consts.TendisTypePredixyTendisplusCluster,
		true, slaveStartPort, numbers)
	// 安装tendisplus
	err = redistest.TendisplusInstall(serverIP, tendisplusPkgName, tendisplusPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5, consts.TendisTypePredixyTendisplusCluster,
		masterStartPort, numbers)
	if err != nil {
		return
	}
	err = redistest.TendisplusInstall(serverIP, tendisplusPkgName, tendisplusPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5, consts.TendisTypePredixyTendisplusCluster,
		slaveStartPort, numbers)
	if err != nil {
		return
	}

	err = redistest.CreateTendisplusREPL(serverIP, masterStartPort, slaveStartPort, numbers)
	if err != nil {
		return
	}
	return nil
}

// PredixyTendisplusClusterClear predixy+tendisplus_cluster清理
func PredixyTendisplusClusterClear(serverIP string, clearDataDir bool) (err error) {
	proxytest.PredixyClear(serverIP, consts.TestPredixyPort, clearDataDir)
	// master清理时, /usr/local/redis 先保留
	redistest.TendisplusClear(serverIP, consts.TendisTypePredixyTendisplusCluster,
		clearDataDir, consts.TestTendisPlusMasterStartPort, consts.TestRedisInstanceNum)
	redistest.TendisplusClear(serverIP, consts.TendisTypePredixyTendisplusCluster,
		clearDataDir, consts.TestTendisPlusSlaveStartPort, consts.TestRedisInstanceNum)

	redistest.TendisplusClear(serverIP, consts.TendisTypePredixyTendisplusCluster,
		clearDataDir, consts.ExpansionTestTendisPlusMasterStartPort, consts.ExpansionTestRedisInstanceNum)
	redistest.TendisplusClear(serverIP, consts.TendisTypePredixyTendisplusCluster,
		clearDataDir, consts.ExpansionTestTendisPlusSlaveStartPort, consts.ExpansionTestRedisInstanceNum)

	redistest.TendisplusClear(serverIP, consts.TendisTypePredixyTendisplusCluster,
		clearDataDir, consts.SlotTestTendisPlusMasterPort, consts.SLotTestRedisInstanceNum)
	redistest.TendisplusClear(serverIP, consts.TendisTypePredixyTendisplusCluster,
		clearDataDir, consts.SLotTestTendisPlusSlaveStart, consts.SLotTestRedisInstanceNum)

	return nil
}

// TendisPlusRebalence tendisplus 集群扩容
func TendisPlusRebalence(localIP string) (err error) {
	err = redistest.Rebalance(localIP, consts.RedisTestPasswd, consts.TestTendisPlusMasterStartPort,
		consts.ExpansionTestTendisPlusMasterStartPort)
	if err != nil {
		return err
	}
	return nil
}

// TendisPlusMigrateSpecificSlots 迁移指定slot
func TendisPlusMigrateSpecificSlots(localIP string) (err error) {
	err = redistest.MigrateSpecificSlots(localIP, consts.RedisTestPasswd,
		consts.TestTendisPlusMasterStartPort, consts.SlotTestTendisPlusMasterPort)
	if err != nil {
		return err
	}
	return nil
}

// PredixyRedisClusterInstallTest predixy+redisCluster 集群安装测试
func PredixyRedisClusterInstallTest(serverIP,
	redisPkgName, redisPkgMd5,
	dbtoolsPkgName, dbtoolsPkgMd5,
	predixyPkgName, predixyPkgMd5 string) (err error) {
	// 先清理
	redistest.RedisInstanceMasterClear(serverIP, consts.TendisTypePredixyRedisCluster, true)
	redistest.RedisInstanceSlaveClear(serverIP, consts.TendisTypePredixyRedisCluster, true)
	proxytest.PredixyClear(serverIP, consts.TestPredixyPort, true)
	return

	// 安装 redis_master 和 redis_slave
	err = redistest.RedisInstanceMasterInstall(serverIP, redisPkgName, redisPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5, consts.TendisTypePredixyRedisCluster)
	if err != nil {
		return
	}

	err = redistest.RedisInstanceSlaveInstall(serverIP, redisPkgName, redisPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5, consts.TendisTypePredixyRedisCluster)
	if err != nil {
		return
	}

	redistest.CreateClusterREPL(serverIP,
		consts.TestRedisMasterStartPort,
		consts.TestRedisSlaveStartPort,
		consts.TestRedisInstanceNum, true, false,
	)

	err = proxytest.PredixyInstall(serverIP, predixyPkgName, predixyPkgMd5,
		consts.TendisTypePredixyTendisplusCluster,
		consts.TestRedisMasterStartPort, consts.TestRedisInstanceNum,
		consts.TestPredixyPort,
	)
	if err != nil {
		return
	}

	// 写入数据
	cmdTest, err := redistest.NewCommandTest(serverIP, consts.TestPredixyPort, consts.ProxyTestPasswd,
		consts.TendisTypeRedisInstance, 0)
	if err != nil {
		return err
	}
	cmdTest.StringTest()
	if cmdTest.Err != nil {
		return cmdTest.Err
	}
	cmdTest.HashTest()
	if cmdTest.Err != nil {
		return cmdTest.Err
	}
	cmdTest.ZsetTest()
	if cmdTest.Err != nil {
		return cmdTest.Err
	}
	cmdTest.ListTest()
	if cmdTest.Err != nil {
		return cmdTest.Err
	}
	return nil
}

// PredixyTendisplusClusterForgetTest predixy+tendisplus cluster集群Forget
func PredixyTendisplusClusterForgetTest(serverIP,
	tendisplusPkgName, tendisplusPkgMd5,
	dbtoolsPkgName, dbtoolsPkgMd5 string) (err error) {
	forgetNodeNum := 2

	fmt.Println("==================================================")
	// 先清理🧹
	if err = redistest.TendisplusClear(serverIP,
		consts.TendisTypePredixyTendisplusCluster, true,
		consts.TestTendisPlusForgetPort, forgetNodeNum,
	); err != nil {
		return
	}

	// 再安装tendisplus
	if err = redistest.TendisplusInstall(
		serverIP, tendisplusPkgName, tendisplusPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5,
		consts.TendisTypePredixyTendisplusCluster,
		consts.TestTendisPlusForgetPort, forgetNodeNum); err != nil {
		return
	}

	// 加入集群
	if err = redistest.ClusterMeetSingleNode(serverIP,
		consts.TestTendisPlusForgetPort, forgetNodeNum,
	); err != nil {
		return
	}

	forgetTest := redistest.ClusterForgetTest{}
	forgetTest.SetClusterMeta(serverIP, consts.TestTendisPlusMasterStartPort,
		consts.TestRedisInstanceNum)
	forgetTest.SetForgetList(serverIP, consts.TestTendisPlusForgetPort, forgetNodeNum)
	forgetTest.RunClusterForget()

	// 清理🧹
	if err = redistest.TendisplusClear(serverIP,
		consts.TendisTypePredixyTendisplusCluster, true,
		consts.TestTendisPlusForgetPort, forgetNodeNum,
	); err != nil {
		return
	}
	fmt.Println("==================================================")
	return nil
}

package clustertest

import (
	"dbm-services/redis/db-tools/dbactuator/pkg/atomjobs/atomredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/tests/redistest"
	"fmt"
)

// PredixyTendisPlusSwitchTest predixy+tendisplus cluster切换测试
func PredixyTendisPlusSwitchTest(serverIP,
	tendisplusPkgName, tendisplusPkgMd5,
	dbtoolsPkgName, dbtoolsPkgMd5 string) (err error) {
	fmt.Println(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
	fmt.Println("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
	return nil

	redistest.TendisplusSyncMasterClear(serverIP, consts.TendisTypePredixyTendisplusCluster, true)
	redistest.TendisplusSyncSlaveClear(serverIP, consts.TendisTypePredixyTendisplusCluster, true)

	err = redistest.TendisplusSyncMasterInstall(serverIP,
		tendisplusPkgName, tendisplusPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5,
		consts.TendisTypePredixyTendisplusCluster)
	if err != nil {
		return
	}

	err = redistest.TendisplusSyncSlaveInstall(serverIP,
		tendisplusPkgName, tendisplusPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5,
		consts.TendisTypePredixyTendisplusCluster)
	if err != nil {
		return
	}

	// 建立tendisplus cluster
	replicaPairs := make([]atomredis.ClusterReplicaItem, 0, consts.TestRedisInstanceNum)
	for i := 0; i < consts.TestRedisInstanceNum; i++ {
		replicaPairs = append(replicaPairs, atomredis.ClusterReplicaItem{
			MasterIP:   serverIP,
			MasterPort: consts.TestSyncTendisPlusMasterStartPort + i,
			SlaveIP:    serverIP,
			SlavePort:  consts.TestSyncTendisPlusSlaveStartPort + i,
		})
	}
	plusClusterTest := redistest.ClusterMeetTest{}
	plusClusterTest.SetPassword(consts.RedisTestPasswd).
		SetSlotAutoAssign(true).
		SetClusterReplicaPairs(replicaPairs)
	if plusClusterTest.Err != nil {
		return plusClusterTest.Err
	}
	plusClusterTest.RunClusterMeetAndSlotsAssign()
	if plusClusterTest.Err != nil {
		return plusClusterTest.Err
	}
	// TODO (新实例加入集群中。。s)

	return DoSwitchActionTest(serverIP,
		consts.TestPredixyPort,
		consts.TestTendisPlusMasterStartPort,
		consts.TestTendisPlusSlaveStartPort,
		consts.TestSyncTendisPlusMasterStartPort,
		consts.TestSyncTendisPlusSlaveStartPort,
		consts.TendisTypePredixyTendisplusCluster)
}

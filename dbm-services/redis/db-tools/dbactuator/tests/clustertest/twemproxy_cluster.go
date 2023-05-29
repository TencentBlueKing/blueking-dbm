package clustertest

import (
	"dbm-services/redis/db-tools/dbactuator/pkg/atomjobs/atomredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/tests/proxytest"
	"dbm-services/redis/db-tools/dbactuator/tests/redistest"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"path/filepath"
)

// TwemproxyRedisInstanceInstall twemproxy + redisinstance 集群安装
func TwemproxyRedisInstanceInstall(serverIP,
	redisPkgName, redisPkgMd5,
	dbtoolsPkgName, dbtoolsPkgMd5,
	twemproxyPkgName, twemproxyPkgMd5 string) (err error) {

	// 先清理再安装
	err = redistest.RedisInstanceMasterClear(serverIP, consts.TendisTypeTwemproxyRedisInstance, true)
	if err != nil {
		return
	}
	err = redistest.RedisInstanceSlaveClear(serverIP, consts.TendisTypeTwemproxyRedisInstance, true)
	if err != nil {
		return
	}
	// 安装master
	err = redistest.RedisInstanceMasterInstall(serverIP, redisPkgName, redisPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5, consts.TendisTypeTwemproxyRedisInstance)
	if err != nil {
		return
	}

	err = redistest.RedisInstanceSlaveInstall(serverIP, redisPkgName, redisPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5, consts.TendisTypeTwemproxyRedisInstance)
	if err != nil {
		return
	}

	// 建立主从关系
	err = redistest.CreateReplicaof(serverIP, consts.TestRedisMasterStartPort, consts.RedisTestPasswd,
		serverIP, consts.TestRedisSlaveStartPort, consts.RedisTestPasswd)
	if err != nil {
		return
	}

	// 安装twemproxy
	err = proxytest.TwemproxyInstall(serverIP, twemproxyPkgName, twemproxyPkgMd5,
		consts.TendisTypeTwemproxyRedisInstance,
		consts.TestRedisMasterStartPort, consts.TestRedisInstanceNum,
		consts.TestTwemproxyPort)
	if err != nil {
		return
	}

	// 写入数据测试
	cmdTest, err := redistest.NewCommandTest(serverIP, consts.TestTwemproxyPort, consts.ProxyTestPasswd,
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

// TwemproxyRedisInstanceClear twemproxy+redis_instance 集群清理
func TwemproxyRedisInstanceClear(serverIP string, clearDataDir bool) (err error) {
	proxytest.TwemproxyClear(serverIP, consts.TestTwemproxyPort, clearDataDir)
	// master清理时, /usr/local/redis 先保留
	redistest.RedisInstanceMasterClear(serverIP, consts.TendisTypeTwemproxyRedisInstance, clearDataDir)
	redistest.RedisInstanceSlaveClear(serverIP, consts.TendisTypeTwemproxyRedisInstance, clearDataDir)
	return nil
}

// TwemproxyTendisSSDInstall twemproxy + tendisSSD 集群安装
func TwemproxyTendisSSDInstall(serverIP,
	redisPkgName, redisPkgMd5,
	dbtoolsPkgName, dbtoolsPkgMd5,
	twemproxyPkgName, twemproxyPkgMd5 string) (err error) {
	var retBase64 string

	// 先清理再安装
	err = redistest.TendisSSDClear(serverIP, consts.TendisTypeTwemproxyTendisSSDInstance,
		true, consts.TestTendisSSDMasterStartPort, consts.TestRedisInstanceNum)
	if err != nil {
		return
	}
	err = redistest.TendisSSDClear(serverIP, consts.TendisTypeTwemproxyTendisSSDInstance,
		true, consts.TestTendisSSDSlaveStartPort, consts.TestRedisInstanceNum)
	if err != nil {
		return
	}
	// 安装ssd master
	err = redistest.TendisSSDInstall(serverIP, redisPkgName, redisPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5, consts.TendisTypeTwemproxyTendisSSDInstance,
		consts.TestTendisSSDMasterStartPort, consts.TestRedisInstanceNum)
	if err != nil {
		return
	}
	err = redistest.TendisSSDInstall(serverIP, redisPkgName, redisPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5, consts.TendisTypeTwemproxyTendisSSDInstance,
		consts.TestTendisSSDSlaveStartPort, consts.TestRedisInstanceNum,
	)
	if err != nil {
		return
	}
	// 向master中写点数据
	for i := 0; i < consts.TestRedisInstanceNum; i++ {
		cmdTest, err := redistest.NewCommandTest(serverIP, consts.TestTendisSSDMasterStartPort+i,
			consts.RedisTestPasswd, consts.TendisTypeRedisInstance, 0)
		if err != nil {
			return err
		}
		cmdTest.StringTest()
		if cmdTest.Err != nil {
			return cmdTest.Err
		}
	}
	// master执行备份
	retBase64, err = redistest.Backup(serverIP, []int{},
		consts.TestTendisSSDMasterStartPort,
		consts.TestRedisInstanceNum, &atomredis.TendisSSDSetLogCount{
			LogCount:          10000,
			SlaveLogKeepCount: 20000,
		})
	if err != nil {
		return
	}
	retDecoded, err := base64.StdEncoding.DecodeString(retBase64)
	if err != nil {
		err = fmt.Errorf("TwemproxyTendisSSDInstall base64 decode fail,err:%v,base64Len:%d,base64Data:%s", err,
			len(retBase64), retBase64)
		fmt.Println(err.Error())
		return
	}
	backupTasks := []atomredis.BackupTask{}
	err = json.Unmarshal(retDecoded, &backupTasks)
	if err != nil {
		err = fmt.Errorf("TwemproxyTendisSSDInstall json.Unmarshal  fail,err:%v,dataDecoded:%s", err, string(retDecoded))
		fmt.Println(err.Error())
		return
	}

	// tendis_ssd restore slave
	err = redistest.SsdRestore(serverIP, []int{}, consts.TestTendisSSDMasterStartPort,
		consts.TestRedisInstanceNum, consts.RedisTestPasswd,
		serverIP, []int{}, consts.TestTendisSSDSlaveStartPort,
		consts.TestRedisInstanceNum, consts.RedisTestPasswd,
		filepath.Join(consts.GetRedisBackupDir(), "dbbak/"), backupTasks)
	if err != nil {
		return
	}

	// 建立主从关系
	// err = redistest.CreateReplicaof(serverIP, consts.TestTendisSSDMasterStartPort, consts.RedisTestPasswd,
	// 	serverIP, consts.TestTendisSSDSlaveStartPort, consts.RedisTestPasswd)
	// if err != nil {
	// 	return
	// }

	// 安装twemproxy
	err = proxytest.TwemproxyInstall(serverIP, twemproxyPkgName, twemproxyPkgMd5,
		consts.TendisTypeTwemproxyRedisInstance,
		consts.TestTendisSSDMasterStartPort, consts.TestRedisInstanceNum,
		consts.TestSSDClusterTwemproxyPort)
	if err != nil {
		return
	}

	// 写入数据测试
	cmdTest, err := redistest.NewCommandTest(serverIP, consts.TestSSDClusterTwemproxyPort, consts.ProxyTestPasswd,
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
	// 和cache,tendisplus 写入类型保持一致，方便key提取删除，校验结果保持一致
	cmdTest.SetTest()
	if cmdTest.Err != nil {
		return cmdTest.Err
	}
	cmdTest.ListTest()
	if cmdTest.Err != nil {
		return cmdTest.Err
	}
	return nil
}

// TwemproxyTendisSSDClear twemproxy+tendisssd 集群清理
func TwemproxyTendisSSDClear(serverIP string, clearDataDir bool) (err error) {
	proxytest.TwemproxyClear(serverIP, consts.TestSSDClusterTwemproxyPort, clearDataDir)
	// 清理redis
	redistest.TendisSSDClear(serverIP, consts.TendisTypeTwemproxyTendisSSDInstance,
		true, consts.TestTendisSSDMasterStartPort, consts.TestRedisInstanceNum)
	redistest.TendisSSDClear(serverIP, consts.TendisTypeTwemproxyTendisSSDInstance,
		true, consts.TestTendisSSDSlaveStartPort, consts.TestRedisInstanceNum)
	return nil
}

// RedisSceneTest TODO
func RedisSceneTest(masterIp, SlaveIp, tp string, mport, sport, num int) error {
	rscene := redistest.RedisSceneTest{}
	rscene.SetClusterType(tp)
	rscene.SetInatances(masterIp, SlaveIp, mport, sport, num)
	if err := rscene.RunRedisCheckSyncStatus(); err != nil {
		return err
	}
	if err := rscene.RunRedisSyncParams(); err != nil {
		return err
	}
	if err := rscene.RunRedisKillConn(); err != nil {
		return err
	}
	return nil
}

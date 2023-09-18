package clustertest

import (
	"fmt"
	"path/filepath"
	"strconv"
	"time"

	"dbm-services/redis/db-tools/dbactuator/mylog"
	"dbm-services/redis/db-tools/dbactuator/pkg/atomjobs/atomredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
	"dbm-services/redis/db-tools/dbactuator/tests/proxytest"
	"dbm-services/redis/db-tools/dbactuator/tests/redistest"
)

// TwemproxyCacheSwitch twemproxy+cache_redis切换测试
// 必须先成功执行 TwemproxyRedisInstanceInstall
func TwemproxyCacheSwitch(serverIP,
	redisPkgName, redisPkgMd5,
	dbtoolsPkgName, dbtoolsPkgMd5,
	bkdbmonPkgName, bkdbmonPkgMd5 string) (err error) {
	// 设置参数
	fmt.Println(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
	fmt.Println(">>>>>>>>>>>>>>>start tendisCacheSwitchTest=================")

	// 先清理,再安装
	redistest.RedisSyncMasterClear(serverIP, consts.TendisTypeTwemproxyRedisInstance, true)
	redistest.RedisSyncSlaveClear(serverIP, consts.TendisTypeTwemproxyRedisInstance, true)

	// 安装sync redis 并创建主从关系
	err = redistest.RedisSyncMasterInstall(serverIP, redisPkgName, redisPkgMd5, dbtoolsPkgName, dbtoolsPkgMd5,
		consts.TendisTypeTwemproxyRedisInstance)
	if err != nil {
		return
	}
	err = redistest.RedisSyncSlaveInstall(serverIP, redisPkgName, redisPkgMd5, dbtoolsPkgName, dbtoolsPkgMd5,
		consts.TendisTypeTwemproxyRedisInstance)
	if err != nil {
		return
	}

	err = redistest.CreateReplicaof(serverIP, consts.TestSyncRedisMasterStartPort, consts.RedisTestPasswd,
		serverIP, consts.TestSyncRedisSlaveStartPort, consts.RedisTestPasswd)
	if err != nil {
		return
	}

	// [oldslave ---> newmaster] cacheRedis 建立主从关系
	fmt.Println(">>>>>>oldmaster-->oldsalve--->newmaster--->newslave>>>>>>>>>>>>>>>>>>")
	replicaOfTest := redistest.RedisReplicaofTest{}
	replicaOfTest.SetMasterIP(serverIP).
		SetMasterPorts(consts.TestRedisSlaveStartPort, consts.TestRedisInstanceNum).
		SetMasterAuth(consts.RedisTestPasswd).
		SetSlaveIP(serverIP).
		SetSlavePorts(consts.TestSyncRedisMasterStartPort, consts.TestRedisInstanceNum).
		SetSlaveAuth(consts.RedisTestPasswd)
	if replicaOfTest.Err != nil {
		return replicaOfTest.Err
	}
	replicaOfTest.RunReplicaOf()
	if replicaOfTest.Err != nil {
		return replicaOfTest.Err
	}

	installTest := redistest.BkDBmonInstallTest{}
	installTest.
		SetBkDbmonPkg(bkdbmonPkgName, bkdbmonPkgMd5).
		SetDbtoolsPkg(dbtoolsPkgName, dbtoolsPkgMd5).
		SetBackupConf().
		AppendMasterServer(serverIP, consts.TestRedisMasterStartPort, consts.TestRedisInstanceNum).
		AppendMasterServer(serverIP, consts.TestSyncRedisMasterStartPort, consts.TestRedisInstanceNum)
	if installTest.Err != nil {
		return installTest.Err
	}
	// 安装bk-dbmon,开始写心跳
	installTest.InstallBkDbmon()
	if installTest.Err != nil {
		return installTest.Err
	}
	// 开始切换
	err = DoSwitchActionTest(serverIP, consts.TestTwemproxyPort, consts.TestRedisMasterStartPort,
		consts.TestRedisSlaveStartPort, consts.TestSyncRedisMasterStartPort,
		consts.TestSyncRedisSlaveStartPort,
		consts.TendisTypeTwemproxyRedisInstance)
	if err != nil {
		return err
	}

	// 切换成功,再次检查 twemproxy的配置中包含了 syncMasterIP:syncMasterPort
	twemport := strconv.Itoa(consts.TestTwemproxyPort)
	twemConfFile := filepath.Join(consts.GetRedisDataDir(), "twemproxy-0.2.4", twemport, "nutcracker."+twemport+".yml")
	if util.FileExists(twemConfFile) {
		var grepRet string
		grepCmd := fmt.Sprintf(`grep '%s:%d' %s`, serverIP, consts.TestSyncRedisMasterStartPort, twemConfFile)
		mylog.Logger.Info(grepCmd)
		grepRet, err = util.RunBashCmd(grepCmd, "", nil, 10*time.Second)
		if err != nil {
			return
		}
		mylog.Logger.Info("%s %s", twemConfFile, grepRet)
	}

	// 检测后端Md5 ,这里只有1个ip，就校验程序的一般性问题吧
	twemproxyMd5 := proxytest.TwemproxyBackendsMd5Test{}
	twemproxyMd5.SetProxiesList([]string{serverIP}, consts.TestTwemproxyPort)
	if err = twemproxyMd5.RunCheckProxyBackends(); err != nil {
		return
	}

	// 卸载 bk-dbmon
	installTest.StopBkDbmon()

	// 旧master 和 slave 环境清理
	redistest.RedisInstanceMasterClear(serverIP, consts.TendisTypeTwemproxyRedisInstance, true)
	redistest.RedisInstanceSlaveClear(serverIP, consts.TendisTypeTwemproxyRedisInstance, true)

	return nil
}

// TwemproxyCacheSwitchRestoreEnv twemproxy+cache_redis恢复环境
// 必须先成功执行 TwemproxyCacheSwitch
func TwemproxyCacheSwitchRestoreEnv(serverIP,
	redisPkgName, redisPkgMd5,
	dbtoolsPkgName, dbtoolsPkgMd5,
	bkdbmonPkgName, bkdbmonPkgMd5 string) (err error) {
	// 设置参数
	fmt.Println(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
	fmt.Println(">>>>>>>>>>>>>>>start TwemproxyCacheSwitchRestoreEnv=================")

	// 先清理,再安装
	redistest.RedisInstanceMasterClear(serverIP, consts.TendisTypeTwemproxyRedisInstance, true)
	redistest.RedisInstanceSlaveClear(serverIP, consts.TendisTypeTwemproxyRedisInstance, true)

	// 安装redis master/slave 并创建主从关系
	err = redistest.RedisInstanceMasterInstall(serverIP, redisPkgName, redisPkgMd5, dbtoolsPkgName, dbtoolsPkgMd5,
		consts.TendisTypeTwemproxyRedisInstance)
	if err != nil {
		return
	}
	err = redistest.RedisInstanceSlaveInstall(serverIP, redisPkgName, redisPkgMd5, dbtoolsPkgName, dbtoolsPkgMd5,
		consts.TendisTypeTwemproxyRedisInstance)
	if err != nil {
		return
	}

	err = redistest.CreateReplicaof(serverIP, consts.TestRedisMasterStartPort, consts.RedisTestPasswd,
		serverIP, consts.TestRedisSlaveStartPort, consts.RedisTestPasswd)
	if err != nil {
		return
	}

	// [syncslave ---> newmaster] cacheRedis 建立主从关系
	fmt.Println(">>>>>>syncmaster-->syncsalve--->newmaster--->newslave>>>>>>>>>>>>>>>>>>")
	replicaOfTest := redistest.RedisReplicaofTest{}
	replicaOfTest.SetMasterIP(serverIP).
		SetMasterPorts(consts.TestSyncRedisSlaveStartPort, consts.TestRedisInstanceNum).
		SetMasterAuth(consts.RedisTestPasswd).
		SetSlaveIP(serverIP).
		SetSlavePorts(consts.TestRedisMasterStartPort, consts.TestRedisInstanceNum).
		SetSlaveAuth(consts.RedisTestPasswd)
	if replicaOfTest.Err != nil {
		return replicaOfTest.Err
	}
	replicaOfTest.RunReplicaOf()
	if replicaOfTest.Err != nil {
		return replicaOfTest.Err
	}

	installTest := redistest.BkDBmonInstallTest{}
	installTest.
		SetBkDbmonPkg(bkdbmonPkgName, bkdbmonPkgMd5).
		SetDbtoolsPkg(dbtoolsPkgName, dbtoolsPkgMd5).
		SetBackupConf().
		AppendMasterServer(serverIP, consts.TestRedisMasterStartPort, consts.TestRedisInstanceNum).
		AppendMasterServer(serverIP, consts.TestSyncRedisMasterStartPort, consts.TestRedisInstanceNum)
	if installTest.Err != nil {
		return installTest.Err
	}
	// 安装bk-dbmon,开始写心跳
	installTest.InstallBkDbmon()
	if installTest.Err != nil {
		return installTest.Err
	}
	// 开始切换
	err = DoSwitchActionTest(serverIP, consts.TestTwemproxyPort,
		consts.TestSyncRedisMasterStartPort, consts.TestSyncRedisSlaveStartPort,
		consts.TestRedisMasterStartPort, consts.TestRedisSlaveStartPort,
		consts.TendisTypeTwemproxyRedisInstance)
	if err != nil {
		return err
	}

	// 切换成功,再次检查 twemproxy的配置中包含了 syncMasterIP:syncMasterPort
	twemport := strconv.Itoa(consts.TestTwemproxyPort)
	twemConfFile := filepath.Join(consts.GetRedisDataDir(), "twemproxy-0.2.4", twemport, "nutcracker."+twemport+".yml")
	if util.FileExists(twemConfFile) {
		var grepRet string
		grepCmd := fmt.Sprintf(`grep '%s:%d' %s`, serverIP, consts.TestRedisMasterStartPort, twemConfFile)
		mylog.Logger.Info(grepCmd)
		grepRet, err = util.RunBashCmd(grepCmd, "", nil, 10*time.Second)
		if err != nil {
			return
		}
		mylog.Logger.Info("%s %s", twemConfFile, grepRet)
	}

	// 卸载 bk-dbmon
	installTest.StopBkDbmon()

	// sync master 和 slave 环境清理
	redistest.RedisSyncMasterClear(serverIP, consts.TendisTypeTwemproxyRedisInstance, true)
	redistest.RedisSyncSlaveClear(serverIP, consts.TendisTypeTwemproxyRedisInstance, true)

	return nil
}

// DoSwitchActionTest 执行切换
func DoSwitchActionTest(serverIP string, proxyPort, cmaster, cslave, syncMaster, syncSlave int, ctp string) error {
	tendisSwitchTest := redistest.RedisSwitchTest{}
	var maddrs, saddrs []string
	for i := 0; i < 4; i++ {
		if ctp == consts.TendisTypeTwemproxyRedisInstance {
			maddrs = append(maddrs, fmt.Sprintf("%s:%d %d-%d", serverIP, cmaster+i, i, i))
			saddrs = append(saddrs, fmt.Sprintf("%s:%d %d-%d", serverIP, cslave+i, i, i))
		} else {
			maddrs = append(maddrs, fmt.Sprintf("%s:%d", serverIP, cmaster+i))
			saddrs = append(saddrs, fmt.Sprintf("%s:%d", serverIP, cslave+i))
		}
	}

	sinf := []atomredis.InstanceSwitchParam{}
	for i := 0; i < 4; i++ {
		sinf = append(sinf, atomredis.InstanceSwitchParam{
			MasterInfo: atomredis.InstanceParam{IP: serverIP, Port: cmaster + i},
			SlaveInfo:  atomredis.InstanceParam{IP: serverIP, Port: syncMaster + i},
		})
	}

	tendisSwitchTest.SetDefaultClusterMeta(consts.ProxyTestPasswd, consts.RedisTestPasswd).
		SetProxySet(fmt.Sprintf("%s:%d", serverIP, proxyPort)).SetClusterType(ctp).
		SetMasterSet(maddrs).
		SetSlaveSet(saddrs).SetDefaultSwitchCondition("mms").
		SetSwitchInfo(sinf)

	if ctp == consts.TendisTypeTwemproxyRedisInstance {
		tendisSwitchTest.SetDefaultSwitchCondition("msms")
	}

	if tendisSwitchTest.Err != nil {
		return tendisSwitchTest.Err
	}

	tendisSwitchTest.RunTendisSwitch()
	return nil
}

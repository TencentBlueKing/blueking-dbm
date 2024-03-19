package main

import (
	"flag"
	"fmt"
	"net/url"
	"os"

	"dbm-services/redis/db-tools/dbactuator/mylog"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
	"dbm-services/redis/db-tools/dbactuator/tests/clustertest"
	"dbm-services/redis/db-tools/dbactuator/tests/proxytest"
	"dbm-services/redis/db-tools/dbactuator/tests/redistest"
	"dbm-services/redis/db-tools/dbactuator/tests/systest"
)

var (
	localIP      string
	repoUrl      string
	repoUser     string
	repoPassword string

	tendisplusPkgName string
	tendisplusPkgMd5  string
	tendisssdPkgName  string
	tendisssdPkgMd5   string
	redisPkgName      string
	redisPkgMd5       string
	predixyPkgName    string
	predixyPkgMd5     string
	twemproxyPkgName  string
	twemproxyPkgMd5   string
	keytoolsPkgName   string
	keytoolsPkgMd5    string
	dbtoolsPkgName    string
	dbtoolsPkgMd5     string
	bkdbmonPkgName    string
	bkdbmonPkgMd5     string
)

func before() (err error) {
	mylog.UnitTestInitLog()
	localIP, err = util.GetLocalIP()
	if err != nil {
		fmt.Println(err.Error())
	}
	return err
}
func after() {
	clustertest.PredixyTendisplusClusterClear(localIP, true)
	clustertest.TwemproxyRedisInstanceClear(localIP, true)
}

func main() {
	flag.StringVar(&tendisplusPkgName, "tendisplus-pkgname", "", "tendisplus pkg name")
	flag.StringVar(&tendisplusPkgMd5, "tendisplus-pkgmd5", "", "tendisplus pkg md5sum")
	flag.StringVar(&tendisssdPkgName, "tendisssd-pkgname", "", "tendisssd pkg name")
	flag.StringVar(&tendisssdPkgMd5, "tendisssd-pkgmd5", "", "tendisssd pkg md5sum")
	flag.StringVar(&redisPkgName, "redis-pkgname", "", "redis pkg name")
	flag.StringVar(&redisPkgMd5, "redis-pkgmd5", "", "redis pkg md5sum")
	flag.StringVar(&predixyPkgName, "predixy-pkgname", "", "predixy pkg name")
	flag.StringVar(&predixyPkgMd5, "predixy-pkgmd5", "", "predixy pkg md5sum")
	flag.StringVar(&twemproxyPkgName, "twemproxy-pkgname", "", "twemproxy pkg name")
	flag.StringVar(&twemproxyPkgMd5, "twemproxy-pkgmd5", "", "twemproxy pkg md5sum")
	flag.StringVar(&dbtoolsPkgName, "dbtools-pkgname", "", "dbtools pkg name")
	flag.StringVar(&dbtoolsPkgMd5, "dbtools-pkgmd5", "", "dbtools pkg md5sum")
	flag.StringVar(&bkdbmonPkgName, "bkdbmon-pkgname", "", "bk-dbmon pkg name")
	flag.StringVar(&bkdbmonPkgMd5, "bkdbmon-pkgmd5", "", "bk-dbmon pkg md5sum")
	flag.StringVar(&repoUrl, "repo-url", "xxxx", "制品库地址")
	flag.StringVar(&repoUser, "user", "xxxx", "制品库用户名")
	flag.StringVar(&repoPassword, "password", "xxxx", "制品库用户密码")
	flag.Parse()

	var err error
	before()

	defer func() {
		if err != nil {
			os.Exit(-1)
		}
	}()

	// 获取制品库地址
	u, err := url.Parse(repoUrl)
	if err != nil {
		fmt.Println("Parse输入网址不正确,请检查!", repoUrl)
		return
	}
	repoUrl = fmt.Sprintf(u.Scheme + "://" + u.Host)

	systest.RunSysInit() // 系统初始化可能出错,忽略错误继续执行

	err = clustertest.PredixyTendisplusClusterInstallTest(localIP,
		tendisplusPkgName, tendisplusPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5,
		predixyPkgName, predixyPkgMd5)
	if err != nil {
		return
	}
	err = clustertest.PredixyRedisClusterInstallTest(localIP, redisPkgName, redisPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5,
		predixyPkgName, predixyPkgMd5)
	if err != nil {
		return
	}

	// PredixyTendisplusClusterForgetTest forget节点测试
	if err = clustertest.PredixyTendisplusClusterForgetTest(localIP,
		tendisplusPkgName, tendisplusPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5); err != nil {
		return
	}

	err = redistest.BkDbmonInstall(localIP, dbtoolsPkgName, dbtoolsPkgMd5,
		bkdbmonPkgName, bkdbmonPkgMd5,
		consts.TendisTypePredixyTendisplusCluster)
	if err != nil {
		return
	}
	redistest.BkDbmonStopNew(localIP, dbtoolsPkgName, dbtoolsPkgMd5,
		bkdbmonPkgName, bkdbmonPkgMd5)

	err = redistest.Keyspattern(localIP, []int{},
		consts.TestTendisPlusSlaveStartPort, consts.TestRedisInstanceNum,
		repoUser, repoPassword, repoUrl, dbtoolsPkgName, dbtoolsPkgMd5)
	if err != nil {
		return
	}
	err = redistest.KeysFilesDelete(localIP, consts.TestTendisplusPredixyPort,
		repoUser, repoPassword, repoUrl,
		dbtoolsPkgName, dbtoolsPkgMd5)
	if err != nil {
		return
	}

	_, err = redistest.Backup(localIP, []int{}, consts.TestTendisPlusSlaveStartPort, consts.TestRedisInstanceNum, nil)
	if err != nil {
		return
	}
	// slot 扩容测试 新增节点
	err = clustertest.TendisplusScaleNodesInstall(localIP,
		tendisplusPkgName, tendisplusPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5,
		predixyPkgName, predixyPkgMd5,
		consts.ExpansionTestTendisPlusMasterStartPort,
		consts.ExpansionTestTendisPlusSlaveStartPort, consts.ExpansionTestRedisInstanceNum)
	if err != nil {
		return
	}

	// slot rebalance 用于扩容
	err = clustertest.TendisPlusRebalence(localIP)
	if err != nil {
		return
	}
	// 新增1组节点 用于迁移特定slot ：处理热点key场景
	err = clustertest.TendisplusScaleNodesInstall(localIP,
		tendisplusPkgName, tendisplusPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5,
		predixyPkgName, predixyPkgMd5,
		consts.SlotTestTendisPlusMasterPort,
		consts.SLotTestTendisPlusSlaveStart, consts.SLotTestRedisInstanceNum)
	if err != nil {
		return
	}

	// slot migrate 用于迁移特定slot ：处理热点key场景
	err = clustertest.TendisPlusMigrateSpecificSlots(localIP)
	if err != nil {
		return
	}
	err = redistest.FlushData(localIP,
		consts.TendisTypePredixyTendisplusCluster, consts.RedisTestPasswd, []int{},
		consts.TestTendisPlusMasterStartPort, consts.TestRedisInstanceNum)
	if err != nil {
		return
	}

	err = clustertest.PredixyTendisPlusSwitchTest(localIP,
		tendisplusPkgName, tendisplusPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5)
	if err != nil {
		return
	}

	// 测试predixy启停
	err = proxytest.PredixyOpenClose(localIP)
	if err != nil {
		return
	}
	err = proxytest.PredixyShutdown(localIP)
	if err != nil {
		return
	}
	err = redistest.RedisShutdown(localIP,
		consts.TestTendisPlusMasterStartPort,
		consts.TestTendisPlusSlaveStartPort,
		consts.TestRedisInstanceNum)
	if err != nil {
		return
	}
	err = clustertest.PredixyTendisplusClusterClear(localIP, true)
	if err != nil {
		return
	}

	fmt.Println(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
	fmt.Println(">>>>>>>>>>>>>>>>>>>>start twmproxy arch test>>>>>>>>>>>>>>>")
	err = clustertest.TwemproxyRedisInstanceInstall(localIP,
		redisPkgName, redisPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5,
		twemproxyPkgName, twemproxyPkgMd5)
	if err != nil {
		return
	}

	err = redistest.Keyspattern(localIP, []int{},
		consts.TestRedisSlaveStartPort, consts.TestRedisInstanceNum,
		repoUser, repoPassword, repoUrl, dbtoolsPkgName, dbtoolsPkgMd5)
	if err != nil {
		return
	}

	err = redistest.KeysFilesDelete(localIP, consts.TestRedisTwemproxyPort, repoUser, repoPassword, repoUrl,
		dbtoolsPkgName, dbtoolsPkgMd5)
	if err != nil {
		return
	}

	err = redistest.RunReplicaPairDataCheck(localIP, consts.TestRedisMasterStartPort, consts.RedisTestPasswd,
		localIP, consts.TestRedisSlaveStartPort, consts.RedisTestPasswd,
		dbtoolsPkgName, dbtoolsPkgMd5)
	if err != nil {
		return
	}
	err = redistest.RunReplicaPairDataRepair(localIP, consts.TestRedisMasterStartPort, consts.RedisTestPasswd,
		localIP, consts.TestRedisSlaveStartPort, consts.RedisTestPasswd,
		dbtoolsPkgName, dbtoolsPkgMd5)
	if err != nil {
		return
	}

	// 测试twemproxy启停
	err = proxytest.TwemproxyOpenClose(localIP)
	if err != nil {
		return
	}
	_, err = redistest.Backup(localIP, []int{}, consts.TestRedisSlaveStartPort, consts.TestRedisInstanceNum, nil)
	if err != nil {
		return
	}
	err = redistest.FlushData(localIP,
		consts.TendisTypeTwemproxyRedisInstance, consts.RedisTestPasswd,
		[]int{},
		consts.TestRedisMasterStartPort,
		consts.TestRedisInstanceNum)
	if err != nil {
		return
	}

	if err := clustertest.RedisSceneTest(localIP, localIP, consts.TendisTypeTwemproxyRedisInstance,
		consts.TestRedisMasterStartPort,
		consts.TestRedisSlaveStartPort, consts.TestRedisInstanceNum); err != nil {
		return
	}

	err = clustertest.TwemproxyCacheSwitch(localIP,
		redisPkgName, redisPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5,
		bkdbmonPkgName, bkdbmonPkgMd5)
	if err != nil {
		return
	}

	err = clustertest.TwemproxyCacheSwitchRestoreEnv(localIP,
		redisPkgName, redisPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5,
		bkdbmonPkgName, bkdbmonPkgMd5)
	if err != nil {
		return
	}

	err = proxytest.TwemproxyShutDown(localIP)
	if err != nil {
		return
	}
	err = redistest.RedisShutdown(localIP, consts.TestRedisMasterStartPort,
		consts.TestRedisSlaveStartPort, consts.TestRedisInstanceNum)
	if err != nil {
		return
	}
	err = clustertest.TwemproxyRedisInstanceClear(localIP, true)
	if err != nil {
		return
	}

	fmt.Println(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
	fmt.Println(">>>>>>>>>>>>>>>>>>>>start twmproxy tendisssd test>>>>>>>>>>>>>>>")
	err = clustertest.TwemproxyTendisSSDInstall(localIP,
		tendisssdPkgName, tendisssdPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5,
		twemproxyPkgName, twemproxyPkgMd5)
	if err != nil {
		return
	}

	if err := clustertest.RedisSceneTest(localIP, localIP, consts.TendisTypeTwemproxyTendisSSDInstance,
		consts.TestTendisSSDMasterStartPort,
		consts.TestTendisSSDSlaveStartPort, consts.TestRedisInstanceNum); err != nil {
		return
	}

	err = redistest.Keyspattern(localIP, []int{},
		consts.TestTendisSSDSlaveStartPort, consts.TestRedisInstanceNum,
		repoUser, repoPassword, repoUrl, dbtoolsPkgName, dbtoolsPkgMd5)
	if err != nil {
		return
	}

	err = redistest.KeysFilesDelete(localIP, consts.TestSSDClusterTwemproxyPort, repoUser, repoPassword, repoUrl,
		dbtoolsPkgName, dbtoolsPkgMd5)
	if err != nil {
		return
	}

	err = clustertest.TwemproxyTendisSSDClear(localIP, true)
	if err != nil {
		return
	}
	return
}

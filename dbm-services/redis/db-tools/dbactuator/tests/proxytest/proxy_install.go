package proxytest

import (
	"encoding/json"
	"fmt"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"dbm-services/redis/db-tools/dbactuator/pkg/atomjobs/atomproxy"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// PredixyInstallTest predixy安装测试
type PredixyInstallTest struct {
	atomproxy.PredixyConfParams
	Err error `json:"-"`
}

// SetIP set ip,传入为空则自动获取本地ip
func (test *PredixyInstallTest) SetIP(ip string) *PredixyInstallTest {
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

// SetPort set port
func (test *PredixyInstallTest) SetPort(port int) *PredixyInstallTest {
	if test.Err != nil {
		return test
	}
	test.Port = port
	return test
}

// SetPkg set pkg信息,传入为空则pkg=predixy-1.4.0.tar.gz,pkgMd5=9a863ce100bfe6138523d046c068f49c
func (test *PredixyInstallTest) SetPkg(pkg, pkgMd5 string) *PredixyInstallTest {
	if test.Err != nil {
		return test
	}
	if pkg == "" || pkgMd5 == "" {
		pkg = "predixy-1.4.0.tar.gz"
		pkgMd5 = "9a863ce100bfe6138523d046c068f49c"
	}
	test.Pkg = pkg
	test.PkgMd5 = pkgMd5
	return test
}

// SetProxyPassword set proxy password,传入为空则password=xxxx
func (test *PredixyInstallTest) SetProxyPassword(proxyPasswd string) *PredixyInstallTest {
	if test.Err != nil {
		return test
	}
	if proxyPasswd == "" {
		proxyPasswd = "xxxx"
	}
	test.PredixyPasswd = proxyPasswd
	test.PredixyAdminPasswd = proxyPasswd
	return test
}

// SetRedisPassword set password,传入为空则password=xxxx
func (test *PredixyInstallTest) SetRedisPassword(redisPasswd string) *PredixyInstallTest {
	if test.Err != nil {
		return test
	}
	if redisPasswd == "" {
		redisPasswd = "xxxx"
	}
	test.RedisPasswd = redisPasswd
	return test
}

// SetServers 设置 servers
func (test *PredixyInstallTest) SetServers(servers []string) *PredixyInstallTest {
	if test.Err != nil {
		return test
	}
	if len(servers) == 0 {
		test.Err = fmt.Errorf("PredixyInstallTest servers cannot be empty")
		fmt.Println(test.Err.Error())
		return test
	}
	test.Servers = servers
	return test
}

// SetOtherParamsDefault 设置其他参数的默认值
func (test *PredixyInstallTest) SetOtherParamsDefault() *PredixyInstallTest {
	if test.Err != nil {
		return test
	}
	test.DbConfig.WorkerThreads = "4"
	test.DbConfig.ClientTimeout = "0"
	test.DbConfig.RefreshInterval = "1"
	test.DbConfig.ServerFailureLimit = "10"
	test.DbConfig.ServerRetryTimeout = "1"
	test.DbConfig.KeepAlive = "0"
	test.DbConfig.ServerTimeout = "0"
	test.DbConfig.SlowlogLogSlowerThan = "100000"
	test.DbConfig.SlowlogMaxLen = "1024"
	return test
}

// RunPredixyInstall 安装predixy
func (test *PredixyInstallTest) RunPredixyInstall() {
	msg := fmt.Sprintf("=========PredixyIntall test start============")
	fmt.Println(msg)

	defer func() {
		if test.Err != nil {
			msg = fmt.Sprintf("=========PredixyIntall test fail============")
		} else {
			msg = fmt.Sprintf("=========PredixyIntall test success============")
		}
		fmt.Println(msg)
	}()

	paramBytes, _ := json.Marshal(test)
	// fmt.Printf("-------payload(raw)--------\n%s\n\n", string(paramBytes))
	// encodeStr := base64.StdEncoding.EncodeToString(paramBytes)
	instllCmd := fmt.Sprintf(consts.ActuatorTestCmd, atomproxy.NewPredixyInstall().Name(), string(paramBytes))
	fmt.Println(instllCmd)
	_, test.Err = util.RunBashCmd(instllCmd, "", nil, 1*time.Hour)
	if test.Err != nil {
		return
	}
	return
}

func predixyStillRunning() bool {
	grepCmd := `ps aux|grep "/usr/local/predixy/bin"|grep -v grep || true;`
	ret, _ := util.RunBashCmd(grepCmd, "", nil, 10*time.Second)
	ret = strings.TrimSpace(ret)
	if ret != "" {
		return true
	}
	return false
}

// ClearPredixy 清理predixy环境
// 关闭predixy进程,清理数据目录,清理 /usr/local/predixy
func (test *PredixyInstallTest) ClearPredixy(clearDataDir bool) {
	var dir string
	var isUsing bool
	isUsing, _ = util.CheckPortIsInUse(test.IP, strconv.Itoa(test.Port))
	if isUsing {
		killCmd := fmt.Sprintf("ps aux|grep predixy|grep -v grep|grep %d|awk '{print $2}'|xargs kill -9", test.Port)
		util.RunBashCmd(killCmd, "", nil, 1*time.Minute)
	}

	if clearDataDir {
		dataDir := consts.GetRedisDataDir()
		predixyDir := filepath.Join(dataDir, "predixy", strconv.Itoa(test.Port))
		if util.FileExists(predixyDir) {
			util.RunBashCmd("rm -rf "+predixyDir, "", nil, 1*time.Minute)
		}
	}

	if !predixyStillRunning() {
		dir = "/usr/local/predixy"
		if util.FileExists(dir) {
			fmt.Println("rm -rf " + dir)
			util.RunBashCmd("rm -rf "+dir, "", nil, 1*time.Minute)
		}
		dir = filepath.Join("/usr/local", test.GePkgBaseName())
		if util.FileExists(dir) {
			fmt.Println("rm -rf " + dir)
			util.RunBashCmd("rm -rf "+dir, "", nil, 1*time.Minute)
		}
	}
}

// TwemproxyInstallTest twemproxy 安装测试
type TwemproxyInstallTest struct {
	atomproxy.TwemproxyInstallParams
	Err error `json:"-"`
}

// SetIP set ip,传入为空则自动获取本地ip
func (test *TwemproxyInstallTest) SetIP(ip string) *TwemproxyInstallTest {
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

// SetPort set port
func (test *TwemproxyInstallTest) SetPort(port int) *TwemproxyInstallTest {
	if test.Err != nil {
		return test
	}
	test.Port = port
	return test
}

// SetDbType 设置DbType,默认为 TwemproxyRedisInstance
func (test *TwemproxyInstallTest) SetDbType(dbType string) *TwemproxyInstallTest {
	if test.Err != nil {
		return test
	}
	if dbType == "" {
		dbType = "TwemproxyRedisInstance"
	}
	test.DbType = dbType
	return test
}

// SetPkg set pkg信息,传入为空则pkg=twemproxy-0.4.1-v23.tar.gz,pkgMd5=41850e44bebfce84ebd4d0cf4cce6833
func (test *TwemproxyInstallTest) SetPkg(pkg, pkgMd5 string) *TwemproxyInstallTest {
	if test.Err != nil {
		return test
	}
	if pkg == "" || pkgMd5 == "" {
		pkg = "twemproxy-0.4.1-v23.tar.gz"
		pkgMd5 = "41850e44bebfce84ebd4d0cf4cce6833"
	}
	test.Pkg = pkg
	test.PkgMd5 = pkgMd5
	return test
}

// SetProxyPassword set proxy password,传入为空则password=xxxx
func (test *TwemproxyInstallTest) SetProxyPassword(proxyPasswd string) *TwemproxyInstallTest {
	if test.Err != nil {
		return test
	}
	if proxyPasswd == "" {
		proxyPasswd = "xxxx"
	}
	test.Password = proxyPasswd
	return test
}

// SetRedisPassword set password,传入为空则password=xxxx
func (test *TwemproxyInstallTest) SetRedisPassword(redisPasswd string) *TwemproxyInstallTest {
	if test.Err != nil {
		return test
	}
	if redisPasswd == "" {
		redisPasswd = "xxxx"
	}
	test.RedisPassword = redisPasswd
	return test
}

// SetServers 设置 servers
func (test *TwemproxyInstallTest) SetServers(servers []string) *TwemproxyInstallTest {
	if test.Err != nil {
		return test
	}
	if len(servers) == 0 {
		test.Err = fmt.Errorf("TwemproxyInstallTest servers cannot be empty")
		fmt.Println(test.Err.Error())
		return test
	}
	test.Servers = servers
	return test
}

// RunTwemproxyInstall 安装twemproxy
func (test *TwemproxyInstallTest) RunTwemproxyInstall() {
	msg := fmt.Sprintf("=========TwemproxyInstall test start============")
	fmt.Println(msg)

	defer func() {
		if test.Err != nil {
			msg = fmt.Sprintf("=========TwemproxyInstall test fail============")
		} else {
			msg = fmt.Sprintf("=========TwemproxyInstall test success============")
		}
		fmt.Println(msg)
	}()

	test.ConfConfigs = map[string]interface{}{
		"hash_tag":             "{}",
		"server_failure_limit": "3",
		"slowms":               "1000000",
		"backlog":              "512",
		"redis":                "true",
		"distribution":         "modhash",
		"hash":                 "fnv1a_64",
		"auto_eject_hosts":     "false",
		"preconnect":           "false",
		"server_retry_timeout": "2000",
		"server_connections":   "1",
		"mbuf-size":            "1024",
	}

	paramBytes, _ := json.Marshal(test)
	// fmt.Printf("-------payload(raw)--------\n%s\n\n", string(paramBytes))
	// encodeStr := base64.StdEncoding.EncodeToString(paramBytes)
	instllCmd := fmt.Sprintf(consts.ActuatorTestCmd, atomproxy.NewTwemproxyInstall().Name(), string(paramBytes))
	fmt.Println(instllCmd)
	_, test.Err = util.RunBashCmd(instllCmd, "", nil, 1*time.Hour)
	if test.Err != nil {
		return
	}
	return
}

func twemproxyStillRunning() bool {
	grepCmd := `ps aux|grep nutcracker|grep -v grep || true;`
	ret, _ := util.RunBashCmd(grepCmd, "", nil, 10*time.Second)
	ret = strings.TrimSpace(ret)
	if ret != "" {
		return true
	}
	return false
}

// ClearTwemproxy  清理twemproxy环境
// 关闭twemproxy进程,清理数据目录,清理 /usr/local/twemproxy
func (test *TwemproxyInstallTest) ClearTwemproxy(clearDataDir bool) {
	var dir string
	var isUsing bool
	isUsing, _ = util.CheckPortIsInUse(test.IP, strconv.Itoa(test.Port))
	if isUsing {
		killCmd := fmt.Sprintf("ps aux|grep nutcracker|grep -v grep|grep %d|awk '{print $2}'|xargs kill -9", test.Port)
		util.RunBashCmd(killCmd, "", nil, 1*time.Minute)
	}

	if clearDataDir {
		dataDir := consts.GetRedisDataDir()
		twemDir := filepath.Join(dataDir, "twemproxy-0.2.4", strconv.Itoa(test.Port))
		if util.FileExists(twemDir) {
			fmt.Println("rm -rf " + twemDir)
			util.RunBashCmd("rm -rf "+twemDir, "", nil, 1*time.Minute)
		}
	}

	if !twemproxyStillRunning() {
		dir = "/usr/local/twemproxy"
		if util.FileExists(dir) {
			fmt.Println("rm -rf " + dir)
			util.RunBashCmd("rm -rf "+dir, "", nil, 1*time.Minute)
		}
		dir = filepath.Join("/usr/local", test.GePkgBaseName())
		if util.FileExists(dir) {
			fmt.Println("rm -rf " + dir)
			util.RunBashCmd("rm -rf "+dir, "", nil, 1*time.Minute)
		}
	}
}

// TwemproxyInstall twemproxy安装 并 绑定集群关系
func TwemproxyInstall(serverIP, twemproxyPkgName, twemproxyPkgMd5, dbType string,
	masterStartPort, instNum, twemPort int) (err error) {
	// 建立twemproxy+cacheRedis集群关系
	twemTest := TwemproxyInstallTest{}
	servers := make([]string, 0, instNum)
	var segStart int
	var segEnd int
	segStep := (consts.TwemproxyMaxSegment + 1) / instNum
	for i := 0; i < instNum; i++ {
		segStart = i * segStep
		segEnd = (i+1)*segStep - 1
		servers = append(servers, fmt.Sprintf("%s:%d:1 testapp %d-%d 1", serverIP, masterStartPort+i,
			segStart,
			segEnd))
	}

	twemTest.SetIP(serverIP).SetPort(twemPort).
		SetPkg(twemproxyPkgName, twemproxyPkgMd5).
		SetProxyPassword(consts.ProxyTestPasswd).
		SetRedisPassword(consts.RedisTestPasswd).
		SetDbType(dbType).
		SetServers(servers)
	if twemTest.Err != nil {
		return twemTest.Err
	}
	// 先清理,再安装
	twemTest.ClearTwemproxy(true)

	twemTest.RunTwemproxyInstall()
	if twemTest.Err != nil {
		return twemTest.Err
	}
	return nil
}

// TwemproxyClear twemproxy 下架与清理
func TwemproxyClear(serverIP string, port int, clearDataDir bool) {
	twemTest := TwemproxyInstallTest{}
	twemTest.SetIP(serverIP).SetPort(port).SetProxyPassword(consts.ProxyTestPasswd)
	if twemTest.Err != nil {
		return
	}
	twemTest.ClearTwemproxy(clearDataDir)
}

// PredixyInstall predixy安装
func PredixyInstall(serverIP, predixyPkgName, predixyPkgMd5, dbType string,
	startPort, instNum, predixyPort int) (err error) {
	// predixy 安装并建立redis关系
	servers := make([]string, 0, instNum)
	for i := 0; i < instNum; i++ {
		servers = append(servers, fmt.Sprintf("%s:%d", serverIP, startPort+i))
	}
	predixyTest := PredixyInstallTest{}
	predixyTest.SetIP(serverIP).SetPort(predixyPort).
		SetPkg(predixyPkgName, predixyPkgMd5).
		SetProxyPassword(consts.ProxyTestPasswd).
		SetRedisPassword(consts.RedisTestPasswd).
		SetServers(servers).
		SetOtherParamsDefault()
	if predixyTest.Err != nil {
		return predixyTest.Err
	}
	// 先清理,再安装
	predixyTest.ClearPredixy(true)

	predixyTest.RunPredixyInstall()
	if predixyTest.Err != nil {
		return predixyTest.Err
	}
	return nil
}

// PredixyClear predixy 下架与清理
func PredixyClear(serverIP string, port int, clearDataDir bool) {
	predixyTest := PredixyInstallTest{}
	predixyTest.SetIP(serverIP).SetPort(port).SetProxyPassword(consts.ProxyTestPasswd)
	if predixyTest.Err != nil {
		return
	}
	predixyTest.ClearPredixy(clearDataDir)
}

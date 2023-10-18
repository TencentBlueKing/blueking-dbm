package redistest

import (
	"encoding/json"
	"fmt"
	"path/filepath"
	"time"

	"dbm-services/redis/db-tools/dbactuator/mylog"
	"dbm-services/redis/db-tools/dbactuator/pkg/atomjobs/atomredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// BkDBmonInstallTest 安装bk-dbmon测试
type BkDBmonInstallTest struct {
	atomredis.BkDbmonInstallParams
	Err error `json:"-"`
}

// SetBkDbmonPkg 设置 bk-dbmon pkg信息
func (test *BkDBmonInstallTest) SetBkDbmonPkg(pkg, pkgMd5 string) *BkDBmonInstallTest {
	if test.Err != nil {
		return test
	}
	if pkg == "" || pkgMd5 == "" {
		pkg = "bk-dbmon-v0.2.tar.gz"
		pkgMd5 = "99081e28443d0615b151ae82e74b69e4"
	}
	test.BkDbmonPkg.Pkg = pkg
	test.BkDbmonPkg.PkgMd5 = pkgMd5
	return test
}

// SetDbtoolsPkg set dbtools pkg信息,传入为空则 pkg=dbtools.tar.gz, pkgMd5=334cf6e3b84d371325052d961584d5aa
func (test *BkDBmonInstallTest) SetDbtoolsPkg(pkg, pkgMd5 string) *BkDBmonInstallTest {
	if test.Err != nil {
		return test
	}
	if pkg == "" || pkgMd5 == "" {
		pkg = "dbtools.tar.gz"
		pkgMd5 = "334cf6e3b84d371325052d961584d5aa"
	}
	test.DbToolsPkg.Pkg = pkg
	test.DbToolsPkg.PkgMd5 = pkgMd5
	return test
}

// SetBackupConf 设置备份配置
func (test *BkDBmonInstallTest) SetBackupConf() *BkDBmonInstallTest {
	if test.Err != nil {
		return test
	}
	test.GsePath = "/usr/local/gse_bkte"
	test.RedisFullBackup = map[string]interface{}{
		"to_backup_system":    "no",
		"old_file_left_day":   2,
		"cron":                "0 5,13,21 * * *",
		"tar_split":           true,
		"tar_split_part_size": "8G",
	}
	test.RedisBinlogBackup = map[string]interface{}{
		"to_backup_system":  "no",
		"old_file_left_day": 2,
		"cron":              "@every 10m",
	}
	test.RedisHeartbeat = map[string]interface{}{
		"cron": "@every 10s",
	}
	test.RedisMonitor = map[string]interface{}{
		"bkmonitor_event_data_id":  542898,
		"bkmonitor_event_token":    "xxxxxx",
		"bkmonitor_metric_data_id": 11111,
		"bkmonitor_metirc_token":   "xxxx",
		"cron":                     "@every 1m",
	}
	test.RedisKeyLifecyckle = map[string]interface{}{
		"stat_dir": "/data/dbbak/keylifecycle",
		"cron":     fmt.Sprintf("%d %d * * *", time.Now().Minute()+1, time.Now().Hour()),
		"hotkey_conf": map[string]interface{}{
			"top_count":        10,
			"duration_seconds": 30,
		},
		"bigkey_conf": map[string]interface{}{
			"top_count":        10,
			"duration_seconds": 60 * 60 * 5,
			"on_master":        false,
			"use_rdb":          true,
			"disk_max_usage":   65,
			"keymod_spec":      "[]",
			"keymod_engine":    "default",
		},
	}
	return test
}

func getRedisClusterServerShargs(ip string, startPort, instNum int, dbType string) (shards map[string]string) {
	if !consts.IsTwemproxyClusterType(dbType) {
		return
	}
	if startPort == 0 {
		startPort = consts.TestRedisMasterStartPort
	}
	if instNum == 0 {
		instNum = 4
	}
	var port int
	var instStr string
	var segStart int
	var segEnd int
	shards = make(map[string]string)
	segStep := (consts.TwemproxyMaxSegment + 1) / instNum
	for i := 0; i < instNum; i++ {
		segStart = i * segStep
		segEnd = (i+1)*segStep - 1
		port = startPort + i
		instStr = fmt.Sprintf("%s:%d", ip, port)
		shards[instStr] = fmt.Sprintf("%d-%d", segStart, segEnd)
	}
	return
}

// AppendMasterServer append master server
func (test *BkDBmonInstallTest) AppendMasterServer(masterIP string, startPort, instNum int,
	dbType string) *BkDBmonInstallTest {
	if test.Err != nil {
		return test
	}
	ports := make([]int, 0, instNum)
	if startPort == 0 {
		startPort = consts.TestTendisPlusMasterStartPort
	}
	if instNum == 0 {
		instNum = 4
	}
	for i := 0; i < instNum; i++ {
		ports = append(ports, startPort+i)
	}
	svrItem := atomredis.ConfServerItem{
		BkBizID:       "200500194",
		BkCloudID:     246,
		App:           "testapp",
		AppName:       "测试app",
		ClusterDomain: "tendisx.aaaa.testapp.db",
		ClusterName:   "aaaa",
		ClusterType:   dbType,
		MetaRole:      consts.MetaRoleRedisMaster,
		ServerIP:      masterIP,
		ServerPorts:   ports,
		ServerShards:  getRedisClusterServerShargs(masterIP, startPort, instNum, dbType),
	}
	test.Servers = append(test.Servers, svrItem)
	return test
}

// OnlyAEmptyServer 将servers中只保留一个实例,且实例ports=[]int{}为空
func (test *BkDBmonInstallTest) OnlyAEmptyServer(ip string) *BkDBmonInstallTest {
	if test.Err != nil {
		return test
	}
	svrItem := atomredis.ConfServerItem{
		BkBizID:       "",
		BkCloudID:     0,
		ClusterDomain: "",
		MetaRole:      consts.MetaRoleRedisMaster,
		ServerIP:      ip,
		ServerPorts:   []int{},
	}
	test.Servers = []atomredis.ConfServerItem{svrItem}
	return test
}

// AppendSlaveServer append slave server
func (test *BkDBmonInstallTest) AppendSlaveServer(slaveIP string, startPort, instNum int,
	dbType string) *BkDBmonInstallTest {
	if test.Err != nil {
		return test
	}
	ports := make([]int, 0, instNum)
	if startPort == 0 {
		startPort = consts.TestTendisPlusSlaveStartPort
	}
	if instNum == 0 {
		instNum = 4
	}
	for i := 0; i < instNum; i++ {
		ports = append(ports, startPort+i)
	}
	svrItem := atomredis.ConfServerItem{
		BkBizID:       "200500194",
		BkCloudID:     246,
		App:           "testapp",
		AppName:       "测试app",
		ClusterDomain: "tendisx.aaaa.testapp.db",
		ClusterName:   "aaaa",
		ClusterType:   dbType,
		MetaRole:      consts.MetaRoleRedisSlave,
		ServerIP:      slaveIP,
		ServerPorts:   ports,
		ServerShards:  getRedisClusterServerShargs(slaveIP, startPort, instNum, dbType),
	}
	test.Servers = append(test.Servers, svrItem)
	return test
}

// InstallBkDbmon 安装bk-dbmon
func (test *BkDBmonInstallTest) InstallBkDbmon() {
	msg := fmt.Sprintf("=========Install_bkDbmon test start============")
	fmt.Println(msg)

	defer func() {
		if test.Err != nil {
			msg = fmt.Sprintf("=========Install_bkDbmon test fail============")
		} else {
			msg = fmt.Sprintf("=========Install_bkDbmon test success============")
		}
		fmt.Println(msg)
	}()
	paramBytes, _ := json.Marshal(test)
	// fmt.Printf("-------payload(raw)--------\n%s\n\n", string(paramBytes))
	// encodeStr := base64.StdEncoding.EncodeToString(paramBytes)
	instllCmd := fmt.Sprintf(consts.ActuatorTestCmd, atomredis.NewBkDbmonInstall().Name(), string(paramBytes))
	fmt.Println(instllCmd)
	_, test.Err = util.RunBashCmd(instllCmd, "", nil, 1*time.Hour)
	if test.Err != nil {
		return
	}
	return
}

// StopBkDbmon stop bk-dbmon
func (test *BkDBmonInstallTest) StopBkDbmon() (err error) {
	if util.FileExists(consts.BkDbmonBin) {
		stopScript := filepath.Join(consts.BkDbmonPath, "stop.sh")
		stopCmd := fmt.Sprintf("su %s -c '%s'", consts.MysqlAaccount, "sh "+stopScript)
		mylog.Logger.Info(stopCmd)
		_, err = util.RunLocalCmd("su", []string{consts.MysqlAaccount, "-c", "sh " + stopScript},
			"", nil, 1*time.Minute)
		return
	}
	killCmd := `
pid=$(ps aux|grep 'bk-dbmon --config'|grep -v dbactuator|grep -v grep|awk '{print $2}')
if [[ -n $pid ]]
then
kill $pid
fi
`
	mylog.Logger.Info(killCmd)
	_, err = util.RunBashCmd(killCmd, "", nil, 1*time.Minute)
	return
}

var (
	bkdbmonTest BkDBmonInstallTest = BkDBmonInstallTest{}
)

// BkDbmonInstall bk-dbmon安装测试
func BkDbmonInstall(serverIP, dbtoolsPkgName, dbtoolsPkgMd5, bkdbmonPkgName, bkdbmonPkgMd5, dbType string) (err error) {
	bkdbmonTest = BkDBmonInstallTest{}
	masterStartPort := 0
	slaveStartPort := 0
	if consts.IsRedisInstanceDbType(dbType) {
		masterStartPort = consts.TestRedisMasterStartPort
		slaveStartPort = consts.TestRedisSlaveStartPort
	} else if consts.IsTendisplusInstanceDbType(dbType) {
		masterStartPort = consts.TestTendisPlusMasterStartPort
		slaveStartPort = consts.TestTendisPlusSlaveStartPort
	}
	bkdbmonTest.
		SetBkDbmonPkg(bkdbmonPkgName, bkdbmonPkgMd5).
		SetDbtoolsPkg(dbtoolsPkgName, dbtoolsPkgMd5).
		SetBackupConf().
		AppendMasterServer(serverIP, masterStartPort, consts.TestRedisInstanceNum, dbType).
		AppendSlaveServer(serverIP, slaveStartPort, consts.TestRedisInstanceNum, dbType)
	if bkdbmonTest.Err != nil {
		return
	}
	bkdbmonTest.InstallBkDbmon()
	return bkdbmonTest.Err
}

// BkDbmonStop bk-dbmon stop
func BkDbmonStop() (err error) {
	return bkdbmonTest.StopBkDbmon()
}

// BkDbmonStopNew bk-dbmon stop
func BkDbmonStopNew(serverIP, dbtoolsPkgName, dbtoolsPkgMd5, bkdbmonPkgName, bkdbmonPkgMd5 string) (err error) {
	bkdbmonTest = BkDBmonInstallTest{}
	bkdbmonTest.
		SetBkDbmonPkg(bkdbmonPkgName, bkdbmonPkgMd5).
		SetDbtoolsPkg(dbtoolsPkgName, dbtoolsPkgMd5).
		SetBackupConf().
		OnlyAEmptyServer(serverIP)
	if bkdbmonTest.Err != nil {
		return
	}
	bkdbmonTest.InstallBkDbmon()
	return bkdbmonTest.Err
}

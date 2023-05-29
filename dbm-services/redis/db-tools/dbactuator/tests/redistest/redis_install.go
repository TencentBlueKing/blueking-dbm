package redistest

import (
	"dbm-services/redis/db-tools/dbactuator/pkg/atomjobs/atomredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
	"encoding/json"
	"fmt"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

// RedisInstallTest 安装测试
type RedisInstallTest struct {
	atomredis.RedisInstallParams
	Err error `json:"-"`
}

// SetIP set ip,传入为空则自动获取本地ip
func (test *RedisInstallTest) SetIP(ip string) *RedisInstallTest {
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

// SetPorts set ports
// 如果ports=[],startPort=0,instNum=0,则默认startPort=40000,instNum=4
func (test *RedisInstallTest) SetPorts(ports []int, startPort, instNum int) *RedisInstallTest {
	if test.Err != nil {
		return test
	}
	if len(ports) == 0 {
		if startPort == 0 {
			startPort = consts.TestTendisPlusMasterStartPort
		}
		if instNum == 0 {
			instNum = 4
		}
		for i := 0; i < instNum; i++ {
			ports = append(ports, startPort+i)
		}
	}
	test.Ports = ports
	test.StartPort = startPort
	test.InstNum = instNum
	return test
}

// SetPassword set password,传入为空则password=xxxxx
func (test *RedisInstallTest) SetPassword(password string) *RedisInstallTest {
	if test.Err != nil {
		return test
	}
	if password == "" {
		password = "xxxx"
	}
	test.Password = password
	return test
}

// SetRedisMediaPkg set redis pkg信息,传入为空则pkg=redis-6.2.7.tar.gz,pkgMd5=ab596d27e8fa545ea5f374d0cc9b263e
func (test *RedisInstallTest) SetRedisMediaPkg(pkg, pkgMd5 string) *RedisInstallTest {
	if test.Err != nil {
		return test
	}
	if pkg == "" || pkgMd5 == "" {
		pkg = "redis-6.2.7.tar.gz"
		pkgMd5 = "ab596d27e8fa545ea5f374d0cc9b263e"
	}
	test.Pkg = pkg
	test.PkgMd5 = pkgMd5
	return test
}

// SetDbtoolsPkg set dbtools pkg信息,传入为空则 pkg=dbtools.tar.gz, pkgMd5=334cf6e3b84d371325052d961584d5aa
func (test *RedisInstallTest) SetDbtoolsPkg(pkg, pkgMd5 string) *RedisInstallTest {
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

// SetDatabases 设置databases,默认为2
func (test *RedisInstallTest) SetDatabases(databases int) *RedisInstallTest {
	if test.Err != nil {
		return test
	}
	if databases == 0 {
		databases = 2
	}
	test.Databases = databases
	return test
}

// SetDbType 设置DbType,默认为 PredixyTendisplusCluster
func (test *RedisInstallTest) SetDbType(dbType string) *RedisInstallTest {
	if test.Err != nil {
		return test
	}
	if dbType == "" {
		dbType = "PredixyTendisplusCluster"
	}
	test.DbType = dbType
	return test
}

// SetMaxMemory 设置
func (test *RedisInstallTest) SetMaxMemory(maxMemory uint64) *RedisInstallTest {
	if test.Err != nil {
		return test
	}
	test.MaxMemory = maxMemory
	return test
}

// InstallTendisplus 安装tendisplus
func (test *RedisInstallTest) InstallTendisplus() {
	msg := fmt.Sprintf("=========install_tendisplus test start============")
	fmt.Println(msg)

	defer func() {
		if test.Err != nil {
			msg = fmt.Sprintf("=========install_tendisplus test fail============")
		} else {
			msg = fmt.Sprintf("=========install_tendisplus test success============")
		}
		fmt.Println(msg)
	}()
	test.SetTendisplusRedisConf()
	paramBytes, _ := json.Marshal(test)
	// fmt.Printf("-------payload(raw)--------\n%s\n\n", string(paramBytes))
	// encodeStr := base64.StdEncoding.EncodeToString(paramBytes)
	instllCmd := fmt.Sprintf(consts.ActuatorTestCmd, atomredis.NewRedisInstall().Name(), string(paramBytes))
	fmt.Println(instllCmd)
	_, test.Err = util.RunBashCmd(instllCmd, "", nil, 1*time.Hour)
	if test.Err != nil {
		return
	}
	return
}

// InstallCacheRedis 安装cache redis
func (test *RedisInstallTest) InstallCacheRedis() {
	msg := fmt.Sprintf("=========install_cache_redis test start============")
	fmt.Println(msg)

	defer func() {
		if test.Err != nil {
			msg = fmt.Sprintf("=========install_cache_redis test fail============")
		} else {
			msg = fmt.Sprintf("=========install_cache_redis test success============")
		}
		fmt.Println(msg)
	}()

	test.SetCacheRedisConf()
	paramBytes, _ := json.Marshal(test)
	// fmt.Printf("-------payload(raw)--------\n%s\n\n", string(paramBytes))
	// encodeStr := base64.StdEncoding.EncodeToString(paramBytes)
	instllCmd := fmt.Sprintf(consts.ActuatorTestCmd, atomredis.NewRedisInstall().Name(), string(paramBytes))
	fmt.Println(instllCmd)
	_, test.Err = util.RunBashCmd(instllCmd, "", nil, 1*time.Hour)
	if test.Err != nil {
		return
	}
	return
}

// InstallTendisSSD 安装 tendisSSD
func (test *RedisInstallTest) InstallTendisSSD() {
	msg := fmt.Sprintf("=========install_tendisSSD test start============")
	fmt.Println(msg)

	defer func() {
		if test.Err != nil {
			msg = fmt.Sprintf("=========install_tendisSSD test fail============")
		} else {
			msg = fmt.Sprintf("=========install_tendisSSD test success============")
		}
		fmt.Println(msg)
	}()

	test.SetTendisSSDRedisConf()
	paramBytes, _ := json.Marshal(test)
	// fmt.Printf("-------payload(raw)--------\n%s\n\n", string(paramBytes))
	// encodeStr := base64.StdEncoding.EncodeToString(paramBytes)
	instllCmd := fmt.Sprintf(consts.ActuatorTestCmd, atomredis.NewRedisInstall().Name(), string(paramBytes))
	fmt.Println(instllCmd)
	_, test.Err = util.RunBashCmd(instllCmd, "", nil, 1*time.Hour)
	if test.Err != nil {
		return
	}
	return
}

func tendisplusStillRunning() bool {
	grepCmd := `ps aux|grep "/usr/local/redis/bin/tendisplus"|grep -v grep || true;`
	ret, _ := util.RunBashCmd(grepCmd, "", nil, 10*time.Second)
	ret = strings.TrimSpace(ret)
	if ret != "" {
		return true
	}
	return false
}

// ClearTendisplus 清理tendisplus环境
// 关闭tendisplus进程,清理数据目录,清理 /usr/local/redis
func (test *RedisInstallTest) ClearTendisplus(clearDataDir bool) {
	dataDirs := []string{}
	var dir string
	for i := 0; i < test.InstNum; i++ {
		dataDirs = append(dataDirs, filepath.Join(consts.GetRedisDataDir(), "redis", strconv.Itoa(test.Ports[i])))
		StopRedisProcess(test.IP, test.Ports[i], test.Password, "tendisplus")
	}

	if clearDataDir {
		for _, dir = range dataDirs {
			if strings.Contains(dir, "redis") && util.FileExists(dir) {
				fmt.Println("rm -rf " + dir)
				util.RunBashCmd("rm -rf "+dir, "", nil, 1*time.Minute)
			}
		}
	}
	if !tendisplusStillRunning() {
		dir = "/usr/local/redis"
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
	time.Sleep(2 * time.Second)
}

func redisserverStillRunning() bool {
	grepCmd := `ps aux|grep "/usr/local/redis/bin/redis-server"|grep -v grep || true;`
	ret, _ := util.RunBashCmd(grepCmd, "", nil, 10*time.Second)
	ret = strings.TrimSpace(ret)
	if ret != "" {
		return true
	}
	return false
}

// ClearCacheRedis 清理Redis环境
// 关闭Redis进程,清理数据目录,清理 /usr/local/redis
func (test *RedisInstallTest) ClearCacheRedis(clearDataDir bool) {
	dataDirs := []string{}
	var dir string
	for i := 0; i < test.InstNum; i++ {
		dataDirs = append(dataDirs, filepath.Join(consts.GetRedisDataDir(), "redis", strconv.Itoa(test.Ports[i])))
		StopRedisProcess(test.IP, test.Ports[i], test.Password, "redis-server")
	}

	if clearDataDir {
		for _, dir = range dataDirs {
			if strings.Contains(dir, "redis") && util.FileExists(dir) {
				fmt.Println("rm -rf " + dir)
				util.RunBashCmd("rm -rf "+dir, "", nil, 1*time.Minute)
			}
		}
	}
	if !redisserverStillRunning() {
		dir = "/usr/local/redis"
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
	time.Sleep(2 * time.Second)
}

// SetCacheRedisConf 设置cache redis dbConfig
func (test *RedisInstallTest) SetCacheRedisConf() {
	test.RedisConfConfigs = map[string]string{
		"bind":                        "{{address}} 127.0.0.1",
		"port":                        "{{port}}",
		"requirepass":                 "{{password}}",
		"maxmemory":                   "{{maxmemory}}",
		"logfile":                     "{{redis_data_dir}}/redis.log",
		"pidfile":                     "{{redis_data_dir}}/redis.pid",
		"dir":                         "{{redis_data_dir}}/data",
		"databases":                   "{{databases}}",
		"cluster-enabled":             "{{cluster_enabled}}",
		"daemonize":                   "yes",
		"tcp-keepalive":               "300",
		"protected-mode":              "yes",
		"maxmemory-policy":            "noeviction",
		"tcp-backlog":                 "511",
		"timeout":                     "0",
		"supervised":                  "no",
		"hz":                          "10",
		"maxclients":                  "180000",
		"loglevel":                    "notice",
		"always-show-logo":            "yes",
		"save":                        "",
		"stop-writes-on-bgsave-error": "yes",
		"rdbcompression":              "yes",
		"rdbchecksum":                 "yes",
		"dbfilename":                  "dump.rdb",
		"slave-serve-stale-data":      "yes",
		"slave-read-only":             "yes",
		"repl-diskless-sync":          "no",
		"slave-priority":              "100",
		"rename-command": `flushdb cleandb
                rename-command flushall cleanall
                rename-command debug nobug
                rename-command keys mykeys`,
		"lazyfree-lazy-eviction":        "yes",
		"lazyfree-lazy-expire":          "yes",
		"lazyfree-lazy-server-del":      "yes",
		"slave-lazy-flush":              "yes",
		"appendonly":                    "no",
		"appendfilename":                "appendonly.aof",
		"appendfsync":                   "everysec",
		"no-appendfsync-on-rewrite":     "yes",
		"auto-aof-rewrite-percentage":   "100",
		"auto-aof-rewrite-min-size":     "64mb",
		"aof-load-truncated":            "yes",
		"aof-use-rdb-preamble":          "no",
		"aof-rewrite-incremental-fsync": "yes",
		"lua-time-limit":                "5000",
		"cluster-config-file":           "nodes.conf",
		"cluster-node-timeout":          "15000",
		"client-output-buffer-limit": `normal 256mb 512mb 300
                client-output-buffer-limit slave 2048mb 2048mb 300
                client-output-buffer-limit pubsub 32mb 8mb 60`,
		"hash-max-ziplist-entries": "512",
		"hash-max-ziplist-value":   "64",
		"list-max-ziplist-size":    "-2",
		"list-compress-depth":      "0",
		"zset-max-ziplist-entries": "128",
		"zset-max-ziplist-value":   "64",
		"hll-sparse-max-bytes":     "3000",
		"activerehashing":          "yes",
		"slowlog-log-slower-than":  "10000",
		"slowlog-max-len":          "256",
	}
}

// SetTendisplusRedisConf 设置tendisplus dbConfig
func (test *RedisInstallTest) SetTendisplusRedisConf() {
	test.RedisConfConfigs = map[string]string{
		"bind":                                "{{address}}",
		"port":                                "{{port}}",
		"loglevel":                            "notice",
		"logdir":                              "{{redis_data_dir}}/data/log",
		"dir":                                 "{{redis_data_dir}}/data/db",
		"dumpdir":                             "{{redis_data_dir}}/data/dump",
		"pidfile":                             "{{redis_data_dir}}data/tendisplus.pid",
		"slowlog":                             "{{redis_data_dir}}/data/slowlog",
		"databases":                           "{{databases}}",
		"requirepass":                         "{{password}}",
		"masterauth":                          "{{password}}",
		"cluster-enabled":                     "{{cluster_enabled}}",
		"executorWorkPoolSize":                "2",
		"executorThreadNum":                   "24",
		"netIoThreadNum":                      "3",
		"noexpire":                            "no",
		"rocks.blockcachemb":                  "{{rocks_blockcachemb}}",
		"kvstorecount":                        "10",
		"rocks.compress_type":                 "lz4",
		"rocks.max_background_compactions":    "12",
		"rocks.write_buffer_size":             "{{rocks_write_buffer_size}}",
		"binlog-using-defaultCF":              "off",
		"maxBinlogKeepNum":                    "1",
		"netBatchSize":                        "1048576",
		"netBatchTimeoutSec":                  "10",
		"cluster-migration-rate-limit":        "200",
		"migrateReceiveThreadnum":             "4",
		"migrateSenderThreadnum":              "4",
		"migrate-snapshot-key-num":            "30000",
		"slave-migrate-enabled":               "on",
		"rocks.cache_index_and_filter_blocks": "0",
		"truncateBinlogNum":                   "10000000",
		"domain-enabled":                      "off",
		"pauseTimeIndexMgr":                   "1",
		"scanCntIndexMgr":                     "10000",
		"truncateBinlogIntervalMs":            "100",
		"minbinlogkeepsec":                    "1800",
		"binlogdelrange":                      "500000",
		"migrate-gc-enabled":                  "false",
		"deletefilesinrange-for-binlog":       "1",
		"incrpushthreadnum":                   "10",
		"rename-command": `config confxx 
                rename-command flushdb cleandb 
                rename-command flushall cleanall
                rename-command debug nobug
                rename-command keys mykeys`,
	}
}

// SetTendisSSDRedisConf 设置tendisssd dbConfig
func (test *RedisInstallTest) SetTendisSSDRedisConf() {
	test.RedisConfConfigs = map[string]string{
		"activerehashing":               "yes",
		"aof-rewrite-incremental-fsync": "yes",
		"appendfilename":                "appendonly.aof",
		"appendfsync":                   "everysec",
		"appendonly":                    "no",
		"auto-aof-rewrite-min-size":     "64mb",
		"auto-aof-rewrite-percentage":   "100",
		"bind":                          "{{address}} 127.0.0.1",
		"binlog-enabled":                "1",
		"binlog-filesize":               "268435456",
		"clean-time":                    "3",
		"client-output-buffer-limit": `normal 256mb 512mb 300
			client-output-buffer-limit slave 2048mb 2048mb 300
			client-output-buffer-limit pubsub 32mb 8mb 60`,
		"daemonize":                 "yes",
		"databases":                 "{{databases}}",
		"dbfilename":                "dump.rdb",
		"dir":                       "{{redis_data_dir}}/data",
		"disk-delete-count":         "50",
		"disk-delete-time":          "50",
		"dumpdir":                   "{{redis_data_dir}}/rbinlog/",
		"hash-max-ziplist-entries":  "512",
		"hash-max-ziplist-value":    "64",
		"hz":                        "10",
		"list-max-ziplist-entries":  "512",
		"list-max-ziplist-value":    "64",
		"log-count":                 "200000",
		"log-keep-count":            "20000000",
		"log-keep-time":             "36000",
		"logfile":                   "{{redis_data_dir}}/redis.log",
		"loglevel":                  "notice",
		"lua-time-limit":            "5000",
		"max_manifest_file_size":    "200000000",
		"max_open_files":            "100000",
		"maxclients":                "50000",
		"maxmemory":                 "{{maxmemory}}",
		"maxmemory-policy":          "noeviction",
		"no-appendfsync-on-rewrite": "no",
		"pause-clean-time":          "5",
		"pause-scan-expires-time":   "100",
		"pidfile":                   "{{redis_data_dir}}/redis.pid",
		"port":                      "{{port}}",
		"rdbchecksum":               "yes",
		"rdbcompression":            "yes",
		"rename-command": `config confxx 
			rename-command debug nobug
			rename-command keys mykeys`,
		"repl-disable-tcp-nodelay":    "no",
		"repl-mode":                   "tredis-binlog",
		"repl-timeout":                "600",
		"requirepass":                 "{{password}}",
		"rocksdb_block_cache":         "500000000",
		"rocksdb_block_size":          "32000",
		"rocksdb_write_buffer_size":   "32000000",
		"save":                        "",
		"scan-expires-time":           "1",
		"set-max-intset-entries":      "512",
		"slave-priority":              "100",
		"slave-read-only":             "yes",
		"slave-serve-stale-data":      "yes",
		"slowlog-log-slower-than":     "10000",
		"slowlog-max-len":             "256",
		"stop-writes-on-bgsave-error": "yes",
		"target_file_size_base":       "8000000",
		"tcp-keepalive":               "300",
		"timeout":                     "0",
		"write_batch_size":            "2",
		"zset-max-ziplist-entries":    "128",
		"zset-max-ziplist-value":      "64",
	}
}

// RedisInstanceInstall cache安装
func RedisInstanceInstall(serverIP,
	redisPkgName, redisPkgMd5,
	dbtoolsPkgName, dbtoolsPkgMd5,
	dbType string, startPort, numbers int) (err error) {
	cacheMasterTest := RedisInstallTest{}
	cacheMasterTest.SetIP(serverIP).
		SetPorts([]int{}, startPort, numbers).
		SetPassword(consts.RedisTestPasswd).
		SetRedisMediaPkg(redisPkgName, redisPkgMd5).
		SetDbtoolsPkg(dbtoolsPkgName, dbtoolsPkgMd5).
		SetDbType(dbType).
		SetDatabases(2).SetMaxMemory(8589934592)
	if cacheMasterTest.Err != nil {
		return cacheMasterTest.Err
	}
	cacheMasterTest.InstallCacheRedis()
	if cacheMasterTest.Err != nil {
		return
	}
	return
}

// RedisInstanceClear cache清理
func RedisInstanceClear(serverIP, dbType string,
	clearDataDir bool, startPort, numbers int) (err error) {
	cacheMasterTest := RedisInstallTest{}
	cacheMasterTest.SetIP(serverIP).
		SetPorts([]int{}, startPort, numbers).
		SetPassword(consts.RedisTestPasswd).
		SetDbType(dbType).
		SetDatabases(2).SetMaxMemory(8589934592)
	if cacheMasterTest.Err != nil {
		return cacheMasterTest.Err
	}
	cacheMasterTest.ClearCacheRedis(clearDataDir)
	if cacheMasterTest.Err != nil {
		return
	}
	return
}

// 下面这些的 install 和 clear函数只是端口不同,其他的均一样

// RedisInstanceMasterInstall cache master安装
func RedisInstanceMasterInstall(serverIP,
	redisPkgName, redisPkgMd5,
	dbtoolsPkgName, dbtoolsPkgMd5,
	dbType string) (err error) {
	return RedisInstanceInstall(serverIP,
		redisPkgName, redisPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5,
		dbType,
		consts.TestRedisMasterStartPort,
		consts.TestRedisInstanceNum)
}

// RedisInstanceMasterClear cache master清理
func RedisInstanceMasterClear(serverIP, dbType string,
	clearDataDir bool) (err error) {
	return RedisInstanceClear(serverIP,
		dbType, clearDataDir,
		consts.TestRedisMasterStartPort,
		consts.TestRedisInstanceNum,
	)
}

// RedisInstanceSlaveInstall cache slave安装
func RedisInstanceSlaveInstall(serverIP,
	redisPkgName, redisPkgMd5,
	dbtoolsPkgName, dbtoolsPkgMd5,
	dbType string) (err error) {
	return RedisInstanceInstall(serverIP,
		redisPkgName, redisPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5,
		dbType,
		consts.TestRedisSlaveStartPort,
		consts.TestRedisInstanceNum)
}

// RedisInstanceSlaveClear cache slave清理
func RedisInstanceSlaveClear(serverIP, dbType string, clearDataDir bool) (err error) {
	return RedisInstanceClear(serverIP,
		dbType, clearDataDir,
		consts.TestRedisSlaveStartPort,
		consts.TestRedisInstanceNum,
	)
}

// RedisSyncMasterInstall cache master安装
func RedisSyncMasterInstall(serverIP,
	redisPkgName, redisPkgMd5,
	dbtoolsPkgName, dbtoolsPkgMd5,
	dbType string) (err error) {
	return RedisInstanceInstall(serverIP,
		redisPkgName, redisPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5,
		dbType,
		consts.TestSyncRedisMasterStartPort,
		consts.TestRedisInstanceNum)
}

// RedisSyncMasterClear cache master清理
func RedisSyncMasterClear(serverIP, dbType string, clearDataDir bool) (err error) {
	return RedisInstanceClear(serverIP,
		dbType, clearDataDir,
		consts.TestSyncRedisMasterStartPort,
		consts.TestRedisInstanceNum,
	)
}

// RedisSyncSlaveInstall cache slave安装
func RedisSyncSlaveInstall(serverIP,
	redisPkgName, redisPkgMd5,
	dbtoolsPkgName, dbtoolsPkgMd5,
	dbType string) (err error) {
	return RedisInstanceInstall(serverIP,
		redisPkgName, redisPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5,
		dbType,
		consts.TestSyncRedisSlaveStartPort,
		consts.TestRedisInstanceNum)
}

// RedisSyncSlaveClear cache slave清理
func RedisSyncSlaveClear(serverIP, dbType string, clearDataDir bool) (err error) {
	return RedisInstanceClear(serverIP,
		dbType, clearDataDir,
		consts.TestSyncRedisSlaveStartPort,
		consts.TestRedisInstanceNum,
	)
}

// TendisplusInstall 安装tendisplus实例
func TendisplusInstall(serverIP,
	tendisplusPkgName, tendisplusPkgMd5,
	dbtoolsPkgName, dbtoolsPkgMd5,
	dbType string, port, numbers int) (err error) {
	plusMasterTest := RedisInstallTest{}
	plusMasterTest.SetIP(serverIP).
		SetPorts([]int{}, port, numbers).
		SetPassword(consts.RedisTestPasswd).
		SetRedisMediaPkg(tendisplusPkgName, tendisplusPkgMd5).
		SetDbtoolsPkg(dbtoolsPkgName, dbtoolsPkgMd5).
		SetDbType(dbType).
		SetDatabases(1).SetMaxMemory(8589934592)
	if plusMasterTest.Err != nil {
		return plusMasterTest.Err
	}
	plusMasterTest.InstallTendisplus()
	if plusMasterTest.Err != nil {
		return plusMasterTest.Err
	}
	return nil
}

// TendisplusClear tendisplus实例清理
func TendisplusClear(serverIP, dbType string,
	clearDataDir bool,
	port, numbers int) (err error) {
	plusMasterTest := RedisInstallTest{}
	plusMasterTest.SetIP(serverIP).
		SetPorts([]int{}, port, numbers).
		SetPassword(consts.RedisTestPasswd).
		SetDbType(dbType).
		SetDatabases(1).SetMaxMemory(8589934592)
	if plusMasterTest.Err != nil {
		return plusMasterTest.Err
	}
	plusMasterTest.ClearTendisplus(clearDataDir)
	if plusMasterTest.Err != nil {
		return plusMasterTest.Err
	}
	return nil
}

// TendisplusMasterInstall 安装tendisplus master实例
func TendisplusMasterInstall(serverIP,
	tendisplusPkgName, tendisplusPkgMd5,
	dbtoolsPkgName, dbtoolsPkgMd5,
	dbType string) (err error) {

	return TendisplusInstall(serverIP,
		tendisplusPkgName, tendisplusPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5,
		dbType, consts.TestTendisPlusMasterStartPort,
		consts.TestRedisInstanceNum)
}

// TendisplusMasterClear tendisplus实例清理
func TendisplusMasterClear(serverIP, dbType string, clearDataDir bool) (err error) {
	return TendisplusClear(serverIP, dbType, clearDataDir,
		consts.TestTendisPlusMasterStartPort,
		consts.TestRedisInstanceNum,
	)
}

// TendisplusSlaveInstall 安装tendisplus slave实例
func TendisplusSlaveInstall(serverIP,
	tendisplusPkgName, tendisplusPkgMd5,
	dbtoolsPkgName, dbtoolsPkgMd5,
	dbType string) (err error) {
	return TendisplusInstall(serverIP,
		tendisplusPkgName, tendisplusPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5,
		dbType, consts.TestTendisPlusSlaveStartPort,
		consts.TestRedisInstanceNum)
}

// TendisplusSlaveClear tendisplus slave实例清理
func TendisplusSlaveClear(serverIP, dbType string, clearDataDir bool) (err error) {
	return TendisplusClear(serverIP, dbType, clearDataDir,
		consts.TestTendisPlusSlaveStartPort,
		consts.TestRedisInstanceNum,
	)
}

// TendisplusSyncMasterInstall 安装tendisplus sync master实例
func TendisplusSyncMasterInstall(serverIP,
	tendisplusPkgName, tendisplusPkgMd5,
	dbtoolsPkgName, dbtoolsPkgMd5,
	dbType string) (err error) {
	return TendisplusInstall(serverIP,
		tendisplusPkgName, tendisplusPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5,
		dbType, consts.TestSyncTendisPlusMasterStartPort,
		consts.TestRedisInstanceNum)
}

// TendisplusSyncMasterClear tendisplus sync master清理
func TendisplusSyncMasterClear(serverIP, dbType string, clearDataDir bool) (err error) {
	return TendisplusClear(serverIP, dbType, clearDataDir,
		consts.TestSyncTendisPlusMasterStartPort,
		consts.TestRedisInstanceNum,
	)
}

// TendisplusSyncSlaveInstall 安装tendisplus sync slave实例
func TendisplusSyncSlaveInstall(serverIP,
	tendisplusPkgName, tendisplusPkgMd5,
	dbtoolsPkgName, dbtoolsPkgMd5,
	dbType string) (err error) {
	return TendisplusInstall(serverIP,
		tendisplusPkgName, tendisplusPkgMd5,
		dbtoolsPkgName, dbtoolsPkgMd5,
		dbType, consts.TestSyncTendisPlusSlaveStartPort,
		consts.TestRedisInstanceNum)
}

// TendisplusSyncSlaveClear tendisplus sync slave清理
func TendisplusSyncSlaveClear(serverIP, dbType string, clearDataDir bool) (err error) {
	return TendisplusClear(serverIP, dbType, clearDataDir,
		consts.TestSyncTendisPlusSlaveStartPort,
		consts.TestRedisInstanceNum,
	)
}

// TendisSSDInstall tendisSSD安装
func TendisSSDInstall(serverIP,
	redisPkgName, redisPkgMd5,
	dbtoolsPkgName, dbtoolsPkgMd5,
	dbType string, startPort, numbers int) (err error) {
	ssdMasterTest := RedisInstallTest{}
	ssdMasterTest.SetIP(serverIP).
		SetPorts([]int{}, startPort, numbers).
		SetPassword(consts.RedisTestPasswd).
		SetRedisMediaPkg(redisPkgName, redisPkgMd5).
		SetDbtoolsPkg(dbtoolsPkgName, dbtoolsPkgMd5).
		SetDbType(dbType).
		SetDatabases(2).SetMaxMemory(8589934592)
	if ssdMasterTest.Err != nil {
		return ssdMasterTest.Err
	}
	ssdMasterTest.InstallTendisSSD()
	if ssdMasterTest.Err != nil {
		return ssdMasterTest.Err
	}
	return
}

// TendisSSDClear tendisSSD清理
func TendisSSDClear(serverIP, dbType string,
	clearDataDir bool, startPort, numbers int) (err error) {
	ssdMasterTest := RedisInstallTest{}
	ssdMasterTest.SetIP(serverIP).
		SetPorts([]int{}, startPort, numbers).
		SetPassword(consts.RedisTestPasswd).
		SetDbType(dbType).
		SetDatabases(2).SetMaxMemory(8589934592)
	if ssdMasterTest.Err != nil {
		return ssdMasterTest.Err
	}
	ssdMasterTest.ClearCacheRedis(clearDataDir)
	if ssdMasterTest.Err != nil {
		return ssdMasterTest.Err
	}
	return
}

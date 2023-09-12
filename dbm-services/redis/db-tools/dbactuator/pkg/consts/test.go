package consts

import "fmt"

// test consts
const (
	// ----- tendisplus  master指定的端口范围 [11000,11999] ------
	// ----- tendisplus slave指定的端口范围 [12000,12999] ------
	// TestTendisPlusMasterStartPort master start port
	TestTendisPlusMasterStartPort = 11000
	// TestTendisPlusSlaveStartPort slave start port
	TestTendisPlusSlaveStartPort = 12000
	// TestTendisPlusForgetPort TestTendisPlusForgetPort
	TestTendisPlusForgetPort = 16600

	// ExpansionTestTendisPlusMasterStartPort master start port
	ExpansionTestTendisPlusMasterStartPort = 11100
	// ExpansionTestTendisPlusSlaveStartPort slave start port
	ExpansionTestTendisPlusSlaveStartPort = 12100

	// SlotTestTendisPlusMasterPort master start port
	SlotTestTendisPlusMasterPort = 11200
	// SLotTestTendisPlusSlaveStart slave start port
	SLotTestTendisPlusSlaveStart = 12200
	// SlotsMigrateTest 指定迁移slot
	SlotsMigrateTest = "0-100"

	// TestSyncTendisPlusMasterStartPort make sync /redo slave
	TestSyncTendisPlusMasterStartPort = 11300
	// TestSyncTendisPlusSlaveStartPort make sync /
	TestSyncTendisPlusSlaveStartPort = 12300

	// ----- cache redis master指定的端口范围 [13000,13999] ------
	// ----- cache redis slave指定的端口范围 [14000,14999] ------

	// TestRedisMasterStartPort master start port
	TestRedisMasterStartPort = 13000
	// TestRedisSlaveStartPort slave start port
	TestRedisSlaveStartPort = 14000

	// TestSyncRedisMasterStartPort make sync /redo slave
	TestSyncRedisMasterStartPort = 13300
	// TestSyncRedisSlaveStartPort make sync /
	TestSyncRedisSlaveStartPort = 14300

	// ----- tendisssd master指定的端口范围 [14000,14999] ------
	// ----- tendisssd slave指定的端口范围 [15000,15999] ------

	// TestTendisSSDMasterStartPort master start port
	TestTendisSSDMasterStartPort = 15000
	// TestTendisSSDSlaveStartPort slave start port
	TestTendisSSDSlaveStartPort = 16000

	// TestTwemproxyPort twemproxy port
	TestTwemproxyPort = 50100
	// TestPredixyPort predixy port
	TestPredixyPort = 50200
	// TestSSDClusterTwemproxyPort twemproxy port
	TestSSDClusterTwemproxyPort = 50300

	// TestRedisInstanceNum instance number
	TestRedisInstanceNum = 4

	// ExpansionTestRedisInstanceNum instance number
	ExpansionTestRedisInstanceNum = 2
	// SLotTestRedisInstanceNum instance number
	SLotTestRedisInstanceNum = 1
)
const (
	// RedisTestPasswd redis test password
	RedisTestPasswd = "redisPassTest"
	// ProxyTestPasswd proxy test password
	ProxyTestPasswd = "proxyPassTest"
)

// test uid/rootid/nodeid
const (
	TestUID    = 1111
	TestRootID = 2222
	TestNodeID = 3333
)

var (
	// ActuatorTestCmd actuator测试命令
	ActuatorTestCmd = fmt.Sprintf(
		// NOCC:tosa/linelength(设计如此)
		"cd %s && ./dbactuator_redis  --uid=%d --root_id=%d --node_id=%d --version_id=v1 --atom-job-list=%%q  --payload=%%q --payload-format=raw",
		PackageSavePath, TestUID, TestRootID, TestNodeID)
)

const (
	// PayloadFormatRaw raw
	PayloadFormatRaw = "raw"
	// PayloadFormatBase64 base64
	PayloadFormatBase64 = "base64"
)

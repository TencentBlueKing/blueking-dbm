package consts

import "fmt"

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

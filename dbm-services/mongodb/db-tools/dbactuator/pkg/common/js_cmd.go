package common

import (
	"fmt"
	"strconv"
	"time"

	"dbm-services/common/go-pubpkg/mycmd"
)

// getFcvEval 从 admin.system.version 读取 FCV，输出纯 JSON，避免 shell 默认输出中的扩展类型无法被 encoding/json 解析。
// 兼容连到 secondary 的场景：先开启 secondary 读，再查询 FCV 文档。
const getFcvEval = `try { db.getMongo().setSecondaryOk(); } catch (e) {}
var doc = db.getSiblingDB('admin').getCollection("system.version").findOne({_id:"featureCompatibilityVersion"});
if (doc == null) {
  print(JSON.stringify({ errmsg: "featureCompatibilityVersion document not found" }));
} else {
  var ver = doc.version != null ? String(doc.version) : "";
  if (ver === "") {
    print(JSON.stringify({ errmsg: "empty featureCompatibilityVersion" }));
  } else {
    print(JSON.stringify(ver));
  }
}`

// GetFCV 获取FCV（直接 exec mongo/mongosh，不经 shell）
func GetFCV(mongoBin string, ip string, port int, username string, password string) (string, error) {
	ret, err := mycmd.New(
		mongoBin,
		"-u", username,
		"-p", mycmd.Password(password),
		"--host", ip,
		"--port", strconv.Itoa(port),
		"--authenticationDatabase=admin",
		"--quiet",
		"--eval", getFcvEval,
		"admin",
	).Run(300 * time.Second)
	if err != nil {
		return "", fmt.Errorf(
			"get FCV command failed: cmd=%q exitCode=%d err=%v stdout=%q stderr=%q",
			ret.Cmdline, ret.ExitCode, err, ret.GetStdout(), ret.GetStderr(),
		)
	}
	fcv, parseErr := ParseGetFcvJSON(ret.GetStdout())
	if parseErr != nil {
		return "", fmt.Errorf(
			"parse FCV output failed: cmd=%q exitCode=%d parseErr=%v stdout=%q stderr=%q",
			ret.Cmdline, ret.ExitCode, parseErr, ret.GetStdout(), ret.GetStderr(),
		)
	}
	return fcv, nil
}

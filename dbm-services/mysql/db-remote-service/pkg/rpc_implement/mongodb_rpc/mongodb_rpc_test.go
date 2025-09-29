// precheck_input_test.go
package mongodb_rpc

import (
	"encoding/json"
	"io"
	"net/http"
	"os"
	"strconv"
	"strings"
	"testing"
	"time"

	"github.com/pkg/errors"
)

// cmdResult 命令执行结果
type cmdResult struct {
	Code            int    `json:"code"`
	Data            string `json:"data"`              // 查询结果
	ErrorMsg        string `json:"error_msg"`         // 错误信息
	DebugInfo       string `json:"debug_info"`        // session信息
	SessionReqCount int    `json:"session_req_count"` // 请求次数
}

func runRpcCommand(t *testing.T, httpServer, mongoAddr, user, pwd, adminuser, adminpwd, version,
	setName, clusterId, clusterDomain, token, command, readPref string, oneOff int, timeout int) (*cmdResult, error) {
	path := "/mongodb/rpc"
	clusterIdInt, err := strconv.Atoi(clusterId)
	if err != nil {
		t.Fatalf("Failed to convert clusterId to int: %v", err)
	}
	jsonMap := map[string]any{
		"addresses":       []string{mongoAddr},
		"set_name":        setName,
		"cluster_id":      clusterIdInt,
		"cluster_domain":  clusterDomain,
		"cluster_type":    "MongoReplicaSet",
		"command":         command,
		"username":        user,
		"password":        pwd,
		"admin_username":  adminuser,
		"admin_password":  adminpwd,
		"timeout":         timeout,
		"session":         token,
		"version":         version,
		"read_preference": readPref,
		"one_off":         oneOff,
		"token":           token,
	}
	jsonData, err := json.Marshal(jsonMap)
	if err != nil {
		return nil, errors.Wrap(err, "Failed to marshal json")
	}
	t.Logf("jsonData: %s", jsonData)

	resp, err := http.Post(httpServer+path, "application/json", strings.NewReader(string(jsonData)))
	if err != nil {
		return nil, errors.Wrap(err, "Failed to send request")
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	var cmdResult cmdResult
	err = json.Unmarshal(body, &cmdResult)
	if err != nil {
		return nil, err
	}
	return &cmdResult, nil
}

func runRpcCommand_test(t *testing.T, token, command, readPref string, oneOff int, timeout int) (*cmdResult, error) {
	// vscode you can set env file in settings.json
	httpServer := os.Getenv("DRS_HTTP_SERVER")
	mongoAddr := os.Getenv("MONGO_ADDR")
	user := os.Getenv("MONGO_USER")
	pwd := os.Getenv("MONGO_PWD")
	adminuser := os.Getenv("MONGO_ADMIN_USER")
	adminpwd := os.Getenv("MONGO_ADMIN_PWD")
	version := os.Getenv("MONGO_VERSION")
	setName := os.Getenv("MONGO_SET_NAME")
	clusterId := os.Getenv("MONGO_CLUSTER_ID")
	clusterDomain := os.Getenv("MONGO_CLUSTER_DOMAIN")
	if httpServer == "" {
		t.Fatalf("DRS_HTTP_SERVER is not set")
	}
	return runRpcCommand(t, httpServer, mongoAddr, user, pwd, adminuser, adminpwd, version, setName, clusterId, clusterDomain, token, command, readPref, oneOff, timeout)
}

func TestMongoRPCEmbed_DoCommand(t *testing.T) {
	t1 := time.Now()
	for range 5 {
		cmdResult, err := runRpcCommand_test(t, "token1"+t1.Format("20060102150405"), "db.isMaster().primary", "direct", 0, 3)
		if err != nil {
			t.Fatalf("Failed to run command: %v", err)
		}
		t.Logf("cmdResult: %+v", cmdResult)
		time.Sleep(1 * time.Second)
	}
}

// TestMongoRPCEmbed_DoCommand_Maxsize测试最大数据量限制
func TestMongoRPCEmbed_DoCommand_Maxsize(t *testing.T) {
	t1 := time.Now()
	cmdResult, err := runRpcCommand_test(t, "token"+t1.Format("20060102150405"), "print('xxxx\\n'.repeat(32*1024*1024))", "direct", 0, 3)
	if err != nil {
		t.Fatalf("Failed to run command: %v", err)
	}
	if cmdResult.Code == 0 && strings.Contains(cmdResult.Data, "excess data size") {
		t.Logf("cmdResult: %+v", cmdResult)
	} else {
		t.Fatalf("Failed to run command: %v", cmdResult)
	}
}

// TestMongoRPCEmbed_DoCommand_Maxsize测试最大数据量限制
func TestMongoRPCEmbed_DoCommand_BigData(t *testing.T) {
	t1 := time.Now()
	runRpcCommand_test(t, "token"+t1.Format("20060102150405"), "use stressdb1;", "direct", 0, 3)
	cmdResult, err := runRpcCommand_test(t, "token"+t1.Format("20060102150405"), "db.room1.find().limit(10).toArray()", "direct", 0, 3)
	if err != nil {
		t.Fatalf("Failed to run command: %v", err)
	}
	if cmdResult.Code != 0 {
		t.Fatalf("Failed to run x command: %v", cmdResult)
	}
}

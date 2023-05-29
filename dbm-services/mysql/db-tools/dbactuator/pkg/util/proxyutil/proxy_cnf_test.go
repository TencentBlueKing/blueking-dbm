package proxyutil

import (
	"encoding/json"
	"testing"
)

func TestNewProxyCnf(t *testing.T) {
	var c ProxyCnfObject
	proxyConfigJson := `{
		"mysql-proxy": 
		{
		"ignore-user": "MONITOR,proxy",
		"conn_log": "true",
		"keepalive": "true", 
		"daemon": "true",
		"interactive_timeout": "86400",
		"admin-username": "proxy"
		}
	}`
	if err := json.Unmarshal([]byte(proxyConfigJson), &c); err != nil {
		t.Fatalf("unmarshal failed %s", err.Error())
		return
	}
	nf, err := c.NewProxyCnfObject("proxy.cnf")
	if err != nil {
		t.Fatalf("NewProxyCnfObject failed %s", err.Error())
		return
	}
	nf.FileName = "proxy.cnf.10000"
	if err := nf.SafeSaveFile(true); err != nil {
		t.Fatalf("save file error %s", err.Error())
		return
	}
}

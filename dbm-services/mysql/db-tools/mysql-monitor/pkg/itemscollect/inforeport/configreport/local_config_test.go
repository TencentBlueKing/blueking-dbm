package configreport

import (
	"encoding/json"
	"strings"
	"testing"

	dbbackupConfig "dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/rotate"
	checksumConfig "dbm-services/mysql/db-tools/mysql-table-checksum/pkg/config"
)

func mustMask(t *testing.T, v interface{}) (interface{}, string) {
	t.Helper()
	payload, body, err := MaskedJSONPayload(v)
	if err != nil {
		t.Fatalf("MaskedJSONPayload: %v", err)
	}
	// 上报的 payload 与写入 local_config 的 JSON 必须一致
	b, _ := json.Marshal(payload)
	if string(b) != body {
		t.Fatalf("payload json != body\n%s\n%s", b, body)
	}
	return payload, body
}

func TestMaskedJSONPayloadGeneric(t *testing.T) {
	in := map[string]interface{}{
		"Password":   "p1",
		"ssh_pass":   "p2",
		"user":       "admin",
		"big":        int64(9007199254740993),
		"empty_pass": map[string]interface{}{"password": ""},
		"servers":    []interface{}{map[string]interface{}{"host": "1.1.1.1", "password": "p3"}},
	}
	_, body := mustMask(t, in)
	for _, s := range []string{"p1", "p2", "p3"} {
		if strings.Contains(body, `"`+s+`"`) {
			t.Errorf("password %s not masked: %s", s, body)
		}
	}
	for _, s := range []string{`"user":"admin"`, `"big":9007199254740993`, `"password":""`,
		`"Password":"******"`, `"ssh_pass":"******"`} {
		if !strings.Contains(body, s) {
			t.Errorf("expect %s in %s", s, body)
		}
	}
}

func TestMaskedJSONPayloadRealConfig(t *testing.T) {
	bk := &dbbackupConfig.BackupConfig{}
	bk.Public.MysqlPasswd = "bkpass"
	bk.BackupToRemote.SshPass = "sshpass"
	_, body := mustMask(t, bk)
	if strings.Contains(body, "bkpass") || strings.Contains(body, "sshpass\"") {
		t.Errorf("dbbackup not masked: %s", body)
	}

	rb := &rotate.Config{Servers: []*rotate.ServerObj{{Host: "1.1.1.1", Port: 3306, Password: "rbpass"}}}
	_, body = mustMask(t, rb)
	if strings.Contains(body, "rbpass") {
		t.Errorf("rotatebinlog not masked: %s", body)
	}

	ck := &checksumConfig.Config{Enable: true}
	ck.Password = "ckpass"
	ck.Slaves = []checksumConfig.Host{{Ip: "2.2.2.2", Password: "slavepass"}}
	_, body = mustMask(t, ck)
	if strings.Contains(body, "ckpass") || strings.Contains(body, "slavepass") {
		t.Errorf("checksum not masked: %s", body)
	}
}

func TestFlattenOneLevel(t *testing.T) {
	in := map[string]interface{}{
		"backup_client": map[string]interface{}{
			"bkbs": map[string]interface{}{"enable": true, "file_tag": "INCREMENT_BACKUP"},
			"ibs":  map[string]interface{}{"enable": false},
		},
		"crond": map[string]interface{}{
			"api_url":  "http://127.0.0.1:9999",
			"schedule": "*/5 * * * *",
		},
		"servers": nil,
		"flag":    true,
	}
	out := FlattenOneLevel(in).(map[string]interface{})

	// backup_client 的子项应被提升
	if _, ok := out["backup_client"]; ok {
		t.Error("backup_client should be flattened away")
	}
	bkbs, ok := out["backup_client.bkbs"].(map[string]interface{})
	if !ok {
		t.Fatal("backup_client.bkbs missing")
	}
	if bkbs["enable"] != true {
		t.Error("backup_client.bkbs.enable should be true")
	}
	if _, ok := out["backup_client.ibs"]; !ok {
		t.Error("backup_client.ibs missing")
	}

	// crond 的标量子项应被提升
	if _, ok := out["crond"]; ok {
		t.Error("crond should be flattened away")
	}
	if out["crond.api_url"] != "http://127.0.0.1:9999" {
		t.Errorf("crond.api_url = %v", out["crond.api_url"])
	}
	if out["crond.schedule"] != "*/5 * * * *" {
		t.Errorf("crond.schedule = %v", out["crond.schedule"])
	}

	// 非 map 值保持不变
	if out["servers"] != nil {
		t.Error("servers should be nil")
	}
	if out["flag"] != true {
		t.Error("flag should be true")
	}
}

func TestFlattenOneLevelNonMap(t *testing.T) {
	// 非 map 输入原样返回
	s := "hello"
	if FlattenOneLevel(s) != s {
		t.Error("string should pass through")
	}
	arr := []interface{}{1, 2}
	if FlattenOneLevel(arr) == nil {
		t.Error("slice should pass through")
	}
}

func TestModelLocalConfigTableName(t *testing.T) {
	m := ModelLocalConfig{}
	tn := m.TableName()
	if !strings.Contains(tn, "local_config") {
		t.Errorf("unexpected table name: %s", tn)
	}
}

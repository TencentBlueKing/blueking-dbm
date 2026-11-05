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

func TestAddRoleDataSchemaGrant(t *testing.T) {
	cases := map[string]string{
		"master":        "Master.DataSchemaGrant",
		"SLAVE":         "Slave.DataSchemaGrant",
		"SPIDER_MASTER": "Spider.DataSchemaGrant",
		"repeater":      "",
	}
	for role, wantKey := range cases {
		bk := &dbbackupConfig.BackupConfig{}
		bk.Public.MysqlRole = role
		bk.Public.DataSchemaGrant = "all"
		masked, _, err := MaskedJSONPayload(bk)
		if err != nil {
			t.Fatal(err)
		}
		m := FlattenOneLevel(masked).(map[string]interface{})
		addRoleDataSchemaGrant(m, role)

		if m["Public.DataSchemaGrant"] != "all" {
			t.Errorf("role %s: Public.DataSchemaGrant missing", role)
		}
		n := 0
		for k := range m {
			if strings.HasSuffix(k, ".DataSchemaGrant") && k != "Public.DataSchemaGrant" {
				n++
			}
		}
		if wantKey == "" {
			if n != 0 {
				t.Errorf("role %s: should not add role key", role)
			}
			continue
		}
		if m[wantKey] != "all" || n != 1 {
			t.Errorf("role %s: expect only %s=all, got %v", role, wantKey, m)
		}
	}
}

func TestCopyEnableBackupClient(t *testing.T) {
	bk := &dbbackupConfig.BackupConfig{}
	bk.BackupClient.EnableBackupClient = "auto"
	masked, _, err := MaskedJSONPayload(bk)
	if err != nil {
		t.Fatal(err)
	}
	payload := FlattenOneLevel(masked)
	copyKey(payload, "BackupClient.EnableBackupClient", "EnableBackupClient")
	m := payload.(map[string]interface{})
	if m["EnableBackupClient"] != "auto" || m["BackupClient.EnableBackupClient"] != "auto" {
		t.Errorf("dbbackup EnableBackupClient not copied: %v", m["EnableBackupClient"])
	}

	rb := &rotate.Config{}
	rb.Public.BackupEnable = "yes"
	masked, _, err = MaskedJSONPayload(rb)
	if err != nil {
		t.Fatal(err)
	}
	payload = FlattenOneLevel(masked)
	copyKey(payload, "public.backup_enable", "EnableBackupClient")
	m = payload.(map[string]interface{})
	if m["EnableBackupClient"] != "yes" || m["public.backup_enable"] != "yes" {
		t.Errorf("rotatebinlog EnableBackupClient not copied: %v", m["EnableBackupClient"])
	}

	// 源 key 不存在时不新增
	m = map[string]interface{}{"a": 1}
	copyKey(m, "missing", "EnableBackupClient")
	if _, ok := m["EnableBackupClient"]; ok {
		t.Error("should not add key when src missing")
	}
}

func TestModelLocalConfigTableName(t *testing.T) {
	m := ModelLocalConfig{}
	tn := m.TableName()
	if !strings.Contains(tn, "local_config") {
		t.Errorf("unexpected table name: %s", tn)
	}
}

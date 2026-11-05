package configreport

import (
	"testing"

	dbbackupConfig "dbm-services/mysql/db-tools/mysql-dbbackup/pkg/config"
	"dbm-services/mysql/db-tools/mysql-rotatebinlog/pkg/rotate"
)

func flatDbbackup(t *testing.T, bk *dbbackupConfig.BackupConfig) map[string]interface{} {
	t.Helper()
	masked, _, err := MaskedJSONPayload(bk)
	if err != nil {
		t.Fatal(err)
	}
	m := FlattenOneLevel(masked).(map[string]interface{})
	addRoleDataSchemaGrant(m, bk.Public.MysqlRole)
	copyKey(m, "BackupClient.EnableBackupClient", "EnableBackupClient")
	return m
}

func flatRotate(t *testing.T, rb *rotate.Config) map[string]interface{} {
	t.Helper()
	masked, _, err := MaskedJSONPayload(rb)
	if err != nil {
		t.Fatal(err)
	}
	m := FlattenOneLevel(masked).(map[string]interface{})
	copyKey(m, "public.backup_enable", "EnableBackupClient")
	return m
}

func TestBuildDbbackupOptions(t *testing.T) {
	bk := &dbbackupConfig.BackupConfig{}
	bk.Public.MysqlRole = "SLAVE"
	bk.Public.BackupType = "physical"
	bk.Public.DataSchemaGrant = "all"
	bk.Schedule.CronTime = "0 3 * * *"
	bk.BackupClient.EnableBackupClient = "auto"

	rb := &rotate.Config{}
	rb.Public.BackupEnable = "auto"

	// 两边 EnableBackupClient 相同，去重为一个值
	got := buildDbbackupOptions(flatDbbackup(t, bk), flatRotate(t, rb))
	want := map[string]string{
		"BackupType":            "physical",
		"CrontabTime":           "0 3 * * *",
		"Slave.DataSchemaGrant": "all",
		"EnableBackupClient":    "auto",
	}
	for k, v := range want {
		if got[k] != v {
			t.Errorf("%s = %v, want %s", k, got[k], v)
		}
	}
	for _, k := range []string{"Master.DataSchemaGrant", "Spider.DataSchemaGrant", "Readonly.DataSchemaGrant"} {
		if _, ok := got[k]; ok {
			t.Errorf("%s should not exist for slave", k)
		}
	}
	if len(got) != len(want) {
		t.Errorf("unexpected keys: %v", got)
	}

	// 两边不一致，去重后用 , 拼接，dbbackup 在前
	rb.Public.BackupEnable = "yes"
	got = buildDbbackupOptions(flatDbbackup(t, bk), flatRotate(t, rb))
	if got["EnableBackupClient"] != "auto,yes" {
		t.Errorf("EnableBackupClient = %v, want auto,yes", got["EnableBackupClient"])
	}

	// 没有 rotatebinlog 时只取 dbbackup
	got = buildDbbackupOptions(flatDbbackup(t, bk), nil)
	if got["EnableBackupClient"] != "auto" {
		t.Errorf("EnableBackupClient = %v, want auto", got["EnableBackupClient"])
	}

	// 一边为空字符串时不参与拼接
	bk.BackupClient.EnableBackupClient = ""
	got = buildDbbackupOptions(flatDbbackup(t, bk), flatRotate(t, rb))
	if got["EnableBackupClient"] != "yes" {
		t.Errorf("EnableBackupClient = %v, want yes", got["EnableBackupClient"])
	}
}

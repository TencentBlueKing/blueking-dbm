package config

import "testing"

func TestIsDtsMachineType(t *testing.T) {
	if !IsDtsMachineType("mysql_dts_master") || !IsDtsMachineType("mysql_dts_worker") {
		t.Fatal("dts machine_type should match")
	}
	if IsDtsMachineType("backend") {
		t.Fatal("backend is not dts")
	}
}

func TestInjectMonitorDbUpItem_SkipDts(t *testing.T) {
	enable := true
	ItemsConfig = []*MonitorItem{{Name: "dts-heartbeat", Enable: &enable}}
	MonitorConfig = &Config{MachineType: "mysql_dts_worker"}
	InjectMonitorDbUpItem()
	for _, item := range ItemsConfig {
		if item.Name == "db-up" {
			t.Fatal("dts should not inject db-up")
		}
	}
}

func TestInjectMonitorDbUpItem_BackendStillInjects(t *testing.T) {
	enable := true
	ItemsConfig = []*MonitorItem{{Name: "engine", Enable: &enable}}
	MonitorConfig = &Config{MachineType: "backend"}
	InjectMonitorDbUpItem()
	found := false
	for _, item := range ItemsConfig {
		if item.Name == "db-up" {
			found = true
		}
	}
	if !found {
		t.Fatal("backend should still inject db-up")
	}
}

package cmd

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"testing"

	dbmonconfig "dbm-services/mongodb/db-tools/dbmon/config"

	"gopkg.in/yaml.v3"
)

func TestConfigSetConcurrentWritesE2E(t *testing.T) {
	t.Parallel()

	tmpDir := t.TempDir()
	binPath := filepath.Join(tmpDir, "bk-dbmon")
	if out, err := exec.Command("go", "build", "-o", binPath, "..").CombinedOutput(); err != nil {
		t.Fatalf("build bk-dbmon failed: %v\n%s", err, out)
	}

	ports := []int{27017, 27018, 27019, 27020, 27021, 27022, 27023, 27024}
	configFile := filepath.Join(tmpDir, "dbmon-config.yaml")
	clusterConfigFile := filepath.Join(tmpDir, "cluster-config.yaml")
	if err := os.WriteFile(configFile, []byte(renderDbmonConfigForPorts(ports)), 0644); err != nil {
		t.Fatalf("write dbmon config failed: %v", err)
	}

	errCh := make(chan error, len(ports))
	for _, port := range ports {
		port := port
		go func() {
			cmd := exec.Command(
				binPath,
				"--config", configFile,
				"--cluster-config", clusterConfigFile,
				"--stdout",
				"config", "set",
				"--port", fmt.Sprintf("%d", port),
				"--segment", dbmonconfig.SegmentBackup,
				"--key", dbmonconfig.KeyEnable,
				"--value", dbmonconfig.ValueFalse,
			)
			if out, err := cmd.CombinedOutput(); err != nil {
				errCh <- fmt.Errorf("config set port %d failed: %w\n%s", port, err, out)
				return
			}
			errCh <- nil
		}()
	}
	for range ports {
		if err := <-errCh; err != nil {
			t.Fatal(err)
		}
	}

	data, err := os.ReadFile(clusterConfigFile)
	if err != nil {
		t.Fatalf("read cluster config failed: %v", err)
	}
	var clusterConfig dbmonconfig.ClusterConfigConf
	if err := yaml.Unmarshal(data, &clusterConfig); err != nil {
		t.Fatalf("unmarshal cluster config failed: %v\n%s", err, data)
	}

	got := make(map[string]string, len(clusterConfig.InstanceConfig))
	for _, item := range clusterConfig.InstanceConfig {
		if item.Segment == dbmonconfig.SegmentBackup && item.Key == dbmonconfig.KeyEnable {
			got[item.Instance] = item.Value
		}
	}
	for _, port := range ports {
		instance := fmt.Sprintf("127.0.0.1:%d", port)
		if got[instance] != dbmonconfig.ValueFalse {
			t.Fatalf("missing config update for %s, got instance config: %#v", instance, got)
		}
	}
}

func renderDbmonConfigForPorts(ports []int) string {
	servers := ""
	for _, port := range ports {
		servers += fmt.Sprintf(`  - ip: 127.0.0.1
    port: %d
    bk_cloud_id: 0
    bk_biz_id: 1
    app: test
    app_name: test
    cluster_domain: test.mongodb.db
    cluster_id: 1
    cluster_name: test
    cluster_type: MongoReplicaSet
    role_type: mongod
    meta_role: m1
    set_name: test-rs
`, port)
	}
	return `report_save_dir: /tmp
report_left_day: 1
backup_client_storage_type: cos
http_address: 127.0.0.1:0
bkmonitorbeat:
  agent_address: ""
  beat_path: ""
  event_config:
    data_id: 0
    token: ""
  metric_config:
    data_id: 0
    token: ""
servers:
` + servers
}

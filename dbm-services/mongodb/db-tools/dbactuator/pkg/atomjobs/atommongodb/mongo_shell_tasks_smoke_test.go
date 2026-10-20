package atommongodb

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"dbm-services/mongodb/db-tools/dbactuator/pkg/consts"
	"dbm-services/mongodb/db-tools/dbactuator/pkg/jobruntime"
)

// TestSmokeActuatorTasksUseMongosh verifies actuator atom jobs on an installation
// without the legacy mongo shell. The fake 8.0 installation intentionally has no
// mongo binary, so an atom still wired to mongo cannot pass.
func TestSmokeActuatorTasksUseMongosh(t *testing.T) {
	binDir := makeFakeMongo80Install(t)
	t.Setenv("MONGO_BIN_DIR", binDir)
	t.Setenv("MONGO_DATA_DIR", t.TempDir())
	t.Setenv("MONGO_BACKUP_DIR", t.TempDir())

	commonAuth := map[string]any{
		"ip": "127.0.0.1", "port": 27017,
		"adminUsername": "admin", "adminPassword": "secret",
	}
	tests := []struct {
		name string
		run  func(*testing.T) (string, error)
	}{
		{
			name: "add_user",
			run: func(t *testing.T) (string, error) {
				p := cloneParams(commonAuth)
				p["instanceType"], p["username"], p["password"] = "mongos", "app", "secret"
				job := &AddUser{}
				err := job.Init(smokeRuntime(t, p, "add_user"))
				return job.Mongo, err
			},
		},
		{
			name: "delete_user",
			run: func(t *testing.T) (string, error) {
				p := cloneParams(commonAuth)
				p["instanceType"], p["username"] = "mongos", "app"
				job := &DelUser{}
				err := job.Init(smokeRuntime(t, p, "delete_user"))
				return job.Mongo, err
			},
		},
		{
			name: "init_replicaset",
			run: func(t *testing.T) (string, error) {
				p := map[string]any{
					"ip": "127.0.0.1", "port": 27017, "setId": "rs0",
					"ips":      []string{"127.0.0.1:27017"},
					"priority": map[string]int{"127.0.0.1:27017": 1},
					"hidden":   map[string]bool{"127.0.0.1:27017": false},
				}
				job := &InitiateReplicaset{}
				err := job.Init(smokeRuntime(t, p, "init_replicaset"))
				return job.Mongo, err
			},
		},
		{
			name: "replicaset_stepdown",
			run: func(t *testing.T) (string, error) {
				p := cloneParams(commonAuth)
				p["targetIP"] = "127.0.0.2"
				job := &StepDown{}
				err := job.Init(smokeRuntime(t, p, "replicaset_stepdown"))
				return job.Mongo, err
			},
		},
		{
			name: "mongo_restart",
			run: func(t *testing.T) (string, error) {
				p := map[string]any{"ip": "127.0.0.1", "port": 27017, "instanceType": "mongod"}
				job := &MongoRestart{}
				err := job.Init(smokeRuntime(t, p, "mongo_restart"))
				return job.Mongo, err
			},
		},
		{
			name: "mongod_replace",
			run: func(t *testing.T) (string, error) {
				job := &MongoDReplace{}
				err := job.Init(smokeRuntime(t, commonAuth, "mongod_replace"))
				return job.Mongo, err
			},
		},
		{
			name: "mongod_node_hidden",
			run: func(t *testing.T) (string, error) {
				p := cloneParams(commonAuth)
				p["hiddenip"], p["hiddenport"] = "127.0.0.2", 27017
				job := &NodeHidden{}
				err := job.Init(smokeRuntime(t, p, "mongod_node_hidden"))
				return job.Mongo, err
			},
		},
		{
			name: "add_shard_to_cluster",
			run: func(t *testing.T) (string, error) {
				p := cloneParams(commonAuth)
				p["shards"] = map[string]string{"rs0": "127.0.0.1:27017"}
				job := &AddShardToCluster{}
				err := job.Init(smokeRuntime(t, p, "add_shard_to_cluster"))
				return job.Mongo, err
			},
		},
		{
			name: "remove_shard_from_cluster",
			run: func(t *testing.T) (string, error) {
				p := cloneParams(commonAuth)
				p["shards"], p["dbVersion"] = []string{"rs0"}, "8.0"
				job := &RemoveShardFromCluster{}
				err := job.Init(smokeRuntime(t, p, "remove_shard_from_cluster"))
				return job.Mongo, err
			},
		},
		{
			name: "cluster_balancer",
			run: func(t *testing.T) (string, error) {
				job := &Balancer{}
				err := job.Init(smokeRuntime(t, commonAuth, "cluster_balancer"))
				return job.Mongo, err
			},
		},
		{
			name: "balance_config_sessions",
			run: func(t *testing.T) (string, error) {
				p := cloneParams(commonAuth)
				p["dbVersion"] = "6.0.4"
				job := &BalanceConfigSessions{}
				err := job.Init(smokeRuntime(t, p, "balance_config_sessions"))
				return job.Mongo, err
			},
		},
		{
			name: "mongo_set_fcv",
			run: func(t *testing.T) (string, error) {
				p := cloneParams(commonAuth)
				p["old_fcv"], p["new_fcv"], p["instanceType"] = "7.0", "8.0", "mongos"
				job := &MongoSetFCV{}
				err := job.Init(smokeRuntime(t, p, "mongo_set_fcv"))
				return job.Mongo, err
			},
		},
		{
			name: "mongo_upgrade_rs_protocol",
			run: func(t *testing.T) (string, error) {
				p := cloneParams(commonAuth)
				p["instanceType"] = "mongos"
				job := &MongoUpgradeRsProtocol{}
				err := job.Init(smokeRuntime(t, p, "mongo_upgrade_rs_protocol"))
				return job.Mongo, err
			},
		},
		{
			name: "mongo_deferred_deinstall",
			run: func(t *testing.T) (string, error) {
				p := map[string]any{
					"ip": "127.0.0.1", "port": 27017,
					"nodeInfo": []string{"127.0.0.1"}, "instanceType": "mongos",
				}
				job := &DeferredDeInstall{}
				err := job.Init(smokeRuntime(t, p, "mongo_deferred_deinstall"))
				return job.Mongo, err
			},
		},
		{
			name: "mongo_execute_script",
			run: func(t *testing.T) (string, error) {
				job := &ExecScript{
					runtime:    smokeRuntime(t, map[string]any{}, "mongo_execute_script"),
					BinDir:     binDir,
					ConfParams: &ExecScriptConfParams{DbVersion: "8.0"},
				}
				err := job.resolveMongoShell()
				return job.Mongo, err
			},
		},
	}

	want := filepath.Join(binDir, "mongodb", "bin", "mongosh")
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, err := tc.run(t)
			if err != nil {
				t.Fatalf("initialize atom job: %v", err)
			}
			if got != want {
				t.Fatalf("selected shell=%q, want %q", got, want)
			}
		})
	}
}

func TestCleanupAndStartInitDoNotRequireMongoBinaries(t *testing.T) {
	t.Setenv("MONGO_BIN_DIR", t.TempDir())
	t.Setenv("MONGO_DATA_DIR", t.TempDir())
	t.Setenv("MONGO_BACKUP_DIR", t.TempDir())

	deinstallPayload := map[string]any{
		"ip": "127.0.0.1", "port": 27017,
		"nodeInfo": []string{"127.0.0.1"}, "instanceType": "mongos",
	}
	if err := (&DeInstall{}).Init(smokeRuntime(t, deinstallPayload, "mongo_deinstall")); err != nil {
		t.Fatalf("deinstall init should not require binaries: %v", err)
	}
	startPayload := map[string]any{"ip": "127.0.0.1", "port": 27017, "instanceType": "mongod"}
	if err := (&MongoStartProcess{}).Init(smokeRuntime(t, startPayload, "mongo_start_process")); err != nil {
		t.Fatalf("start init should not resolve a shell: %v", err)
	}
}

// TestSmokeInstanceOpUsesMongosh covers the two instance-op upgrade paths that
// query buildInfo through a shell. The fake install contains no mongo binary.
func TestSmokeInstanceOpUsesMongosh(t *testing.T) {
	binDir := makeFakeMongo80Install(t)
	t.Setenv("MONGO_BIN_DIR", binDir)
	job := &instOpJob{
		ConfParams: &instOpParams{
			IP: "127.0.0.1", Port: 27017, CurrentVersion: "8.0",
			InstanceType: "mongos", AdminUsername: "admin", AdminPassword: "secret",
		},
	}
	job.runtime = smokeRuntime(t, map[string]any{}, "mongodb_instance_op")

	version, err := job.getRunningVersionMajorMinor()
	if err != nil {
		t.Fatalf("getRunningVersionMajorMinor: %v", err)
	}
	if version != "8.0" {
		t.Fatalf("running version=%q, want 8.0", version)
	}
	if err := job.doPrecheckUpgrade(); err != nil {
		t.Fatalf("doPrecheckUpgrade: %v", err)
	}
}

func smokeRuntime(t *testing.T, payload map[string]any, atom string) *jobruntime.JobGenericRuntime {
	t.Helper()
	data, err := json.Marshal(payload)
	if err != nil {
		t.Fatalf("marshal payload: %v", err)
	}
	rt, err := jobruntime.NewJobGenericRuntime(
		"smoke-uid", "smoke-root", "smoke-node", "smoke-version",
		string(data), consts.PayloadFormatRaw, atom, t.TempDir(),
	)
	if err != nil {
		t.Fatalf("new runtime: %v", err)
	}
	return rt
}

func cloneParams(src map[string]any) map[string]any {
	dst := make(map[string]any, len(src))
	for key, value := range src {
		dst[key] = value
	}
	return dst
}

func makeFakeMongo80Install(t *testing.T) string {
	t.Helper()
	binDir := t.TempDir()
	mongoBinDir := filepath.Join(binDir, "mongodb", "bin")
	if err := os.MkdirAll(mongoBinDir, 0o755); err != nil {
		t.Fatalf("mkdir fake mongo bin: %v", err)
	}
	mongod := "#!/bin/sh\n" +
		"if [ \"$1\" = \"-version\" ]; then echo 'db version v8.0.32'; exit 0; fi\n" +
		"exit 1\n"
	mongosh := "#!/bin/sh\n" +
		"case \"$*\" in\n" +
		"  *buildInfo*) echo '8.0.32' ;;\n" +
		"  *) echo '127.0.0.1:27017' ;;\n" +
		"esac\n"
	for name, body := range map[string]string{"mongod": mongod, "mongosh": mongosh} {
		if err := os.WriteFile(filepath.Join(mongoBinDir, name), []byte(body), 0o755); err != nil {
			t.Fatalf("write fake %s: %v", name, err)
		}
	}
	return binDir
}

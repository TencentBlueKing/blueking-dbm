package atomredis

import (
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
	"time"

	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
)

// writeInstanceData 在实例数据目录里造出一份"重启会被加载"的现场
func writeInstanceData(t *testing.T, dataDir string, names ...string) {
	t.Helper()
	if err := os.MkdirAll(dataDir, 0755); err != nil {
		t.Fatalf("mkdir %s failed:%v", dataDir, err)
	}
	for _, name := range names {
		path := filepath.Join(dataDir, name)
		if name == "appendonlydir" {
			if err := os.MkdirAll(path, 0755); err != nil {
				t.Fatalf("mkdir %s failed:%v", path, err)
			}
			if err := os.WriteFile(filepath.Join(path, "appendonly.aof.1.incr.aof"), []byte("x"), 0644); err != nil {
				t.Fatalf("write aof failed:%v", err)
			}
			continue
		}
		if err := os.WriteFile(path, []byte(name), 0644); err != nil {
			t.Fatalf("write %s failed:%v", path, err)
		}
	}
}

// setupDiscardJob 造一个"已判定要空载起进程"的 job, 返回实例数据目录
func setupDiscardJob(t *testing.T, port int, confBody string, dataFiles ...string) (*RedisVersionUpdate, string) {
	t.Helper()
	confFile := setupInstanceConf(t, port, "placeholder\n")
	instDir := filepath.Dir(confFile)
	dataDir := filepath.Join(instDir, "data")
	conf := "port 30000\ndir " + dataDir + "\n" + confBody
	if err := os.WriteFile(confFile, []byte(conf), 0644); err != nil {
		t.Fatalf("rewrite conf failed:%v", err)
	}
	writeInstanceData(t, dataDir, dataFiles...)

	job := buildRegenJob("1.1.1.1", []int{port})
	job.discardPorts[port] = true
	return job, dataDir
}

func TestMoveAsideLocalDataAndCleanup(t *testing.T) {
	job, dataDir := setupDiscardJob(t, 30000, "appendonly yes\n", "dump.rdb", "appendonly.aof", "nodes.conf")

	if err := job.moveAsideLocalData(30000); err != nil {
		t.Fatalf("moveAsideLocalData err:%v", err)
	}
	for _, name := range []string{"dump.rdb", "appendonly.aof"} {
		if _, err := os.Stat(filepath.Join(dataDir, name)); !os.IsNotExist(err) {
			t.Errorf("%s should have been moved aside", name)
		}
	}
	// nodes.conf 是 cluster 的节点身份, 挪走等于丢掉这个节点
	if _, err := os.Stat(filepath.Join(dataDir, "nodes.conf")); err != nil {
		t.Errorf("nodes.conf must stay in place:%v", err)
	}
	if got := len(job.discardedFiles[30000]); got != 2 {
		t.Fatalf("moved %d files, want 2:%+v", got, job.discardedFiles[30000])
	}

	job.cleanupDiscardedLocalData(30000)
	entries, err := os.ReadDir(dataDir)
	if err != nil {
		t.Fatalf("read data dir failed:%v", err)
	}
	for _, entry := range entries {
		if strings.Contains(entry.Name(), "upgrade_bak") {
			t.Errorf("moved aside file %s not cleaned up", entry.Name())
		}
	}
	if _, ok := job.discardedFiles[30000]; ok {
		t.Error("discarded files entry should be dropped after cleanup")
	}
}

func TestRestoreDiscardedLocalData(t *testing.T) {
	// 新版本起不来时要退回"带着原数据重启"的老行为, 数据必须逐字节回到原处
	job, dataDir := setupDiscardJob(t, 30000, "", "dump.rdb")

	if err := job.moveAsideLocalData(30000); err != nil {
		t.Fatalf("moveAsideLocalData err:%v", err)
	}
	// 上一次启动尝试写出了一份新的同名文件, 回滚时要被原来那份覆盖
	if err := os.WriteFile(filepath.Join(dataDir, "dump.rdb"), []byte("half written"), 0644); err != nil {
		t.Fatalf("write failed:%v", err)
	}
	if err := job.restoreDiscardedLocalData(30000); err != nil {
		t.Fatalf("restoreDiscardedLocalData err:%v", err)
	}
	got, err := os.ReadFile(filepath.Join(dataDir, "dump.rdb"))
	if err != nil {
		t.Fatalf("read restored file failed:%v", err)
	}
	if string(got) != "dump.rdb" {
		t.Errorf("restored content = %q, want the original one", got)
	}
	if len(job.discardedFiles[30000]) != 0 {
		t.Error("discarded files entry should be dropped after restore")
	}
}

func TestMoveAsideLocalDataNoopWhenNotDiscarding(t *testing.T) {
	job, dataDir := setupDiscardJob(t, 30000, "", "dump.rdb")
	job.discardPorts = map[int]bool{}

	if err := job.moveAsideLocalData(30000); err != nil {
		t.Fatalf("moveAsideLocalData err:%v", err)
	}
	if _, err := os.Stat(filepath.Join(dataDir, "dump.rdb")); err != nil {
		t.Errorf("data must stay untouched when not discarding:%v", err)
	}
}

func TestLocalDataFileNamesCoversBothConfSpellings(t *testing.T) {
	// 跨大版本升级: 旧配置是 redis 6 的单文件 AOF, 新配置是 redis 7 的 appenddirname 目录.
	// 只按其中一份的名字挪, 另一套名字的数据会被新进程原样加载起来
	confFile := setupInstanceConf(t, 30000, "placeholder\n")
	instDir := filepath.Dir(confFile)
	dataDir := filepath.Join(instDir, "data")
	newConf := "port 30000\ndir " + dataDir + "\nappenddirname \"appendonlydir\"\n"
	if err := os.WriteFile(confFile, []byte(newConf), 0644); err != nil {
		t.Fatalf("write conf failed:%v", err)
	}
	backupFile := confFile + ".bak"
	oldConf := "port 30000\ndir " + dataDir + "\nappendfilename \"appendonly.aof\"\ndbfilename dump-30000.rdb\n"
	if err := os.WriteFile(backupFile, []byte(oldConf), 0644); err != nil {
		t.Fatalf("write backup conf failed:%v", err)
	}

	job := buildRegenJob("1.1.1.1", []int{30000})
	job.confBackupFiles[30000] = backupFile

	gotDir, names, err := job.localDataFileNames(30000)
	if err != nil {
		t.Fatalf("localDataFileNames err:%v", err)
	}
	if gotDir != dataDir {
		t.Errorf("dataDir = %q, want %q", gotDir, dataDir)
	}
	want := map[string]bool{
		"dump.rdb": true, "dump-30000.rdb": true, "appendonly.aof": true, "appendonlydir": true,
	}
	for _, name := range names {
		if !want[name] {
			t.Errorf("unexpected file name %q", name)
		}
		delete(want, name)
	}
	if len(want) > 0 {
		t.Errorf("missing file names %v, got %v", want, names)
	}
}

func TestWhyKeepLocalDataGates(t *testing.T) {
	slaveSnap := replSnapshot{
		addr: "1.1.1.1:30000", role: consts.RedisSlaveRole, masterHost: "1.1.1.2", masterPort: "30000",
	}
	masterSnap := replSnapshot{addr: "1.1.1.1:30000", role: consts.RedisMasterRole}

	cases := []struct {
		name        string
		clusterType string
		snap        replSnapshot
		wantReason  string
	}{
		{
			// TendisSSD 的从库只能靠全备重建, 数据挪走就回不来了
			name:        "tendisssd refused",
			clusterType: consts.TendisTypeTwemproxyTendisSSDInstance,
			snap:        slaveSnap,
			wantReason:  "not cache",
		},
		{
			name:        "tendisplus refused",
			clusterType: consts.TendisTypePredixyTendisplusCluster,
			snap:        slaveSnap,
			wantReason:  "not cache",
		},
		{
			// 没有主库可同步时把数据挪走就是丢数据
			name:        "master instance refused",
			clusterType: consts.TendisTypeTwemproxyRedisInstance,
			snap:        masterSnap,
			wantReason:  "not expected to replicate",
		},
		{
			name:        "no snapshot refused",
			clusterType: consts.TendisTypeTwemproxyRedisInstance,
			wantReason:  "not expected to replicate",
		},
		{
			name:        "stopped cache slave trusts cluster_type",
			clusterType: consts.TendisTypeTwemproxyRedisInstance,
			snap:        slaveSnap,
			wantReason:  "get password from conf file",
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			job := buildRegenJob("1.1.1.1", []int{30000})
			job.params.ClusterType = tc.clusterType
			job.replSnapshots[30000] = tc.snap

			reason := job.whyKeepLocalData(30000, job.replExpectation(30000))
			if !strings.Contains(reason, tc.wantReason) {
				t.Errorf("reason = %q, want it to contain %q", reason, tc.wantReason)
			}
		})
	}
}

func TestRestoreClusterFailoverPermissionWithoutMemoryFlags(t *testing.T) {
	job := buildRegenJob("1.1.1.1", []int{30000})
	job.params.ClusterType = consts.TendisTypeTwemproxyRedisInstance
	if err := job.restoreClusterFailoverPermission(30000); err != nil {
		t.Fatalf("non-cluster should no-op:%v", err)
	}

	// cluster 且没有 client: 即使 discardPorts / confBackupFiles 都是空的, 也不能短路成成功.
	// 重试时内存旗标就是空的, 必须去读运行态, 没 client 就该失败.
	job.params.ClusterType = consts.TendisTypePredixyRedisCluster
	job.discardPorts = map[int]bool{}
	job.confBackupFiles = map[int]string{}
	err := job.restoreClusterFailoverPermission(30000)
	if err == nil {
		t.Fatal("cluster with no client should fail, not be skipped by empty discardPorts")
	}
	if !strings.Contains(err.Error(), "no client") {
		t.Errorf("err = %v, want it to contain no client", err)
	}
}

func TestWhyKeepLocalDataRuntimeTendisplus(t *testing.T) {
	fake := newFakeRedis(t, "xxxxpasswd")
	fake.info = "redis_version:2.8.3-rocksdb-v5.13.4\r\n"
	host, portStr := fake.hostPort()
	port, err := strconv.Atoi(portStr)
	if err != nil {
		t.Fatal(err)
	}
	job := buildRegenJob(host, []int{port})
	job.params.ClusterType = consts.TendisTypeTwemproxyRedisInstance
	cli, err := myredis.NewRedisClient(fake.addr(), "xxxxpasswd", 0, consts.TendisTypeRedisInstance, 2*time.Second)
	if err != nil {
		t.Fatalf("connect fake redis:%v", err)
	}
	t.Cleanup(func() { cli.Close() })
	job.AddrMapCli = map[string]*myredis.RedisClient{fmt.Sprintf("%s:%d", host, port): cli}
	job.replSnapshots[port] = replSnapshot{
		addr: fmt.Sprintf("%s:%d", host, port), role: consts.RedisSlaveRole,
		masterHost: "1.1.1.2", masterPort: "30000",
	}
	reason := job.whyKeepLocalData(port, job.replExpectation(port))
	if !strings.Contains(reason, "not cache") {
		t.Errorf("reason = %q, want it to contain not cache", reason)
	}
}

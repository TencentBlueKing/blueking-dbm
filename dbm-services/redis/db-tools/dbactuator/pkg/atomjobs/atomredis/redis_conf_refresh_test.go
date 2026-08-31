package atomredis

import (
	"encoding/json"
	"errors"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/mylog"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
)

func newRefreshJob(ip string, ports []int, mode string) *RedisConfRefresh {
	testLogger := logger.New(io.Discard, false, logger.InfoLevel)
	mylog.SetDefaultLogger(testLogger)
	return &RedisConfRefresh{
		runtime:          &jobruntime.JobGenericRuntime{Logger: testLogger},
		params:           RedisConfRefreshParams{IP: ip, Ports: ports, Role: consts.MetaRoleRedisSlave, ApplyMode: mode},
		addrMapCli:       map[string]*myredis.RedisClient{},
		replSnapshots:    map[int]replSnapshot{},
		masterAuthFollow: map[int]bool{},
		localPkgBaseName: "redis-6.2.7",
		instCount:        uint64(len(ports)),
	}
}

func TestRedisConfRefreshInit(t *testing.T) {
	item := RedisConfRenderItem{ConfConfigs: map[string]string{"port": "{{port}}"}}
	cases := []struct {
		name    string
		payload RedisConfRefreshParams
		wantErr string
	}{
		{
			name: "ok",
			payload: RedisConfRefreshParams{
				IP: "1.1.1.1", Ports: []int{30000}, Role: consts.MetaRoleRedisSlave,
				ClusterType:     consts.TendisTypeTwemproxyRedisInstance,
				ApplyMode:       ApplyModeConfFile,
				PortConfConfigs: map[string]RedisConfRenderItem{"30000": item},
			},
		},
		{
			name: "bad apply_mode",
			payload: RedisConfRefreshParams{
				IP: "1.1.1.1", Ports: []int{30000}, Role: consts.MetaRoleRedisSlave,
				ClusterType:     consts.TendisTypeTwemproxyRedisInstance,
				ApplyMode:       "nope",
				PortConfConfigs: map[string]RedisConfRenderItem{"30000": item},
			},
			wantErr: "ApplyMode",
		},
		{
			name: "missing port conf",
			payload: RedisConfRefreshParams{
				IP: "1.1.1.1", Ports: []int{30000, 30001}, Role: consts.MetaRoleRedisSlave,
				ClusterType:     consts.TendisTypeTwemproxyRedisInstance,
				ApplyMode:       ApplyModeRestart,
				PortConfConfigs: map[string]RedisConfRenderItem{"30000": item},
			},
			wantErr: "missing from port_conf_configs",
		},
		{
			name: "empty conf_configs",
			payload: RedisConfRefreshParams{
				IP: "1.1.1.1", Ports: []int{30000}, Role: consts.MetaRoleRedisSlave,
				ClusterType:     consts.TendisTypeTwemproxyRedisInstance,
				ApplyMode:       ApplyModeConfFile,
				PortConfConfigs: map[string]RedisConfRenderItem{"30000": {ConfConfigs: map[string]string{}}},
			},
			wantErr: "missing from port_conf_configs",
		},
		{
			name: "bad role",
			payload: RedisConfRefreshParams{
				IP: "1.1.1.1", Ports: []int{30000}, Role: "predixy",
				ClusterType:     consts.TendisTypeTwemproxyRedisInstance,
				ApplyMode:       ApplyModeConfFile,
				PortConfConfigs: map[string]RedisConfRenderItem{"30000": item},
			},
			wantErr: "not support",
		},
		{
			name: "password change on config_set",
			payload: RedisConfRefreshParams{
				IP: "1.1.1.1", Ports: []int{30000}, Role: consts.MetaRoleRedisSlave,
				ClusterType:         consts.TendisTypeTwemproxyRedisInstance,
				ApplyMode:           ApplyModeConfigSet,
				PortConfConfigs:     map[string]RedisConfRenderItem{"30000": item},
				PortTargetPasswords: map[string]string{"30000": "newpasswd"},
			},
		},
		{
			// 只写文件不碰运行态: 文件是新密码而进程还是旧的, dbmon / proxy 全都连不上
			name: "password change rejected on conf_file",
			payload: RedisConfRefreshParams{
				IP: "1.1.1.1", Ports: []int{30000}, Role: consts.MetaRoleRedisSlave,
				ClusterType:         consts.TendisTypeTwemproxyRedisInstance,
				ApplyMode:           ApplyModeConfFile,
				PortConfConfigs:     map[string]RedisConfRenderItem{"30000": item},
				PortTargetPasswords: map[string]string{"30000": "newpasswd"},
			},
			wantErr: "port_target_passwords requires apply_mode",
		},
		{
			// restart 也支持: masterauth 由探测结论随渲染结果一起落盘, 停机用改写前的旧密码
			name: "password change on restart",
			payload: RedisConfRefreshParams{
				IP: "1.1.1.1", Ports: []int{30000}, Role: consts.MetaRoleRedisSlave,
				ClusterType:         consts.TendisTypeTwemproxyRedisInstance,
				ApplyMode:           ApplyModeRestart,
				PortConfConfigs:     map[string]RedisConfRenderItem{"30000": item},
				PortTargetPasswords: map[string]string{"30000": "newpasswd"},
			},
		},
		{
			// 空串是合法目标(改成无密码), 不能被当成"没下发"而放过 apply_mode 检查
			name: "empty target password is a real target",
			payload: RedisConfRefreshParams{
				IP: "1.1.1.1", Ports: []int{30000}, Role: consts.MetaRoleRedisSlave,
				ClusterType:         consts.TendisTypeTwemproxyRedisInstance,
				ApplyMode:           ApplyModeConfFile,
				PortConfConfigs:     map[string]RedisConfRenderItem{"30000": item},
				PortTargetPasswords: map[string]string{"30000": ""},
			},
			wantErr: "port_target_passwords requires apply_mode",
		},
		{
			name: "password for a port not being refreshed",
			payload: RedisConfRefreshParams{
				IP: "1.1.1.1", Ports: []int{30000}, Role: consts.MetaRoleRedisSlave,
				ClusterType:         consts.TendisTypeTwemproxyRedisInstance,
				ApplyMode:           ApplyModeConfigSet,
				PortConfConfigs:     map[string]RedisConfRenderItem{"30000": item},
				PortTargetPasswords: map[string]string{"30001": "newpasswd"},
			},
			wantErr: "not in ports",
		},
		{
			name: "missing cluster_type",
			payload: RedisConfRefreshParams{
				IP: "1.1.1.1", Ports: []int{30000}, Role: consts.MetaRoleRedisSlave,
				ApplyMode:       ApplyModeConfFile,
				PortConfConfigs: map[string]RedisConfRenderItem{"30000": item},
			},
			wantErr: "ClusterType",
		},
		{
			name: "unknown cluster_type",
			payload: RedisConfRefreshParams{
				IP: "1.1.1.1", Ports: []int{30000}, Role: consts.MetaRoleRedisSlave,
				ClusterType:     "NotARedisType",
				ApplyMode:       ApplyModeConfFile,
				PortConfConfigs: map[string]RedisConfRenderItem{"30000": item},
			},
			wantErr: "unknown cluster_type",
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			raw, err := json.Marshal(tc.payload)
			if err != nil {
				t.Fatal(err)
			}
			job := NewRedisConfRefresh().(*RedisConfRefresh)
			job.runtime = &jobruntime.JobGenericRuntime{
				Logger:         logger.New(io.Discard, false, logger.InfoLevel),
				PayloadDecoded: string(raw),
			}
			err = job.Init(job.runtime)
			if tc.wantErr == "" {
				if err != nil {
					t.Fatalf("unexpected err:%v", err)
				}
				return
			}
			if err == nil {
				t.Fatalf("expected error containing %q", tc.wantErr)
			}
			if !strings.Contains(err.Error(), tc.wantErr) {
				t.Errorf("err=%v, want it to contain %q", err, tc.wantErr)
			}
		})
	}
}

func TestRedisConfRefreshRegenRequest(t *testing.T) {
	job := newRefreshJob("1.1.1.1", []int{30000}, ApplyModeRestart)
	job.params.ClusterType = consts.TendisTypeTwemproxyRedisInstance
	job.replSnapshots[30000] = replSnapshot{
		addr: "1.1.1.1:30000", role: consts.RedisSlaveRole, masterHost: "1.1.1.2", masterPort: "30000",
	}

	req := job.regenRequest(30000)
	if req.PkgBaseName != "redis-6.2.7" {
		t.Errorf("PkgBaseName=%q, want redis-6.2.7 (local symlink, not a media pkg)", req.PkgBaseName)
	}
	if req.DiscardLocalData {
		t.Error("refresh job must not discard local data")
	}
	if req.Expect.wanted {
		t.Error("refresh job must not override topology")
	}
	if req.Expect.masterAddr() != "1.1.1.2:30000" {
		t.Errorf("Expect.master=%q, want snapshot", req.Expect.masterAddr())
	}
	if req.InstCount != 1 {
		t.Errorf("InstCount=%d", req.InstCount)
	}
}

func TestRedisConfRefreshRegenRequestTargetPassword(t *testing.T) {
	job := newRefreshJob("1.1.1.1", []int{30000, 30001}, ApplyModeConfigSet)
	job.params.PortTargetPasswords = map[string]string{"30000": "newpasswd", "30001": ""}

	req := job.regenRequest(30000)
	if req.TargetPassword == nil || *req.TargetPassword != "newpasswd" {
		t.Errorf("TargetPassword=%v, want newpasswd", req.TargetPassword)
	}
	// 空串是"改成无密码", 不是"没下发": 用指针才区分得开
	req = job.regenRequest(30001)
	if req.TargetPassword == nil || *req.TargetPassword != "" {
		t.Errorf("TargetPassword=%v, want an empty target", req.TargetPassword)
	}

	job.params.PortTargetPasswords = nil
	if req = job.regenRequest(30000); req.TargetPassword != nil {
		t.Errorf("TargetPassword=%v, want nil when nothing is delivered", req.TargetPassword)
	}
}

// TestRedisConfRefreshBuildPortPlanChangesPassword 走完整的渲染+校验, 确认改密码这条路
// 在动运行态之前就是通的: requirepass 换成目标值.
//
// config_set 模式不写这份渲染结果, 但它仍是 applyConfigSet 的比对基准, 必须先过自己的校验
func TestRedisConfRefreshBuildPortPlanChangesPassword(t *testing.T) {
	confFile := setupInstanceConf(t, 30000, "placeholder\n")
	instDir := filepath.Dir(confFile)
	if err := os.WriteFile(confFile, []byte(liveConfForInstDir(instDir)), 0644); err != nil {
		t.Fatal(err)
	}

	job := newRefreshJob("1.1.1.1", []int{30000}, ApplyModeConfigSet)
	job.params.ClusterType = consts.TendisTypeTwemproxyRedisInstance
	job.params.PortConfConfigs = map[string]RedisConfRenderItem{"30000": targetConfItem(instDir)}
	job.params.PortTargetPasswords = map[string]string{"30000": "newpasswd"}
	job.replSnapshots[30000] = replSnapshot{
		addr: "1.1.1.1:30000", role: consts.RedisSlaveRole, masterHost: "1.1.1.2", masterPort: "30000",
	}

	plan, err := job.buildPortPlan(30000)
	if err != nil {
		t.Fatalf("buildPortPlan err:%v", err)
	}
	for _, want := range []string{"requirepass newpasswd", "masterauth newpasswd"} {
		if !strings.Contains(plan.confData, want) {
			t.Errorf("plan missing %q:\n%s", want, plan.confData)
		}
	}
	if strings.Contains(plan.confData, "xxxxpasswd") {
		t.Errorf("old password left in the plan:\n%s", plan.confData)
	}
}

func TestIsRedisAuthError(t *testing.T) {
	cases := []struct {
		name string
		err  error
		want bool
	}{
		{"wrong password", errors.New("redis new conn fail,err:WRONGPASS invalid username-password pair"), true},
		{"no password sent", errors.New("NOAUTH Authentication required."), true},
		{"old redis wording", errors.New("ERR invalid password"), true},
		// 改成无密码的单据里, 主库先改完就是这一种: 我们还带着密码去 AUTH, 对端已经不设密码了
		{"target has no password anymore", errors.New("ERR Client sent AUTH, but no password is set"), true},
		{"unreachable", errors.New("dial tcp 1.1.1.1:30000: connect: connection refused"), false},
		{"timeout", errors.New("context deadline exceeded"), false},
		{"nil", nil, false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := isRedisAuthError(tc.err); got != tc.want {
				t.Errorf("isRedisAuthError(%v)=%v, want %v", tc.err, got, tc.want)
			}
		})
	}
}

// TestMasterAcceptsPassword 分清"密码不对"和"探不到". 前者是明确的"主库还没改",
// 后者只说明我们不知道, 两者在 followMasterAuth 里的处置不一样
func TestMasterAcceptsPassword(t *testing.T) {
	master := newFakeRedis(t, "newpasswd")
	if accepted, err := masterAcceptsPassword(master.addr(), "newpasswd"); err != nil || !accepted {
		t.Errorf("accepted=%v,err=%v, want the target password to be accepted", accepted, err)
	}
	if accepted, err := masterAcceptsPassword(master.addr(), "xxxxpasswd"); err != nil || accepted {
		t.Errorf("accepted=%v,err=%v, want a plain rejection without an error", accepted, err)
	}

	// 主库已经改成无密码: 我们还揣着密码去 AUTH, 对端回 "no password is set"
	nopass := newFakeRedis(t, "")
	if accepted, err := masterAcceptsPassword(nopass.addr(), "newpasswd"); err != nil || accepted {
		t.Errorf("accepted=%v,err=%v, want a rejection from a password-less master", accepted, err)
	}
	if accepted, err := masterAcceptsPassword(nopass.addr(), ""); err != nil || !accepted {
		t.Errorf("accepted=%v,err=%v, want an empty target to match a password-less master", accepted, err)
	}

	// 连不上必须是 error, 不能是 accepted=false: 后者会被当成"主库确实还没改"
	dead := newFakeRedis(t, "")
	deadAddr := dead.addr()
	dead.ln.Close()
	if accepted, err := masterAcceptsPassword(deadAddr, "newpasswd"); err == nil || accepted {
		t.Errorf("accepted=%v,err=%v, want an error when the master cannot be reached", accepted, err)
	}
}

const (
	oldPass = "xxxxpasswd"
	newPass = "newpasswd"
)

// refreshJobWithMaster 一个改 30000 端口密码的任务, 复制快照指向给定的假主库
func refreshJobWithMaster(t *testing.T, mode string, master *fakeRedis, role string) *RedisConfRefresh {
	t.Helper()
	job := newRefreshJob("1.1.1.1", []int{30000}, mode)
	job.params.ClusterType = consts.TendisTypeTwemproxyRedisInstance
	job.params.PortTargetPasswords = map[string]string{"30000": newPass}
	masterHost, masterPort := master.hostPort()
	job.replSnapshots[30000] = replSnapshot{
		addr: "1.1.1.1:30000", role: role, masterHost: masterHost, masterPort: masterPort,
	}
	return job
}

// TestResolveMasterAuthTargets masterauth 该不该跟到新密码, 由实拨一次主库决定.
//
// 跟早了(主库还是旧密码)和不跟(主库已经是新密码)都会让从库在下次重连时 AUTH 失败,
// 光看本机分不出这两种. 探不出结论时一律按"还没改"处理, 现存链路还活着, 保持现状不会更糟.
func TestResolveMasterAuthTargets(t *testing.T) {
	cases := []struct {
		name string
		// masterPass 主库当前收的密码; killMaster 模拟主库连不上
		masterPass string
		killMaster bool
		role       string
		clusterTyp string
		noTarget   bool
		want       bool
	}{
		{name: "master already changed", masterPass: newPass, role: consts.RedisSlaveRole, want: true},
		{name: "master not changed yet", masterPass: oldPass, role: consts.RedisSlaveRole, want: false},
		{name: "master unreachable", masterPass: newPass, killMaster: true, role: consts.RedisSlaveRole, want: false},
		// 主库自己没有 masterauth 要跟; 实例没在跑时抓不到快照, role 为空, 同样落在这里
		{name: "instance is a master", masterPass: newPass, role: consts.RedisMasterRole, want: false},
		{name: "instance is down", masterPass: newPass, role: "", want: false},
		{
			// cluster 的凭据由 redis_switch / redis_cluster_failover 统一管
			name: "cluster is skipped", masterPass: newPass, role: consts.RedisSlaveRole,
			clusterTyp: consts.TendisTypePredixyRedisCluster, want: false,
		},
		{name: "port without a password change", masterPass: newPass, role: consts.RedisSlaveRole,
			noTarget: true, want: false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			master := newFakeRedis(t, tc.masterPass)
			if tc.killMaster {
				master.ln.Close()
			}
			job := refreshJobWithMaster(t, ApplyModeConfigSet, master, tc.role)
			if tc.clusterTyp != "" {
				job.params.ClusterType = tc.clusterTyp
			}
			if tc.noTarget {
				job.params.PortTargetPasswords = nil
			}

			job.resolveMasterAuthTargets()

			if got := job.masterAuthFollow[30000]; got != tc.want {
				t.Errorf("masterAuthFollow=%v, want %v", got, tc.want)
			}
			if tc.noTarget {
				if _, probed := job.masterAuthFollow[30000]; probed {
					t.Error("a port without a target password should not be probed at all")
				}
			}
		})
	}
}

// TestFollowMasterAuth config_set 模式按探测结论改运行态, 自己不再拨主库
func TestFollowMasterAuth(t *testing.T) {
	newLocal := func(t *testing.T, follow bool, currentAuth string) (*RedisConfRefresh, *myredis.RedisClient, *fakeRedis) {
		t.Helper()
		local := newFakeRedis(t, oldPass)
		local.setConfig("masterauth", currentAuth)
		cli, err := myredis.NewRedisClient(local.addr(), oldPass, 0, consts.TendisTypeRedisInstance, 5*time.Second)
		if err != nil {
			t.Fatalf("connect fake local redis failed:%v", err)
		}
		t.Cleanup(cli.Close)

		job := newRefreshJob("1.1.1.1", []int{30000}, ApplyModeConfigSet)
		job.masterAuthFollow[30000] = follow
		return job, cli, local
	}

	t.Run("follows when the probe said so", func(t *testing.T) {
		job, cli, local := newLocal(t, true, oldPass)
		changed, err := job.followMasterAuth(cli, 30000, newPass)
		if err != nil {
			t.Fatalf("followMasterAuth err:%v", err)
		}
		if !changed {
			t.Error("masterauth should have followed")
		}
		if !local.got("CONFIG SET masterauth " + newPass) {
			t.Error("masterauth was not actually set on the instance")
		}
	})

	t.Run("stays put when the probe said the master is behind", func(t *testing.T) {
		job, cli, local := newLocal(t, false, oldPass)
		changed, err := job.followMasterAuth(cli, 30000, newPass)
		if err != nil || changed {
			t.Errorf("changed=%v,err=%v, want masterauth to stay put", changed, err)
		}
		if local.got("CONFIG SET masterauth") {
			t.Error("masterauth must not move ahead of the master")
		}
	})

	// 已经是目标值就别再写一遍
	t.Run("already following", func(t *testing.T) {
		job, cli, local := newLocal(t, true, newPass)
		changed, err := job.followMasterAuth(cli, 30000, newPass)
		if err != nil || changed {
			t.Errorf("changed=%v,err=%v, want a no-op", changed, err)
		}
		if local.got("CONFIG SET masterauth") {
			t.Error("masterauth was rewritten with the value it already had")
		}
	})
}

// TestStopRedisForRestartTakesPasswordFromPlan restart 模式停机要用改写前的密码: 配置文件
// 此时已经是渲染结果(改密码时里面是新密码), 而进程还只认旧的.
//
// 这里没有真实实例, 靠"密码从哪来"造出可观测的差异: 磁盘上没有任何 conf 文件时,
// 读文件那条路径必然报错, 从 plan 取密码那条则一路走到不存在的 stop-redis.sh 后返回 not exist.
func TestStopRedisForRestartTakesPasswordFromPlan(t *testing.T) {
	t.Setenv("REDIS_DATA_DIR", t.TempDir())
	job := newRefreshJob("1.1.1.1", []int{30000}, ApplyModeRestart)
	plan := &regenConfPlan{
		oldConfData: "port 30000\nrequirepass \"" + oldPass + "\"\n",
		confData:    "port 30000\nrequirepass " + newPass + "\n",
	}
	if err := stopRedisViaScript(job.params.IP, 30000, job.runtime.Logger); err == nil {
		t.Fatal("reading the password from disk should have failed here,test cannot tell the paths apart")
	}
	if err := job.stopRedisForRestart(30000, plan); err == nil || !strings.Contains(err.Error(), "stop-redis.sh") {
		t.Errorf("stopRedisForRestart should take the password from the plan then fail on missing stop script,err:%v", err)
	}

	// 旧配置没声明 requirepass 时(密码可能在 instance.conf 里)退回读文件的老路径
	plan.oldConfData = "port 30000\n"
	if err := job.stopRedisForRestart(30000, plan); err == nil {
		t.Error("without requirepass on disk it should fall back to reading the conf file")
	}
}

func TestRedisConfRefreshBuildPortPlanCarriesLocal(t *testing.T) {
	confFile := setupInstanceConf(t, 30000, "placeholder\n")
	instDir := filepath.Dir(confFile)
	liveConf := liveConfForInstDir(instDir)
	if err := os.WriteFile(confFile, []byte(liveConf), 0644); err != nil {
		t.Fatal(err)
	}

	job := newRefreshJob("1.1.1.1", []int{30000}, ApplyModeConfFile)
	job.params.ClusterType = consts.TendisTypeTwemproxyRedisInstance
	job.params.PortConfConfigs = map[string]RedisConfRenderItem{"30000": targetConfItem(instDir)}
	job.replSnapshots[30000] = replSnapshot{
		addr: "1.1.1.1:30000", role: consts.RedisSlaveRole, masterHost: "1.1.1.2", masterPort: "30000",
	}

	plan, err := job.buildPortPlan(30000)
	if err != nil {
		t.Fatalf("buildPortPlan err:%v", err)
	}
	if !strings.Contains(plan.confData, "requirepass xxxxpasswd") {
		t.Errorf("password not taken from disk\n%s", plan.confData)
	}
	if !strings.Contains(plan.confData, "replicaof 1.1.1.2 30000") {
		t.Errorf("replicaof not carried from local\n%s", plan.confData)
	}
	if !strings.Contains(plan.confData, "maxmemory 8589934592") {
		t.Errorf("maxmemory not carried from local\n%s", plan.confData)
	}
	if !strings.Contains(plan.confData, "replica-lazy-flush yes") {
		t.Errorf("delivered directive missing\n%s", plan.confData)
	}
	if strings.Contains(plan.confData, "slave-lazy-flush") {
		t.Errorf("stale directive should be dropped\n%s", plan.confData)
	}
}

func TestWritePlanIfChangedSkipWhenEqual(t *testing.T) {
	confFile := setupInstanceConf(t, 30000, "port 30000\ndir /data/redis/30000/data\n")
	orig, err := os.ReadFile(confFile)
	if err != nil {
		t.Fatal(err)
	}
	job := newRefreshJob("1.1.1.1", []int{30000}, ApplyModeConfFile)
	plan := &regenConfPlan{
		confFile:    confFile,
		oldConfData: string(orig),
		confData:    "port 30000\ndir \"/data/redis/30000/data\"\n", // quote-only, still equal
	}
	if err = job.writePlanIfChanged(30000, plan); err != nil {
		t.Fatalf("writePlanIfChanged err:%v", err)
	}
	got, err := os.ReadFile(confFile)
	if err != nil {
		t.Fatal(err)
	}
	if string(got) != string(orig) {
		t.Errorf("equal conf should not be rewritten\ngot:\n%s", got)
	}
	matches, err := filepath.Glob(confFile + ".*.bak")
	if err != nil {
		t.Fatal(err)
	}
	if len(matches) != 0 {
		t.Errorf("skip path should not create backup, got %v", matches)
	}
}

func TestWritePlanIfChangedWritesWhenDifferent(t *testing.T) {
	confFile := setupInstanceConf(t, 30000, "port 30000\ntimeout 10\n")
	job := newRefreshJob("1.1.1.1", []int{30000}, ApplyModeConfFile)
	plan := &regenConfPlan{
		confFile:    confFile,
		oldConfData: "port 30000\ntimeout 10\n",
		confData:    "port 30000\ntimeout 60\n",
	}
	if err := job.writePlanIfChanged(30000, plan); err != nil {
		t.Fatalf("writePlanIfChanged err:%v", err)
	}
	got, err := os.ReadFile(confFile)
	if err != nil {
		t.Fatal(err)
	}
	if string(got) != plan.confData {
		t.Errorf("conf not written, got:\n%s", got)
	}
}

func TestDecideRestartAction(t *testing.T) {
	cases := []struct {
		running, confEqual, runtimeMatch bool
		want                             restartAction
	}{
		{true, true, true, restartSkip},
		{true, true, false, restartBounce},
		{true, false, true, restartBounce},
		{true, false, false, restartBounce},
		{false, true, false, restartStart},
		{false, false, false, restartStart},
	}
	for _, tc := range cases {
		got := decideRestartAction(tc.running, tc.confEqual, tc.runtimeMatch)
		if got != tc.want {
			t.Errorf("decideRestartAction(%v,%v,%v)=%d, want %d",
				tc.running, tc.confEqual, tc.runtimeMatch, got, tc.want)
		}
	}
}

func TestRedisConfRefreshName(t *testing.T) {
	if NewRedisConfRefresh().Name() != "redis_conf_refresh" {
		t.Errorf("Name()=%q", NewRedisConfRefresh().Name())
	}
}

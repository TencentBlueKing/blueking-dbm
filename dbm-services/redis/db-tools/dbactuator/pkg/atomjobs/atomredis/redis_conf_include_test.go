package atomredis

import (
	"os"
	"path/filepath"
	"slices"
	"strings"
	"testing"

	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
)

func writeTestFile(t *testing.T, path, data string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		t.Fatalf("mkdir %s failed:%v", filepath.Dir(path), err)
	}
	if err := os.WriteFile(path, []byte(data), 0644); err != nil {
		t.Fatalf("write %s failed:%v", path, err)
	}
}

func readTestFile(t *testing.T, path string) string {
	t.Helper()
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read %s failed:%v", path, err)
	}
	return string(data)
}

func TestExpandRedisConfIncludes(t *testing.T) {
	dir := t.TempDir()
	confFile := filepath.Join(dir, "redis.conf")
	instConf := filepath.Join(dir, "instance.conf")
	writeTestFile(t, instConf, "requirepass p1\nmaxmemory 1gb\n")
	nested := filepath.Join(dir, "nested.conf")
	writeTestFile(t, nested, "include "+instConf+"\nslaveof 1.1.1.2 30000\n")
	noNewline := filepath.Join(dir, "nonl.conf")
	writeTestFile(t, noNewline, "masterauth p1")

	cases := []struct {
		name         string
		raw          string
		want         string
		wantIncludes []string
	}{
		{
			name: "no include returns raw unchanged",
			raw:  "port 30000\n# include /nowhere.conf\n\n",
			want: "port 30000\n# include /nowhere.conf\n\n",
		},
		{
			name:         "absolute path inlined in place",
			raw:          "port 30000\ninclude " + instConf + "\nmaxmemory 2gb\n",
			want:         "port 30000\nrequirepass p1\nmaxmemory 1gb\nmaxmemory 2gb\n",
			wantIncludes: []string{instConf},
		},
		{
			name:         "relative path resolved against conf dir",
			raw:          "include instance.conf\n",
			want:         "requirepass p1\nmaxmemory 1gb\n",
			wantIncludes: []string{instConf},
		},
		{
			name:         "quoted path and upper case directive",
			raw:          "INCLUDE \"" + instConf + "\"\n",
			want:         "requirepass p1\nmaxmemory 1gb\n",
			wantIncludes: []string{instConf},
		},
		{
			name:         "nested include",
			raw:          "port 30000\ninclude " + nested + "\n",
			want:         "port 30000\nrequirepass p1\nmaxmemory 1gb\nslaveof 1.1.1.2 30000\n",
			wantIncludes: []string{nested, instConf},
		},
		{
			name:         "included file without trailing newline does not glue to next line",
			raw:          "include " + noNewline + "\nport 30000\n",
			want:         "masterauth p1\nport 30000\n",
			wantIncludes: []string{noNewline},
		},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got, includes, err := expandRedisConfIncludes(confFile, tc.raw)
			if err != nil {
				t.Fatalf("expand err:%v", err)
			}
			if got != tc.want {
				t.Errorf("expanded =\n%q\nwant\n%q", got, tc.want)
			}
			if strings.Join(includes, ",") != strings.Join(tc.wantIncludes, ",") {
				t.Errorf("includes = %v, want %v", includes, tc.wantIncludes)
			}
		})
	}
}

func TestExpandRedisConfIncludesOverrideOrder(t *testing.T) {
	dir := t.TempDir()
	confFile := filepath.Join(dir, "redis.conf")
	instConf := filepath.Join(dir, "instance.conf")
	writeTestFile(t, instConf, "maxmemory 1gb\n")

	after, _, err := expandRedisConfIncludes(confFile, "include "+instConf+"\nmaxmemory 2gb\n")
	if err != nil {
		t.Fatal(err)
	}
	if got := parseRedisConfDirectives(after).lastValue("maxmemory"); got != "2gb" {
		t.Errorf("directive after include should win,got %q", got)
	}
	before, _, err := expandRedisConfIncludes(confFile, "maxmemory 2gb\ninclude "+instConf+"\n")
	if err != nil {
		t.Fatal(err)
	}
	if got := parseRedisConfDirectives(before).lastValue("maxmemory"); got != "1gb" {
		t.Errorf("included value should override the one before include,got %q", got)
	}
}

func TestExpandRedisConfIncludesErrors(t *testing.T) {
	dir := t.TempDir()
	confFile := filepath.Join(dir, "redis.conf")
	writeTestFile(t, confFile, "include "+filepath.Join(dir, "a.conf")+"\n")
	writeTestFile(t, filepath.Join(dir, "a.conf"), "include "+confFile+"\n")

	// 一条 9 层的链: deep0 -> deep1 -> ... -> deep9
	for i := 0; i < 9; i++ {
		writeTestFile(t, filepath.Join(dir, "deep"+string(rune('0'+i))+".conf"),
			"include "+filepath.Join(dir, "deep"+string(rune('0'+i+1))+".conf")+"\n")
	}
	writeTestFile(t, filepath.Join(dir, "deep9.conf"), "port 30000\n")

	cases := []struct {
		name    string
		raw     string
		wantErr string
	}{
		{"missing file", "include " + filepath.Join(dir, "instance.conf") + "\n", "instance.conf cannot be read"},
		{"cycle", "include " + filepath.Join(dir, "a.conf") + "\n", "forms a cycle"},
		{"glob", "include " + filepath.Join(dir, "*.conf") + "\n", "glob"},
		{"too deep", "include " + filepath.Join(dir, "deep0.conf") + "\n", "nested deeper than"},
		{"no path", "include\n", "without a path"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			_, _, err := expandRedisConfIncludes(confFile, tc.raw)
			if err == nil || !strings.Contains(err.Error(), tc.wantErr) {
				t.Errorf("err = %v, want it to contain %q", err, tc.wantErr)
			}
		})
	}
}

// setupGcsLayout 复现 GCS 迁过来的布局: redis.conf 只有基础项和 include,
// 密码与主从关系都在 instance.conf 里
func setupGcsLayout(t *testing.T, port int) (confFile, instConf, raw string) {
	t.Helper()
	confFile = setupInstanceConf(t, port, "placeholder\n")
	instDir := filepath.Dir(confFile)
	instConf = filepath.Join(instDir, "instance.conf")
	raw = strings.Join([]string{
		"bind 1.1.1.1",
		"port 30000",
		"dir " + filepath.Join(instDir, "data"),
		"maxmemory 8589934592",
		"include " + instConf,
	}, "\n") + "\n"
	writeTestFile(t, confFile, raw)
	writeTestFile(t, instConf, "requirepass xxxxpasswd\nslaveof 1.1.1.2 30000\nmasterauth xxxxpasswd\n")
	return confFile, instConf, raw
}

func retiredBackups(t *testing.T, file string) []string {
	t.Helper()
	matches, err := filepath.Glob(file + ".*.bak")
	if err != nil {
		t.Fatal(err)
	}
	return matches
}

func TestRegenConfFileRetiresIncludedInstanceConf(t *testing.T) {
	confFile, instConf, raw := setupGcsLayout(t, 30000)
	instContent := readTestFile(t, instConf)

	job := buildRegenJob("1.1.1.1", []int{30000})
	job.params.PortConfConfigs = map[string]RedisConfRenderItem{"30000": targetConfItem(filepath.Dir(confFile))}
	if err := job.regenConfFile(30000); err != nil {
		t.Fatalf("regenConfFile err:%v", err)
	}

	got := readTestFile(t, confFile)
	for _, want := range []string{"requirepass xxxxpasswd", "masterauth xxxxpasswd", "slaveof 1.1.1.2 30000"} {
		if !strings.Contains(got, want) {
			t.Errorf("regenerated conf missing %q:\n%s", want, got)
		}
	}
	if strings.Contains(got, `requirepass ""`) || strings.Contains(got, "include") {
		t.Errorf("regenerated conf must carry the real password and no include:\n%s", got)
	}
	if backup := readTestFile(t, job.confBackupFiles[30000]); backup != raw {
		t.Errorf("backup should hold the raw conf with include,got:\n%s", backup)
	}
	if _, err := os.Stat(instConf); !os.IsNotExist(err) {
		t.Errorf("instance.conf should be retired,stat err:%v", err)
	}
	moved := retiredBackups(t, instConf)
	if len(moved) != 1 || readTestFile(t, moved[0]) != instContent {
		t.Errorf("instance.conf should be moved aside with its content kept,got %v", moved)
	}
}

func TestRegenConfFileKeepsIncludeOutsideInstDir(t *testing.T) {
	confFile := setupInstanceConf(t, 30000, "placeholder\n")
	instDir := filepath.Dir(confFile)
	shared := filepath.Join(t.TempDir(), "common.conf")
	writeTestFile(t, shared, "requirepass xxxxpasswd\n")
	writeTestFile(t, confFile, liveConfForInstDir(instDir)+"include "+shared+"\n")

	job := buildRegenJob("1.1.1.1", []int{30000})
	job.params.PortConfConfigs = map[string]RedisConfRenderItem{"30000": targetConfItem(instDir)}
	if err := job.regenConfFile(30000); err != nil {
		t.Fatalf("regenConfFile err:%v", err)
	}
	if strings.Contains(readTestFile(t, confFile), "include") {
		t.Error("regenerated conf should not keep the include")
	}
	if _, err := os.Stat(shared); err != nil {
		t.Errorf("include outside inst dir should be left in place,err:%v", err)
	}
	if len(job.retiredIncludes[30000]) != 0 {
		t.Errorf("nothing should be recorded as retired,got %+v", job.retiredIncludes[30000])
	}
}

func TestRegenConfFileRestoresWhenRetireFails(t *testing.T) {
	confFile, instConf, raw := setupGcsLayout(t, 30000)
	orig := renameIncludedConfFile
	renameIncludedConfFile = func(string, string) error { return os.ErrPermission }
	t.Cleanup(func() { renameIncludedConfFile = orig })

	job := buildRegenJob("1.1.1.1", []int{30000})
	job.params.PortConfConfigs = map[string]RedisConfRenderItem{"30000": targetConfItem(filepath.Dir(confFile))}
	err := job.regenConfFile(30000)
	if err == nil || !strings.Contains(err.Error(), "retire include") {
		t.Fatalf("err = %v, want retire failure", err)
	}
	if got := readTestFile(t, confFile); got != raw {
		t.Errorf("redis.conf should be restored to the raw conf,got:\n%s", got)
	}
	if _, statErr := os.Stat(instConf); statErr != nil {
		t.Errorf("instance.conf should stay in place,err:%v", statErr)
	}
	if _, ok := job.confBackupFiles[30000]; ok {
		t.Error("failed regen should not record a backup for rollback")
	}
}

func TestRestoreRedisConfFileBringsBackRetiredInclude(t *testing.T) {
	confFile, instConf, raw := setupGcsLayout(t, 30000)
	instContent := readTestFile(t, instConf)

	job := buildRegenJob("1.1.1.1", []int{30000})
	job.params.PortConfConfigs = map[string]RedisConfRenderItem{"30000": targetConfItem(filepath.Dir(confFile))}
	if err := job.regenConfFile(30000); err != nil {
		t.Fatalf("regenConfFile err:%v", err)
	}
	if err := job.restoreRedisConfFile(30000); err != nil {
		t.Fatalf("restoreRedisConfFile err:%v", err)
	}
	if got := readTestFile(t, confFile); got != raw {
		t.Errorf("redis.conf should be back to the raw conf,got:\n%s", got)
	}
	if got := readTestFile(t, instConf); got != instContent {
		t.Errorf("instance.conf should be back with its content,got:\n%s", got)
	}
	if moved := retiredBackups(t, instConf); len(moved) != 0 {
		t.Errorf("no retired copy should remain,got %v", moved)
	}
}

func TestPrecheckReplExpectationSeesIncludedReplication(t *testing.T) {
	setupGcsLayout(t, 30000)

	slave := buildRegenJob("1.1.1.1", []int{30000})
	slave.params.Role = consts.MetaRoleRedisSlave
	slave.replSnapshots[30000] = replSnapshot{
		addr: "1.1.1.1:30000", role: consts.RedisSlaveRole, masterHost: "1.1.1.2", masterPort: "30000",
	}
	if err := slave.precheckReplExpectation([]int{30000}); err != nil {
		t.Errorf("slaveof only in instance.conf should satisfy the snapshot,err:%v", err)
	}

	// 实例已被 switch 关掉、元数据角色是 master, 而 instance.conf 里留着 slaveof
	master := buildRegenJob("1.1.1.1", []int{30000})
	master.params.Role = consts.MetaRoleRedisMaster
	err := master.precheckReplExpectation([]int{30000})
	if err == nil || !strings.Contains(err.Error(), "turn a master into a replica") {
		t.Errorf("err = %v, want the included slaveof caught", err)
	}
}

func TestLocalDataFileNamesSeesIncludedDbfilename(t *testing.T) {
	confFile, instConf, _ := setupGcsLayout(t, 30000)
	writeTestFile(t, instConf, readTestFile(t, instConf)+"dbfilename dump-30000.rdb\n")

	job := buildRegenJob("1.1.1.1", []int{30000})
	job.params.PortConfConfigs = map[string]RedisConfRenderItem{"30000": targetConfItem(filepath.Dir(confFile))}
	if err := job.regenConfFile(30000); err != nil {
		t.Fatalf("regenConfFile err:%v", err)
	}
	// 此时 instance.conf 已随重建挪走, 旧配置里的 dbfilename 只能靠重建时记下的展开结果
	_, names, err := job.localDataFileNames(30000)
	if err != nil {
		t.Fatalf("localDataFileNames err:%v", err)
	}
	if !slices.Contains(names, "dump-30000.rdb") {
		t.Errorf("dbfilename defined in instance.conf should be covered,got %v", names)
	}
}

// TestRegenPlainConfUnchanged 没有 include 的配置: 渲染结果与"直接拿磁盘原文当旧配置"
// (改动前的做法)逐字节一致, 备份是原文, 目录里没被 include 的 instance.conf 不动
func TestRegenPlainConfUnchanged(t *testing.T) {
	confFile := setupInstanceConf(t, 30000, "placeholder\n")
	instDir := filepath.Dir(confFile)
	raw := liveConfForInstDir(instDir)
	writeTestFile(t, confFile, raw)
	strayInstConf := filepath.Join(instDir, "instance.conf")
	writeTestFile(t, strayInstConf, "requirepass stale\n")

	job := buildRegenJob("1.1.1.1", []int{30000})
	item := targetConfItem(instDir)
	job.params.PortConfConfigs = map[string]RedisConfRenderItem{"30000": item}

	legacyReq := job.regenRequest(30000)
	legacyReq.Item = item
	legacyReq.ConfFile = confFile
	legacyReq.OldConfData = raw
	legacy, err := legacyReq.buildPlan()
	if err != nil {
		t.Fatalf("legacy buildPlan err:%v", err)
	}
	plan, err := job.buildRegenConfPlan(30000)
	if err != nil {
		t.Fatalf("buildRegenConfPlan err:%v", err)
	}
	if plan.confData != legacy.confData {
		t.Errorf("plain conf output changed:\ngot:\n%s\nwant:\n%s", plan.confData, legacy.confData)
	}
	if plan.hasInclude() || plan.oldConfData != raw {
		t.Errorf("plain conf should not be treated as include layout,includes=%v", plan.includedFiles)
	}

	if err = job.regenConfFile(30000); err != nil {
		t.Fatalf("regenConfFile err:%v", err)
	}
	if got := readTestFile(t, confFile); got != legacy.confData {
		t.Errorf("written conf differs from legacy output:\n%s", got)
	}
	if backup := readTestFile(t, job.confBackupFiles[30000]); backup != raw {
		t.Errorf("backup should be the raw conf,got:\n%s", backup)
	}
	if got := readTestFile(t, strayInstConf); got != "requirepass stale\n" {
		t.Errorf("instance.conf not included should be left untouched,got %q", got)
	}
	if moved := retiredBackups(t, strayInstConf); len(moved) != 0 {
		t.Errorf("instance.conf not included should not be retired,got %v", moved)
	}
}

func TestValidateRegenConfRejectsInclude(t *testing.T) {
	oldConf := "port 30000\ndir /data1/redis/30000/data\n"
	conf := oldConf + "include /data1/redis/30000/instance.conf\n"
	job := buildRegenJob("1.1.1.1", []int{30000})
	err := job.validateRegenConf(
		30000, "/data1/redis/30000/redis.conf", conf, oldConf, parseRedisConfDirectives(oldConf))
	if err == nil || !strings.Contains(err.Error(), "must not contain include") {
		t.Errorf("err = %v, want include rejected", err)
	}
}

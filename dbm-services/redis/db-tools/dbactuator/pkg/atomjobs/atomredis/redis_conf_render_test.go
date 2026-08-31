package atomredis

import (
	"strconv"
	"strings"
	"testing"

	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
)

func TestBuildRedisConfTemplateExpandsRepeatableDirectives(t *testing.T) {
	// dbconfig 里 rename-command / client-output-buffer-limit / save 是"一个配置项 +
	// 值内嵌换行并重复 key 前缀", 渲染后必须自然展开成多行
	confConfigs := map[string]string{
		"rename-command": "config confxx \nrename-command flushdb cleandb \n" +
			"rename-command flushall cleanall\nrename-command debug nobug\nrename-command keys mykeys",
		"client-output-buffer-limit": "normal 256mb 512mb 300\nclient-output-buffer-limit slave 2048mb 2048mb 300\n" +
			"client-output-buffer-limit pubsub 32mb 8mb 60",
		"save": "",
		"port": "{{port}}",
	}
	got := BuildRedisConfTemplate(confConfigs, nil, "redis-6.2.7")

	if want, count := "rename-command", strings.Count(got, "rename-command "); count != 5 {
		t.Errorf("%s lines = %d, want 5\ngot:\n%s", want, count, got)
	}
	if count := strings.Count(got, "client-output-buffer-limit "); count != 3 {
		t.Errorf("client-output-buffer-limit lines = %d, want 3\ngot:\n%s", count, got)
	}
	// save "" 需要写成带引号的空值, 否则 redis 解析报错
	if !strings.Contains(got, "save \"\"\n") {
		t.Errorf("empty save value not quoted\ngot:\n%s", got)
	}
}

func TestBuildRedisConfTemplateIsSorted(t *testing.T) {
	// 渲染结果需稳定可 diff: Go map 遍历是随机序, 必须按 key 排序输出
	confConfigs := map[string]string{"zset-max-ziplist-entries": "128", "appendonly": "no", "maxmemory": "{{maxmemory}}"}
	first := BuildRedisConfTemplate(confConfigs, nil, "redis-6.2.7")
	for i := 0; i < 20; i++ {
		if got := BuildRedisConfTemplate(confConfigs, nil, "redis-6.2.7"); got != first {
			t.Fatalf("render not deterministic:\n%s\nvs\n%s", first, got)
		}
	}
	wantOrder := []string{"appendonly no", "maxmemory {{maxmemory}}", "zset-max-ziplist-entries 128"}
	if got := strings.TrimRight(first, "\n"); got != strings.Join(wantOrder, "\n") {
		t.Errorf("render = %q, want sorted %q", got, strings.Join(wantOrder, "\n"))
	}
}

func TestBuildRedisConfTemplateModules(t *testing.T) {
	confConfigs := map[string]string{"appendonly": "yes", "loadmodule": "ignored"}
	got := BuildRedisConfTemplate(confConfigs, []LoadModuleItem{{SoFile: "libB2RedisModule.so"}}, "redis-6.2.7")

	// dbconfig 里的 loadmodule 项不参与渲染, module 只从 LoadModulesDetail 来
	if strings.Contains(got, "loadmodule ignored") {
		t.Errorf("dbconfig loadmodule item should be skipped\ngot:\n%s", got)
	}
	if !strings.Contains(got, "loadmodule /home/mysql/redis_modules/libB2RedisModule.so") {
		t.Errorf("module not rendered\ngot:\n%s", got)
	}
	// libB2RedisModule 必须关 aof, 且要覆盖 dbconfig 的 appendonly yes -> 只能排在其后
	appendonlyNo, appendonlyYes := strings.Index(got, "appendonly no"), strings.Index(got, "appendonly yes")
	if appendonlyNo < 0 || appendonlyYes < 0 || appendonlyNo < appendonlyYes {
		t.Errorf("module appendonly no must come after dbconfig appendonly yes\ngot:\n%s", got)
	}
}

func TestBuildRedisConfTemplateSkipsReplDisklessSyncOnRedis2817(t *testing.T) {
	confConfigs := map[string]string{"repl-diskless-sync": "no", "port": "{{port}}"}
	if got := BuildRedisConfTemplate(confConfigs, nil, "redis-2.8.17-rocksdb-v1.3.10"); strings.Contains(
		got, "repl-diskless-sync") {
		t.Errorf("repl-diskless-sync must be skipped for redis-2.8.17\ngot:\n%s", got)
	}
	if got := BuildRedisConfTemplate(confConfigs, nil, "redis-6.2.7"); !strings.Contains(
		got, "repl-diskless-sync no") {
		t.Errorf("repl-diskless-sync must be kept for redis-6\ngot:\n%s", got)
	}
}

// mustRender 走完整的 "推导 -> 替换" 两步
func mustRender(t *testing.T, tmpl string, p RedisConfRenderParams) string {
	t.Helper()
	values, err := p.Resolve()
	if err != nil {
		t.Fatalf("Resolve err:%v", err)
	}
	return RenderRedisConfData(tmpl, values)
}

// placeholderNames 取出已推导的占位符名字, 用于断言某些占位符压根没被算出来
func placeholderNames(values RedisConfRenderValues) []string {
	names := make([]string, 0, len(values))
	for _, ph := range values {
		names = append(names, ph.name)
	}
	return names
}

func TestRenderRedisConfDataEmptyPasswordQuoted(t *testing.T) {
	// 空密码必须渲染成 "": 裸 requirepass 没有参数, redis 解析配置文件直接报错
	got := mustRender(t, "requirepass {{password}}\nmasterauth {{password}}\n", RedisConfRenderParams{
		IP:      "1.1.1.1",
		Port:    30000,
		InstDir: "/data1/redis/30000",
		DbType:  consts.TendisTypeTwemproxyRedisInstance,
	})
	if want := "requirepass \"\"\nmasterauth \"\"\n"; got != want {
		t.Errorf("rendered conf = %q, want %q", got, want)
	}
}

func TestRenderRedisConfData(t *testing.T) {
	tmpl := strings.Join([]string{
		"bind {{address}}",
		"port {{port}}",
		"requirepass {{password}}",
		"dir {{redis_data_dir}}/data",
		"logfile {{redis_data_dir}}/redis.log",
		"databases {{databases}}",
		"cluster-enabled {{cluster_enabled}}",
		"maxmemory {{maxmemory}}",
	}, "\n") + "\n"

	got := mustRender(t, tmpl, RedisConfRenderParams{
		IP:        "1.1.1.1",
		Port:      30000,
		Password:  "xxxx",
		Databases: 4,
		InstDir:   "/data1/redis/30000",
		DbType:    "PredixyRedisCluster",
		MaxMemory: "8589934592",
		InstCount: 4,
	})
	for _, want := range []string{
		"bind 1.1.1.1", "port 30000", "requirepass xxxx",
		"dir /data1/redis/30000/data", "logfile /data1/redis/30000/redis.log",
		"databases 4", "cluster-enabled yes", "maxmemory 8589934592",
	} {
		if !strings.Contains(got, want) {
			t.Errorf("rendered conf missing %q\ngot:\n%s", want, got)
		}
	}
}

func TestRenderRedisConfDataMaxMemoryDefaultsToZero(t *testing.T) {
	got := mustRender(t, "maxmemory {{maxmemory}}\n", RedisConfRenderParams{Port: 30000})
	if got != "maxmemory 0\n" {
		t.Errorf("rendered = %q, want %q", got, "maxmemory 0\n")
	}
}

func TestRenderRedisConfDataClusterEnabled(t *testing.T) {
	cases := map[string]string{
		"PredixyRedisCluster":        "yes",
		"TwemproxyRedisInstance":     "no",
		"PredixyTendisplusCluster":   "yes",
		"TwemproxyTendisSSDInstance": "no",
	}
	for dbType, want := range cases {
		got := mustRender(t, "cluster-enabled {{cluster_enabled}}\n",
			RedisConfRenderParams{Port: 30000, DbType: dbType})
		if strings.TrimSpace(got) != "cluster-enabled "+want {
			t.Errorf("dbType(%s) rendered %q, want cluster-enabled %s", dbType, strings.TrimSpace(got), want)
		}
	}
}

func TestRenderRedisConfDataKeepsUnknownPlaceholder(t *testing.T) {
	// 历史模板存在渲染器不认识的占位符(如 TendisCache-3.2 的 {{masterauth}}),
	// 安装路径一直是原样写入, 渲染器不能改这个行为
	got := mustRender(t, "masterauth {{masterauth}}\n", RedisConfRenderParams{Port: 30000})
	if got != "masterauth {{masterauth}}\n" {
		t.Errorf("rendered = %q, want placeholder kept as-is", got)
	}
	// 但重建配置的调用方必须能识别出来并拒绝写入
	if err := CheckUnresolvedPlaceholder(got); err == nil {
		t.Error("CheckUnresolvedPlaceholder should reject leftover placeholder")
	}
}

func TestResolveSkipsRocksValuesForNonTendisplus(t *testing.T) {
	// rocks 取值要读本机内存, cache/tendisSSD 的模板用不到这两项, 不该为此去探测系统
	for _, dbType := range []string{
		"TwemproxyRedisInstance", "PredixyRedisCluster", "TwemproxyTendisSSDInstance",
	} {
		values, err := RedisConfRenderParams{Port: 30000, DbType: dbType, InstCount: 4}.Resolve()
		if err != nil {
			t.Fatalf("dbType(%s) Resolve err:%v", dbType, err)
		}
		for _, name := range placeholderNames(values) {
			if name == "{{rocks_blockcachemb}}" || name == "{{rocks_write_buffer_size}}" {
				t.Errorf("dbType(%s) should not resolve %s", dbType, name)
			}
		}
	}
}

func TestRenderRedisConfDataTendisplusRocksValues(t *testing.T) {
	tmpl := "rocks.blockcachemb {{rocks_blockcachemb}}\nrocks.write_buffer_size {{rocks_write_buffer_size}}\n"
	for _, dbType := range []string{"PredixyTendisplusCluster", "TwemproxyTendisplusInstance"} {
		got := mustRender(t, tmpl, RedisConfRenderParams{Port: 30000, DbType: dbType, InstCount: 4})
		if err := CheckUnresolvedPlaceholder(got); err != nil {
			t.Fatalf("dbType(%s) rocks placeholder left unresolved:%v", dbType, err)
		}
		for _, line := range strings.Split(strings.TrimSpace(got), "\n") {
			fields := strings.Fields(line)
			if len(fields) != 2 {
				t.Fatalf("dbType(%s) unexpected line %q", dbType, line)
			}
			if _, err := strconv.ParseUint(fields[1], 10, 64); err != nil {
				t.Errorf("dbType(%s) %s value %q not a number", dbType, fields[0], fields[1])
			}
		}
	}
}

func TestCheckUnresolvedPlaceholder(t *testing.T) {
	if err := CheckUnresolvedPlaceholder("port 30000\ndir /data/redis/30000/data\n"); err != nil {
		t.Errorf("clean conf rejected:%v", err)
	}
	if err := CheckUnresolvedPlaceholder(""); err != nil {
		t.Errorf("empty conf rejected:%v", err)
	}

	// 报错只带占位符本身, 不能把配置原文(含密码)抄进日志
	err := CheckUnresolvedPlaceholder("port 30000\nmaxmemory {{maxmemory}}\nrequirepass topsecretpass\n")
	if err == nil {
		t.Fatal("expected unresolved placeholder error")
	}
	if !strings.Contains(err.Error(), "{{maxmemory}}") {
		t.Errorf("err should name the placeholder, got:%v", err)
	}
	if strings.Contains(err.Error(), "topsecretpass") {
		t.Errorf("err leaked conf content:%v", err)
	}
}

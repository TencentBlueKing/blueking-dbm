package atomredis

import (
	"strings"
	"testing"
)

func TestDiffRedisConfDirectives(t *testing.T) {
	oldConf := strings.Join([]string{
		"port 30000",
		"slave-lazy-flush yes",
		"maxmemory 100",
		"io-threads 2",
	}, "\n") + "\n"
	newConf := strings.Join([]string{
		"maxmemory 200",
		"port 30000",
		"replica-lazy-flush yes",
		"disable-thp yes",
	}, "\n") + "\n"
	got := diffRedisConfDirectives(oldConf, newConf)

	// 改名要归成一条, 而不是拆成一加一减淹没真正的增删
	if !strings.Contains(got, "[renamed] 1 item(s)") {
		t.Errorf("rename not grouped\ngot:\n%s", got)
	}
	if !strings.Contains(got, "  slave-lazy-flush yes => replica-lazy-flush yes") {
		t.Errorf("rename pair not reported\ngot:\n%s", got)
	}
	if strings.Contains(got, "  replica-lazy-flush yes\n") {
		t.Errorf("renamed directive should not also appear as added\ngot:\n%s", got)
	}
	if !strings.Contains(got, "[value changed] 1 item(s)") ||
		!strings.Contains(got, "  maxmemory: 100 => 200") {
		t.Errorf("value change not reported\ngot:\n%s", got)
	}
	if !strings.Contains(got, "[added by target version] 1 item(s)") ||
		!strings.Contains(got, "  disable-thp yes") {
		t.Errorf("added directive not reported\ngot:\n%s", got)
	}
	if !strings.Contains(got, "[dropped by target version] 1 item(s)") ||
		!strings.Contains(got, "  io-threads 2") {
		t.Errorf("dropped directive not reported\ngot:\n%s", got)
	}

	// 仅顺序不同不应产生噪音
	if !strings.Contains(diffRedisConfDirectives("a 1\nb 2\n", "b 2\na 1\n"), "no directive level change") {
		t.Error("reordering should not be reported as a change")
	}
}

func TestDiffRedisConfDirectivesIgnoresQuotingOnly(t *testing.T) {
	// config rewrite 会给字符串取值加引号, 我们按 dbconfig 原样渲染;
	// 这种纯写法差异不是变更, 不该刷屏
	oldConf := strings.Join([]string{
		"dir \"/data/redis/30000/data\"",
		"dbfilename \"dump.rdb\"",
		"appendfilename \"appendonly.aof\"",
		"logfile \"/data/redis/30000/redis.log\"",
	}, "\n") + "\n"
	newConf := strings.Join([]string{
		"dir /data/redis/30000/data",
		"dbfilename dump.rdb",
		"appendfilename appendonly.aof",
		"logfile /data/redis/30000/redis.log",
	}, "\n") + "\n"

	if got := diffRedisConfDirectives(oldConf, newConf); !strings.Contains(got, "no directive level change") {
		t.Errorf("quote-only difference reported as change\ngot:\n%s", got)
	}
	// 引号里的内容真变了还是要报出来, 且展示时两边都不带引号
	got := diffRedisConfDirectives("dbfilename \"dump.rdb\"\n", "dbfilename other.rdb\n")
	if !strings.Contains(got, "dbfilename: dump.rdb => other.rdb") {
		t.Errorf("real value change should be shown unquoted\ngot:\n%s", got)
	}
	// 空值仍要看得出来
	got = diffRedisConfDirectives("port 30000\n", "port 30000\naof_rewrite_cpulist \"\"\n")
	if !strings.Contains(got, "aof_rewrite_cpulist \"\"") {
		t.Errorf("empty value should stay visible as \"\"\ngot:\n%s", got)
	}
}

func TestConfDirectivesEqual(t *testing.T) {
	live := liveConfAfterConfigRewrite
	// 重排 + 加引号仍等价
	reordered := strings.Join([]string{
		"replicaof 1.1.1.2 30000",
		`requirepass "xxxxpasswd"`,
		"port 30000",
		`dir "/data1/redis/30000/data"`,
		"bind 1.1.1.1",
		`masterauth "xxxxpasswd"`,
		"logfile /data1/redis/30000/redis.log",
		"databases 2",
		"maxmemory 8589934592",
		"appendonly no",
		"slave-lazy-flush yes",
		"rename-command config confxx",
		"rename-command flushdb cleandb",
		"rename-command flushall cleanall",
		"save 3600 1",
		"save 300 100",
		"client-output-buffer-limit normal 256mb 512mb 300",
		"client-output-buffer-limit slave 2048mb 2048mb 300",
	}, "\n") + "\n"
	if !confDirectivesEqual(live, reordered) {
		t.Error("reordered/quoted conf should equal the rewrite form")
	}
	if !confDirectivesEqual(live, live) {
		t.Error("identical conf should equal")
	}
	if confDirectivesEqual(live, strings.Replace(live, "maxmemory 8589934592", "maxmemory 1", 1)) {
		t.Error("value change should not equal")
	}
	if confDirectivesEqual("port 30000\n", "port 30000\ntimeout 60\n") {
		t.Error("added directive should not equal")
	}
}

func TestConfDirectivesEqualToleratesRewriteNormalization(t *testing.T) {
	// config rewrite 会把 256mb 折算成字节数、把布尔归一成 yes/no: 纯写法差异不算变更,
	// 否则每次 refresh 都会误判有差异而多写一次文件
	if !confDirectivesEqual("maxmemory 268435456\nappendonly yes\n", "maxmemory 256mb\nappendonly 1\n") {
		t.Error("rewrite normalization should not count as a change")
	}
	// 凭据类指令不做归一化: 大小写不同就是不同
	if confDirectivesEqual("requirepass Abc\n", "requirepass abc\n") {
		t.Error("password compare must stay strict")
	}
	// 长得像内存单位的密码也不能被折算成字节数
	if confDirectivesEqual("requirepass 1k\n", "requirepass 1024\n") {
		t.Error("password must not be treated as a memory size")
	}
	if !confDirectivesEqual("slave-read-only yes\n", "replica-read-only yes\n") {
		t.Error("alias pair should equal")
	}
	if confDirectivesEqual("slave-read-only yes\n", "replica-read-only no\n") {
		t.Error("alias pair with different values should not equal")
	}
}

func TestDiffRedisConfDirectivesMasksSecrets(t *testing.T) {
	oldConf := strings.Join([]string{
		"requirepass \"oldsecretpass\"",
		"masterauth \"oldsecretpass\"",
		"user default on sanitize-payload #2b5136ae19bf035d763608129cad3f27 ~* &* +@all",
	}, "\n") + "\n"
	newConf := "requirepass newsecretpass\nmasteruser someuser\n"

	got := diffRedisConfDirectives(oldConf, newConf)
	for _, secret := range []string{"oldsecretpass", "newsecretpass", "someuser",
		"2b5136ae19bf035d763608129cad3f27"} {
		if strings.Contains(got, secret) {
			t.Errorf("secret %q leaked into diff\ngot:\n%s", secret, got)
		}
	}
	// 打码之后仍要能看出这些项发生了什么
	if !strings.Contains(got, "requirepass: <masked> => <masked>") {
		t.Errorf("requirepass change not reported\ngot:\n%s", got)
	}
	if !strings.Contains(got, "#<masked>") || !strings.Contains(got, "+@all") {
		t.Errorf("acl line should keep its non-secret part\ngot:\n%s", got)
	}
}

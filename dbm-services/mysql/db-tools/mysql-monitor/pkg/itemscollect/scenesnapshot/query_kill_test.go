package scenesnapshot

import (
	"database/sql"
	"testing"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg/monitoriteminterface"

	"github.com/go-viper/mapstructure/v2"
)

func newProcess(id int64, user, host, db, command string, t int64, state, info string) *mysqlProcess {
	return &mysqlProcess{
		Id:      sql.NullInt64{Int64: id, Valid: true},
		User:    sql.NullString{String: user, Valid: true},
		Host:    sql.NullString{String: host, Valid: true},
		Db:      sql.NullString{String: db, Valid: true},
		Command: sql.NullString{String: command, Valid: true},
		Time:    sql.NullInt64{Int64: t, Valid: true},
		State:   sql.NullString{String: state, Valid: true},
		Info:    sql.NullString{String: info, Valid: true},
	}
}

func TestQueryKillRulePrepare(t *testing.T) {
	// 没有任何匹配条件的规则必须被拒绝
	r := &QueryKillRuleDef{}
	if err := r.prepare(0); err == nil {
		t.Fatal("rule without any condition should be invalid")
	}

	r = &QueryKillRuleDef{MatchCommand: " Sleep ", TimeGreaterThan: 100}
	if err := r.prepare(1); err != nil {
		t.Fatal(err)
	}
	if r.Action != QueryKillActionKill {
		t.Fatalf("default action should be kill, got %s", r.Action)
	}
	if r.RuleName != "query-kill-rule-1" {
		t.Fatalf("unexpected default rule name: %s", r.RuleName)
	}
	if r.MatchCommand != "Sleep" {
		t.Fatalf("match_command should be trimmed, got %q", r.MatchCommand)
	}

	r = &QueryKillRuleDef{MatchCommand: "Sleep", Action: "reboot"}
	if err := r.prepare(2); err == nil {
		t.Fatal("unsupported action should be invalid")
	}

	// 只有 match_query 是正则, 非法正则要报错
	r = &QueryKillRuleDef{MatchQuery: "(("}
	if err := r.prepare(3); err == nil {
		t.Fatal("bad match_query pattern should be invalid")
	}

	// 其他字段不当正则处理, 特殊字符也是合法的精确匹配值
	r = &QueryKillRuleDef{MatchDB: "(("}
	if err := r.prepare(4); err != nil {
		t.Fatal(err)
	}
}

func TestQueryKillRuleMatch(t *testing.T) {
	r := &QueryKillRuleDef{
		MatchCommand:    "Query",
		MatchState:      "Sending Data",
		MatchDB:         "test_db",
		MatchHost:       "1.1.1.1",
		MatchQuery:      `^select`,
		TimeGreaterThan: 10,
		Action:          QueryKillActionKill,
	}
	if err := r.prepare(0); err != nil {
		t.Fatal(err)
	}

	for _, c := range []struct {
		p      *mysqlProcess
		expect bool
	}{
		// match_* 精确匹配忽略大小写
		{newProcess(1, "u1", "1.1.1.1:100", "test_db", "Query", 11, "Sending data", "select 1"), true},
		// match_query 大小写敏感, SELECT 不命中 ^select
		{newProcess(11, "u1", "1.1.1.1:100", "test_db", "Query", 11, "Sending data", "SELECT 1"), false},
		// time 不满足
		{newProcess(2, "u1", "1.1.1.1:100", "test_db", "Query", 10, "Sending data", "select 1"), false},
		// db 只是前缀, 精确匹配不命中
		{newProcess(3, "u1", "1.1.1.1:100", "test_db_2", "Query", 100, "Sending data", "select 1"), false},
		// host ip 不同
		{newProcess(4, "u1", "1.1.1.9:100", "test_db", "Query", 100, "Sending data", "select 1"), false},
		// command 不同
		{newProcess(5, "u1", "1.1.1.1:100", "test_db", "Sleep", 100, "Sending data", "select 1"), false},
		// state 只是包含, 精确匹配不命中
		{newProcess(6, "u1", "1.1.1.1:100", "test_db", "Query", 100, "Sending data to client", "select 1"), false},
		// match_query 正则不命中
		{newProcess(7, "u1", "1.1.1.1:100", "test_db", "Query", 100, "Sending data", "update t set a=1"), false},
	} {
		match, err := r.match(c.p)
		if err != nil {
			t.Fatal(err)
		}
		if match != c.expect {
			t.Fatalf("process %d expect %v, got %v", c.p.Id.Int64, c.expect, match)
		}
	}
}

func TestMatchQueryCaseSensitive(t *testing.T) {
	// 默认大小写敏感
	r := &QueryKillRuleDef{MatchQuery: `^select sleep`}
	if err := r.prepare(0); err != nil {
		t.Fatal(err)
	}
	for _, c := range []struct {
		query  string
		expect bool
	}{
		{"select sleep(10)", true},
		{"SELECT SLEEP(10)", false},
		{"Select Sleep(10)", false},
	} {
		p := newProcess(1, "u1", "1.1.1.1:100", "db1", "Query", 100, "", c.query)
		match, err := r.match(p)
		if err != nil {
			t.Fatal(err)
		}
		if match != c.expect {
			t.Fatalf("case sensitive: query %q expect %v, got %v", c.query, c.expect, match)
		}
	}

	// 用户自己加 (?i) 就忽略大小写
	r = &QueryKillRuleDef{MatchQuery: `(?i)^select sleep`}
	if err := r.prepare(1); err != nil {
		t.Fatal(err)
	}
	for _, query := range []string{"select sleep(10)", "SELECT SLEEP(10)", "Select Sleep(10)"} {
		p := newProcess(1, "u1", "1.1.1.1:100", "db1", "Query", 100, "", query)
		match, err := r.match(p)
		if err != nil {
			t.Fatal(err)
		}
		if !match {
			t.Fatalf("(?i) should match query %q", query)
		}
	}
}

func TestMatchHostPatterns(t *testing.T) {
	r := &QueryKillRuleDef{MatchHost: "1.1.1.1, 1.1.1.2 ,1.2.%"}
	if err := r.prepare(0); err != nil {
		t.Fatal(err)
	}
	if len(r.hostPatterns) != 3 {
		t.Fatalf("expect 3 host patterns, got %d", len(r.hostPatterns))
	}

	for _, c := range []struct {
		host   string
		expect bool
	}{
		{"1.1.1.1:100", true},
		{"1.1.1.2:100", true},
		{"1.2.3.4:100", true},   // 1.2.% 通配
		{"1.2.33.44:100", true}, // 1.2.% 通配
		{"1.1.1.3:100", false},  // 不在列表里
		{"1.20.1.1:100", false}, // 1.2.% 要求第二段就是 2
		{"1.1.2.3:100", false},  // 中间出现 1.2. 也不算命中, 必须从头匹配
		{"1.1.1.10:100", false}, // 1.1.1.1 是精确匹配, 不是前缀
	} {
		p := newProcess(1, "u1", c.host, "db1", "Query", 100, "", "")
		match, err := r.match(p)
		if err != nil {
			t.Fatal(err)
		}
		if match != c.expect {
			t.Fatalf("host %s expect %v, got %v", c.host, c.expect, match)
		}
	}

	// . 必须按字面处理, 不能当成正则的任意字符
	r = &QueryKillRuleDef{MatchHost: "1.1.1.%"}
	if err := r.prepare(1); err != nil {
		t.Fatal(err)
	}
	if r.matchHost("1x1x1x1") {
		t.Fatal("dot should be escaped")
	}

	// 配了 match_host 但解析不出有效项, 规则必须被拒绝
	r = &QueryKillRuleDef{MatchHost: " , , "}
	if err := r.prepare(2); err == nil {
		t.Fatal("match_host without valid item should be invalid")
	}
}

func TestHostIP(t *testing.T) {
	for _, c := range []struct {
		host   string
		expect string
	}{
		{"1.1.1.1:3306", "1.1.1.1"},
		{"localhost", "localhost"},
		{"", ""},
	} {
		if got := hostIP(c.host); got != c.expect {
			t.Fatalf("hostIP(%q) expect %q, got %q", c.host, c.expect, got)
		}
	}
}

func TestSkipProcess(t *testing.T) {
	if !skipProcess(newProcess(10, "u1", "", "", "Query", 100, "", ""), 10) {
		t.Fatal("should skip self connection")
	}
	if !skipProcess(newProcess(11, "system user", "", "", "Connect", 100, "", ""), 10) {
		t.Fatal("should skip system user")
	}
	if !skipProcess(newProcess(12, "repl", "", "", "Binlog Dump GTID", 100, "", ""), 10) {
		t.Fatal("should skip binlog dump")
	}
	if skipProcess(newProcess(13, "u1", "", "", "Query", 100, "", ""), 10) {
		t.Fatal("should not skip normal process")
	}
}

func TestDecodeQueryKillRulesOption(t *testing.T) {
	// 模拟 items-config.yaml 里的 options 结构
	opts := monitoriteminterface.ItemOptions{
		"query_kill_enable":        true,
		"query_kill_max_per_round": 20,
		"query_kill_rules": []interface{}{
			map[interface{}]interface{}{
				"rule_name":     "long-sleep",
				"match_command": "Sleep",
				"time_gt":       3600,
				"action":        "kill",
			},
		},
	}

	var c Checker
	if err := mapstructure.Decode(opts, &c); err != nil {
		t.Fatal(err)
	}
	if !c.QueryKillEnable {
		t.Fatal("query kill should be enabled")
	}
	if c.QueryKillMaxPerRound != 20 {
		t.Fatalf("expect max per round 20, got %d", c.QueryKillMaxPerRound)
	}
	if len(c.QueryKillRules) != 1 {
		t.Fatalf("expect 1 rule, got %d", len(c.QueryKillRules))
	}
	rule := c.QueryKillRules[0]
	if rule.RuleName != "long-sleep" || rule.MatchCommand != "Sleep" ||
		rule.TimeGreaterThan != 3600 || rule.Action != QueryKillActionKill {
		t.Fatalf("unexpected rule: %+v", rule)
	}

	c.initQueryKillRules()
	if len(c.queryKillRules) != 1 {
		t.Fatalf("expect 1 valid rule, got %d", len(c.queryKillRules))
	}
}

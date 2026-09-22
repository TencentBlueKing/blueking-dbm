package scenesnapshot

/*
query-kill 在某些异常情况下, 快速 kill 掉异常请求
规则通过监控项 scene-snapshot 的个性化 options 下发, 每个规则支持:

	rule_name     : 规则名, 只用于日志, 不填自动生成
	match_db      : db 精确匹配, 忽略大小写
	match_user    : user 精确匹配, 忽略大小写
	match_host    : 来源 ip, 忽略大小写. processlist 里的 host 是 ip:port, 只比较 ip 部分
	                支持逗号分隔多个, % 通配, 命中任一即可, 比如 1.1.1.1,1.1.1.2,1.2.%
	match_command : command 精确匹配, 忽略大小写, 比如 Sleep
	match_state   : state 精确匹配, 忽略大小写, 比如 Sending data
	match_query   : 执行的 sql 匹配, 正则, 大小写敏感. 需要忽略大小写用 (?i) 前缀, 比如 (?i)^select sleep
	time_gt       : Time 大于 N 秒
	action        : kill / print, 默认 kill. print 只打印不执行

上面的匹配条件是 and 关系, 全部为空的规则会被丢弃, 避免误杀.
多个规则之间是 or 关系, 按配置顺序依次处理.
规则直接以列表形式配在 items-config.yaml 的 options.query_kill_rules 下.

options.query_kill_max_per_round 是全局上限: 单轮所有规则合计最多处理 N 个连接, 0 表示不限制.
*/

import (
	"fmt"
	"log/slog"
	"regexp"
	"strings"

	"github.com/dlclark/regexp2"

	"dbm-services/mysql/db-tools/mysql-monitor/pkg"
	"dbm-services/mysql/db-tools/mysql-monitor/pkg/internal/cst"
)

// query kill 支持的动作
const (
	// QueryKillActionPrint 只记录, 不执行 kill
	QueryKillActionPrint = "print"
	// QueryKillActionKill kill 连接
	QueryKillActionKill = "kill"
)

// 这些连接永远不处理, 比较时忽略大小写
var queryKillIgnoreCommands = []string{
	"binlog dump",
	"binlog dump gtid",
	"daemon",
	"connect",
}
var queryKillIgnoreUsers = []string{
	cst.SystemUser, // 复制线程
	"event_scheduler",
}

// QueryKillRuleDef query kill 规则定义
type QueryKillRuleDef struct {
	// RuleName 规则名, 用于日志和自定义指标维度
	RuleName string `mapstructure:"rule_name" yaml:"rule_name" json:"rule_name"`
	// MatchDB db 精确匹配, 忽略大小写
	MatchDB string `mapstructure:"match_db" yaml:"match_db" json:"match_db"`
	// MatchUser user 精确匹配, 忽略大小写
	MatchUser string `mapstructure:"match_user" yaml:"match_user" json:"match_user"`
	// MatchHost 来源 ip, 只比较 ip 部分. 逗号分隔多个, % 通配, 命中任一即可
	// 比如 1.1.1.1,1.1.1.2,1.2.%
	MatchHost string `mapstructure:"match_host" yaml:"match_host" json:"match_host"`
	// MatchCommand command 精确匹配, 忽略大小写, 比如 Sleep
	MatchCommand string `mapstructure:"match_command" yaml:"match_command" json:"match_command"`
	// MatchState state 精确匹配, 忽略大小写, 比如 Sending data
	MatchState string `mapstructure:"match_state" yaml:"match_state" json:"match_state"`
	// MatchQuery 执行的 sql 正则, 大小写敏感, 需要忽略大小写用 (?i) 前缀
	// example: '^select.*select' / '(?i)^select sleep'
	MatchQuery string `mapstructure:"match_query" yaml:"match_query" json:"match_query"`
	// TimeGreaterThan Time 大于 N 秒
	TimeGreaterThan int64 `mapstructure:"time_gt" yaml:"time_gt" json:"time_gt"`
	// Action kill / print, 默认 kill
	Action string `mapstructure:"action" yaml:"action" json:"action"`

	// 只有 match_query 用正则
	reQuery *regexp2.Regexp
	// match_host 拆分后的多个 host 条件
	hostPatterns []*hostPattern
}

// hostPattern match_host 拆分出的单个 host 条件
type hostPattern struct {
	// exact 不含 % 时的字面值, 精确比较
	exact string
	// re 含 % 时编译出的正则
	re *regexp.Regexp
}

func (h *hostPattern) match(host string) bool {
	if h.re != nil {
		return h.re.MatchString(host)
	}
	return strings.EqualFold(h.exact, host)
}

// parseHostPatterns 解析 match_host, 逗号分隔, % 通配
func parseHostPatterns(matchHost string) ([]*hostPattern, error) {
	var res []*hostPattern

	for _, ele := range strings.Split(matchHost, ",") {
		ele = strings.TrimSpace(ele)
		if ele == "" {
			continue
		}

		if !strings.Contains(ele, "%") {
			res = append(res, &hostPattern{exact: ele})
			continue
		}

		// 只有 % 是通配符, 其余字符按字面处理, 比如 ip 里的 . 不能当成正则的任意字符
		parts := strings.Split(ele, "%")
		for i := range parts {
			parts[i] = regexp.QuoteMeta(parts[i])
		}
		re, err := regexp.Compile("^" + strings.Join(parts, ".*") + "$")
		if err != nil {
			return nil, fmt.Errorf("compile host pattern %s: %w", ele, err)
		}
		res = append(res, &hostPattern{re: re})
	}

	return res, nil
}

// prepare 校验规则, 编译正则
func (r *QueryKillRuleDef) prepare(idx int) error {
	if r.RuleName == "" {
		r.RuleName = fmt.Sprintf("query-kill-rule-%d", idx)
	}

	r.Action = strings.ToLower(strings.TrimSpace(r.Action))
	switch r.Action {
	case "":
		r.Action = QueryKillActionKill
	case QueryKillActionPrint, QueryKillActionKill:
	default:
		return fmt.Errorf("unsupported action: %s", r.Action)
	}

	// 精确匹配的字段去掉首尾空格, 比较时用 strings.EqualFold 忽略大小写
	r.MatchDB = strings.TrimSpace(r.MatchDB)
	r.MatchUser = strings.TrimSpace(r.MatchUser)
	r.MatchHost = strings.TrimSpace(r.MatchHost)
	r.MatchCommand = strings.TrimSpace(r.MatchCommand)
	r.MatchState = strings.TrimSpace(r.MatchState)

	// 所有匹配条件都为空的规则会命中全部连接, 丢弃掉
	if r.TimeGreaterThan <= 0 &&
		r.MatchDB == "" && r.MatchUser == "" && r.MatchHost == "" &&
		r.MatchCommand == "" && r.MatchState == "" && r.MatchQuery == "" {
		return fmt.Errorf("no match condition")
	}

	// 只有 match_query 是正则, 默认大小写敏感, 需要忽略大小写自己在正则里加 (?i)
	if r.MatchQuery != "" {
		re, err := regexp2.Compile(r.MatchQuery, regexp2.None)
		if err != nil {
			return fmt.Errorf("compile match_query %s: %w", r.MatchQuery, err)
		}
		r.reQuery = re
	}

	if r.MatchHost != "" {
		hostPatterns, err := parseHostPatterns(r.MatchHost)
		if err != nil {
			return err
		}
		// 配了 match_host 但一个有效项都解析不出来, 比如 ",,"
		// 这种如果当成没配, 会让规则的命中范围变大, 所以直接报错丢弃规则
		if len(hostPatterns) == 0 {
			return fmt.Errorf("invalid match_host: %s", r.MatchHost)
		}
		r.hostPatterns = hostPatterns
	}

	return nil
}

// match 规则和连接是否匹配, 所有条件 and 关系
func (r *QueryKillRuleDef) match(p *mysqlProcess) (bool, error) {
	if r.TimeGreaterThan > 0 && p.Time.Int64 <= r.TimeGreaterThan {
		return false, nil
	}

	for _, ele := range []struct {
		expect string
		value  string
	}{
		{r.MatchDB, p.Db.String},
		{r.MatchUser, p.User.String},
		{r.MatchCommand, p.Command.String},
		{r.MatchState, p.State.String},
	} {
		if ele.expect == "" {
			continue
		}
		if !strings.EqualFold(ele.expect, strings.TrimSpace(ele.value)) {
			return false, nil
		}
	}

	// 多个 host 之间是 or 关系
	if len(r.hostPatterns) > 0 && !r.matchHost(hostIP(p.Host.String)) {
		return false, nil
	}

	if r.reQuery != nil {
		match, err := r.reQuery.MatchString(p.Info.String)
		if err != nil {
			return false, err
		}
		if !match {
			return false, nil
		}
	}

	return true, nil
}

// matchHost 命中任一 host 条件即可
func (r *QueryKillRuleDef) matchHost(host string) bool {
	host = strings.TrimSpace(host)
	for _, ele := range r.hostPatterns {
		if ele.match(host) {
			return true
		}
	}

	return false
}

// hostIP processlist 里的 host 是 ip:port, 只取 ip 部分
// localhost 这种没有 port 的原样返回
func hostIP(host string) string {
	if idx := strings.LastIndex(host, ":"); idx >= 0 {
		return host[:idx]
	}
	return host
}

// queryKillProcesslist 按规则处理 processlist 快照里的异常连接
func (c *Checker) queryKillProcesslist(processList []*mysqlProcess) {
	if !c.QueryKillEnable || len(c.queryKillRules) == 0 {
		return
	}

	// 不能 kill 自己
	selfID := currentConnectionID(c.db)

	killed := 0
	for _, p := range processList {
		// 全局上限, 所有规则合计
		if c.QueryKillMaxPerRound > 0 && killed >= c.QueryKillMaxPerRound {
			slog.Info(
				"query kill reach max kills per round",
				slog.Int("query_kill_max_per_round", c.QueryKillMaxPerRound),
			)
			break
		}

		if skipProcess(p, selfID) {
			continue
		}

		// 多个规则 or 关系, 命中第一条就处理
		rule := c.matchRule(p)
		if rule == nil {
			continue
		}

		var killErr string
		if rule.Action != QueryKillActionPrint {
			if err := killProcess(c.db, p.Id.Int64); err != nil {
				killErr = err.Error()
			}
		}
		killed++

		slog.Info(
			"query kill hit process",
			slog.String("rule", rule.RuleName), slog.String("action", rule.Action),
			slog.Int64("id", p.Id.Int64), slog.String("user", p.User.String),
			slog.String("host", p.Host.String), slog.String("db", p.Db.String),
			slog.String("command", p.Command.String), slog.Int64("time", p.Time.Int64),
			slog.String("state", p.State.String), slog.String("info", p.Info.String),
			slog.String("kill error", killErr),
		)
	}

	slog.Info("query kill finish", slog.Int("killed", killed))
}

// matchRule 返回命中的第一条规则, 没有命中返回 nil
func (c *Checker) matchRule(p *mysqlProcess) *QueryKillRuleDef {
	for _, rule := range c.queryKillRules {
		match, err := rule.match(p)
		if err != nil {
			slog.Error(
				"query kill match process",
				slog.String("rule", rule.RuleName), slog.String("error", err.Error()),
			)
			continue
		}
		if match {
			return rule
		}
	}

	return nil
}

// skipProcess 无论什么规则都不处理的连接
func skipProcess(p *mysqlProcess, selfID int64) bool {
	if !p.Id.Valid || (selfID > 0 && p.Id.Int64 == selfID) {
		return true
	}

	user := strings.TrimSpace(p.User.String)
	for _, ele := range queryKillIgnoreUsers {
		if strings.EqualFold(user, ele) {
			return true
		}
	}

	command := strings.TrimSpace(p.Command.String)
	for _, ele := range queryKillIgnoreCommands {
		if strings.EqualFold(command, ele) {
			return true
		}
	}

	return false
}

func currentConnectionID(db *pkg.MySQLMonitorDBH) int64 {
	var connID int64
	if err := db.QueryRowx(`SELECT CONNECTION_ID()`).Scan(&connID); err != nil {
		slog.Error("query kill get connection id", slog.String("error", err.Error()))
		return 0
	}
	return connID
}

func killProcess(db *pkg.MySQLMonitorDBH, id int64) error {
	killSQL := fmt.Sprintf(`KILL %d`, id)

	if _, err := db.Exec(killSQL); err != nil {
		// 连接可能已经自己结束了, 不影响其他连接的处理
		slog.Warn(
			"query kill execute",
			slog.String("sql", killSQL), slog.String("error", err.Error()),
		)
		return err
	}

	slog.Info("query kill execute", slog.String("sql", killSQL))
	return nil
}

// initQueryKillRules 校验规则, 非法规则丢弃, 不影响快照采集
func (c *Checker) initQueryKillRules() {
	if !c.QueryKillEnable {
		if len(c.QueryKillRules) > 0 {
			slog.Info(name, slog.String("msg", "query kill disabled"))
		}
		return
	}

	for i, rule := range c.QueryKillRules {
		if err := rule.prepare(i); err != nil {
			slog.Error(
				name,
				slog.String("msg", "invalid query kill rule"),
				slog.String("rule", rule.RuleName), slog.String("error", err.Error()),
			)
			continue
		}
		c.queryKillRules = append(c.queryKillRules, rule)
	}

	slog.Info(
		name,
		slog.String("msg", "query kill enabled"), slog.Int("rules", len(c.queryKillRules)),
	)
}

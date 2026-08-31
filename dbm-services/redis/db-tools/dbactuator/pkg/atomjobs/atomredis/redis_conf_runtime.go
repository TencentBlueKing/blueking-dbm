package atomredis

import (
	"fmt"
	"strconv"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
)

// redisConfRuntime 运行态配置读写. *myredis.RedisClient 满足此接口, 测试用假客户端也满足.
type redisConfRuntime interface {
	ConfigGet(confName string) (map[string]string, error)
	ConfigSet(confName string, val string) (string, error)
}

// confSetKind 一条渲染指令在 config_set 模式下的处置
type confSetKind int

const (
	// confSetSkip 永远不 SET: 本地取得 / 拓扑 / dbmon 管的项
	confSetSkip confSetKind = iota
	// confSetApply 可 SET, 值不同才发
	confSetApply
)

// confSetNeverNames 这份任务不该改的项: 密码只走 port_target_passwords,
// replicaof/slaveof 走独立建同步原子任务, maxmemory 由 dbmon 管.
// databases 运行态 CONFIG SET 会失败, 只允许主从版通过重建 redis.conf + 重启改.
var confSetNeverNames = map[string]bool{
	"requirepass": true,
	"masterauth":  true,
	"masteruser":  true,
	"user":        true,
	"replicaof":   true,
	"slaveof":     true,
	"maxmemory":   true,
	"databases":   true,
}

func classifyConfSetKind(name string) confSetKind {
	if confSetNeverNames[name] {
		return confSetSkip
	}
	return confSetApply
}

func joinDirectiveValues(values []string) string {
	parts := make([]string, 0, len(values))
	for _, v := range values {
		parts = append(parts, unquoteConfValue(strings.TrimSpace(v)))
	}
	return strings.Join(parts, " ")
}

// confRuntimeLookup 从 CONFIG GET 的返回里取出取值. 空 map 表示这条指令运行态查不到.
func confRuntimeLookup(got map[string]string, name string) (value string, found bool) {
	if len(got) == 0 {
		return "", false
	}
	for k, v := range got {
		if strings.EqualFold(k, name) {
			return strings.TrimSpace(v), true
		}
	}
	// CONFIG GET 有时用指令名当 key, 有时把整段当唯一 value
	if len(got) == 1 {
		for _, v := range got {
			return strings.TrimSpace(v), true
		}
	}
	return "", false
}

// sameConfRuntimeValueFor 按指令名比较. 路径类指令还要走 samePathValue, 容忍软链别名.
func sameConfRuntimeValueFor(name, rendered, runtime string) bool {
	if sameConfRuntimeValue(rendered, runtime) {
		return true
	}
	switch name {
	case "dir", "pidfile", "logfile", "unixsocket":
		return samePathValue(rendered, runtime)
	}
	return false
}

// sameConfRuntimeValue 比较渲染取值和 CONFIG GET 取值.
//
// 容忍: 引号、大小写、yes/no vs 1/0、redis 内存单位 (256mb == 268435456).
func sameConfRuntimeValue(rendered, runtime string) bool {
	a := unquoteConfValue(strings.TrimSpace(rendered))
	b := unquoteConfValue(strings.TrimSpace(runtime))
	if a == b {
		return true
	}
	if a == "" && (b == "" || b == `""`) {
		return true
	}
	if b == "" && (a == "" || a == `""`) {
		return true
	}
	if confBoolEqual(a, b) {
		return true
	}
	ta := strings.Fields(a)
	tb := strings.Fields(b)
	if len(ta) != len(tb) {
		return false
	}
	if len(ta) == 0 {
		return true
	}
	for i := range ta {
		if !sameConfRuntimeToken(ta[i], tb[i]) {
			return false
		}
	}
	return true
}

func confBoolEqual(a, b string) bool {
	return (confTruthy(a) && confTruthy(b)) || (confFalsy(a) && confFalsy(b))
}

func confTruthy(s string) bool {
	switch strings.ToLower(s) {
	case "yes", "true", "on", "1":
		return true
	}
	return false
}

func confFalsy(s string) bool {
	switch strings.ToLower(s) {
	case "no", "false", "off", "0":
		return true
	}
	return false
}

func sameConfRuntimeToken(a, b string) bool {
	if strings.EqualFold(a, b) {
		return true
	}
	if confBoolEqual(a, b) {
		return true
	}
	if redisMemHasUnit(a) || redisMemHasUnit(b) {
		ba, oka := parseRedisMemBytes(a)
		bb, okb := parseRedisMemBytes(b)
		return oka && okb && ba == bb
	}
	return false
}

func redisMemHasUnit(s string) bool {
	s = strings.ToLower(strings.TrimSpace(s))
	for _, suffix := range []string{"tb", "gb", "mb", "kb", "t", "g", "m", "k", "b"} {
		if strings.HasSuffix(s, suffix) && len(s) > len(suffix) {
			if _, err := strconv.ParseFloat(s[:len(s)-len(suffix)], 64); err == nil {
				return true
			}
		}
	}
	return false
}

// parseRedisMemBytes 按 redis 的内存单位解析: 1kb=1024, 1mb=1024^2. 纯数字当字节.
func parseRedisMemBytes(s string) (uint64, bool) {
	s = strings.ToLower(strings.TrimSpace(s))
	if s == "" {
		return 0, false
	}
	if n, err := strconv.ParseUint(s, 10, 64); err == nil {
		return n, true
	}
	type unit struct {
		suffix string
		mul    uint64
	}
	for _, u := range []unit{
		{"tb", 1024 * 1024 * 1024 * 1024},
		{"gb", 1024 * 1024 * 1024},
		{"mb", 1024 * 1024},
		{"kb", 1024},
		{"t", 1024 * 1024 * 1024 * 1024},
		{"g", 1024 * 1024 * 1024},
		{"m", 1024 * 1024},
		{"k", 1024},
		{"b", 1},
	} {
		if !strings.HasSuffix(s, u.suffix) {
			continue
		}
		num := strings.TrimSpace(s[:len(s)-len(u.suffix)])
		f, err := strconv.ParseFloat(num, 64)
		if err != nil {
			return 0, false
		}
		return uint64(f * float64(u.mul)), true
	}
	return 0, false
}

// confRuntimeDiff 渲染结果与运行态的一条差异
type confRuntimeDiff struct {
	Name     string
	Kind     confSetKind
	Rendered string
	Runtime  string
	Found    bool // CONFIG GET 是否查到了这条
}

// inspectConfRuntime 把渲染结果里的每条指令和运行态比一遍.
func inspectConfRuntime(cli redisConfRuntime, confData string) ([]confRuntimeDiff, error) {
	directives := parseRedisConfDirectives(confData)
	names := sortedDirectiveNames(directives)
	diffs := make([]confRuntimeDiff, 0, len(names))
	for _, name := range names {
		rendered := joinDirectiveValues(directives[name])
		kind := classifyConfSetKind(name)
		got, err := cli.ConfigGet(name)
		if err != nil {
			return nil, fmt.Errorf("config get %s failed,err:%v", name, err)
		}
		runtime, found := confRuntimeLookup(got, name)
		if found && sameConfRuntimeValueFor(name, rendered, runtime) {
			continue
		}
		if !found && rendered == "" {
			continue
		}
		diffs = append(diffs, confRuntimeDiff{
			Name: name, Kind: kind, Rendered: rendered, Runtime: runtime, Found: found,
		})
	}
	return diffs, nil
}

// runtimeMatchesPlan 运行态是否已经和渲染结果对齐.
//
// skip 项(密码/主从/maxmemory) 和查不到的项不参与: 前者不是这次刷新该改的,
// 后者 CONFIG SET 也动不了. 可 SET 或必须重启才能改的项有差异, 就还没到位.
func runtimeMatchesPlan(cli redisConfRuntime, confData string) (bool, error) {
	diffs, err := inspectConfRuntime(cli, confData)
	if err != nil {
		return false, err
	}
	for _, d := range diffs {
		if d.Kind == confSetSkip {
			continue
		}
		if !d.Found {
			continue // 查不到的指令无法用运行态证明, 不挡 skip
		}
		return false, nil
	}
	return true, nil
}

// applyConfigSet 按分类把运行态收敛到渲染结果. 不写配置文件.
//
// skip 项有差异只打 warn, 永不 SET.
// 查不到的指令跳过 (CONFIG GET 空, 没法 SET 也没法证伪).
// CONFIG SET 失败原样返回, 并提示改用 restart 模式.
func applyConfigSet(cli redisConfRuntime, confData string, log *logger.Logger) error {
	diffs, err := inspectConfRuntime(cli, confData)
	if err != nil {
		return err
	}
	if len(diffs) == 0 {
		log.Info("config_set: runtime already matches rendered conf")
		return nil
	}
	for _, d := range diffs {
		shownRendered := maskConfValue(d.Name, d.Rendered)
		shownRuntime := maskConfValue(d.Name, d.Runtime)
		switch d.Kind {
		case confSetSkip:
			log.Warn("config_set: skip %s (local/topology/dbmon owned), runtime=%q rendered=%q",
				d.Name, shownRuntime, shownRendered)
		case confSetApply:
			if !d.Found {
				log.Info("config_set: %s not queryable at runtime,skip", d.Name)
				continue
			}
			log.Info("config_set: set %s %q -> %q", d.Name, shownRuntime, shownRendered)
			if _, err = cli.ConfigSet(d.Name, d.Rendered); err != nil {
				return fmt.Errorf("config set %s failed,err:%v, use apply_mode=restart", d.Name, err)
			}
		}
	}
	return nil
}

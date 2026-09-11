package atomredis

import (
	"fmt"
	"sort"
	"strings"
)

// 本文件只负责升级重建配置时的日志 diff, 不参与是否写入的决策.
// 渲染结果按 key 排序, config rewrite 后的旧文件是另一种顺序, 逐行 diff 全是噪音,
// 所以按 "指令 -> 取值集合" 比对, 并归并版本间的配置项改名.

// confNameAliasPairs 同一个配置项在不同版本下的两种叫法 (旧名 -> 新名).
//
// diff 里一条改名会同时表现为 "掉了旧名" + "多了新名", 不归并的话真正的
// 新增默认值和废弃项会被改名噪音淹没.
var confNameAliasPairs = map[string]string{
	"slave-priority":                "replica-priority",
	"slave-read-only":               "replica-read-only",
	"slave-serve-stale-data":        "replica-serve-stale-data",
	"slave-lazy-flush":              "replica-lazy-flush",
	"slave-announce-ip":             "replica-announce-ip",
	"slave-announce-port":           "replica-announce-port",
	"min-slaves-to-write":           "min-replicas-to-write",
	"min-slaves-max-lag":            "min-replicas-max-lag",
	"cluster-slave-no-failover":     "cluster-replica-no-failover",
	"cluster-slave-validity-factor": "cluster-replica-validity-factor",
	"hash-max-ziplist-entries":      "hash-max-listpack-entries",
	"hash-max-ziplist-value":        "hash-max-listpack-value",
	"zset-max-ziplist-entries":      "zset-max-listpack-entries",
	"zset-max-ziplist-value":        "zset-max-listpack-value",
	"list-max-ziplist-size":         "list-max-listpack-size",
	"slowlog-log-slower-than":       "commandlog-execution-slower-than",
	"slowlog-max-len":               "commandlog-slow-execution-max-len",
}

// confNameAliasIndex confNameAliasPairs 的双向索引, diff 里正反都要查
var confNameAliasIndex = func() map[string]string {
	index := make(map[string]string, len(confNameAliasPairs)*2)
	for legacy, current := range confNameAliasPairs {
		index[legacy] = current
		index[current] = legacy
	}
	return index
}()

// sensitiveConfNames 凭据类指令: 比对按原文严格来, 不做大小写/内存单位归一化
var sensitiveConfNames = map[string]bool{
	"requirepass": true,
	"masterauth":  true,
	"masteruser":  true,
	"user":        true,
}

// maskConfValue 打日志前给敏感取值打码, 避免密码进任务日志
func maskConfValue(name, value string) string {
	if value == "" {
		return value
	}
	switch name {
	case "requirepass", "masterauth", "masteruser":
		return "<masked>"
	case "user":
		// ACL 行形如 user default on sanitize-payload #<sha256> ~* &* +@all,
		// 只把凭据 token 打掉, 其余权限描述留着才看得出差异
		fields := strings.Fields(value)
		for i, field := range fields {
			if len(field) > 1 && (field[0] == '#' || field[0] == '>') {
				fields[i] = string(field[0]) + "<masked>"
			}
		}
		return strings.Join(fields, " ")
	}
	return value
}

// joinMaskedValues 把某指令的多个取值拼成一行日志: 打码, 并去掉引号.
//
// 引号不构成差异(见 sameConfValues), 展示时一并去掉, 免得 diff 里
// 一边带引号一边不带, 看着像变更.
func joinMaskedValues(name string, values []string) string {
	shown := make([]string, 0, len(values))
	for _, value := range values {
		display := unquoteConfValue(strings.TrimSpace(value))
		if display == "" {
			display = "\"\"" // 空值保留 "" 的写法, 否则日志里看不出这项有值
		}
		shown = append(shown, maskConfValue(name, display))
	}
	return strings.Join(shown, " | ")
}

// sameConfValues 比较指令的取值集合, 忽略 config rewrite 带来的纯写法差异.
//
// dir "/data/redis/30000/data" 与 dir /data/redis/30000/data 是同一份配置,
// redis 两种写法都认: 我们按 dbconfig 原样渲染(不加引号), 引号是 redis 自己
// rewrite 时补的, 这种纯写法差异不该在 diff 里刷屏.
// rewrite 还会把 yes/no 归一、把 256mb 折算成字节数, 同样不算变更;
// 凭据类指令(见 sensitiveConfNames)除外, 密码按原文严格比.
func sameConfValues(name string, oldValues, newValues []string) bool {
	if len(oldValues) != len(newValues) {
		return false
	}
	for i := range oldValues {
		oldVal := unquoteConfValue(strings.TrimSpace(oldValues[i]))
		newVal := unquoteConfValue(strings.TrimSpace(newValues[i]))
		if oldVal == newVal {
			continue
		}
		if sensitiveConfNames[name] || !sameConfRuntimeValue(oldVal, newVal) {
			return false
		}
	}
	return true
}

// confDirectivesEqual 按指令维度判断两份配置是否等价.
//
// 不比字节: CONFIG REWRITE 会重排、加引号, 重跑任务时旧文件和刚渲染的结果
// 字节上几乎总是不同, 但指令集合相同就该当成已经到位.
func confDirectivesEqual(a, b string) bool {
	oldDirectives := parseRedisConfDirectives(a)
	newDirectives := parseRedisConfDirectives(b)
	handled := make(map[string]bool)
	for _, name := range sortedDirectiveNames(oldDirectives, newDirectives) {
		if handled[name] {
			continue
		}
		alias := confNameAliasIndex[name]
		if alias != "" {
			handled[alias] = true
		}
		handled[name] = true
		if !sameConfValues(name, confValuesWithAlias(oldDirectives, name, alias),
			confValuesWithAlias(newDirectives, name, alias)) {
			return false
		}
	}
	return true
}

// confValuesWithAlias 取指令取值, 本名字没有时回落到版本间别名.
func confValuesWithAlias(directives confDirectives, name, alias string) []string {
	if vals := directives[name]; len(vals) > 0 {
		return vals
	}
	if alias != "" {
		return directives[alias]
	}
	return nil
}

// sortedDirectiveNames 新旧配置里出现过的全部指令名, 排序后返回, 保证日志稳定
func sortedDirectiveNames(directiveSets ...confDirectives) []string {
	names := make([]string, 0)
	seen := make(map[string]bool)
	for _, directives := range directiveSets {
		for name := range directives {
			if !seen[name] {
				seen[name] = true
				names = append(names, name)
			}
		}
	}
	sort.Strings(names)
	return names
}

// diffRedisConfDirectives 按指令维度给出新旧配置差异.
func diffRedisConfDirectives(oldConf, newConf string) string {
	oldDirectives := parseRedisConfDirectives(oldConf)
	newDirectives := parseRedisConfDirectives(newConf)
	names := sortedDirectiveNames(oldDirectives, newDirectives)

	added := make(map[string]bool)
	dropped := make(map[string]bool)
	var changedLines []string
	for _, name := range names {
		oldValues, newValues := oldDirectives[name], newDirectives[name]
		switch {
		case len(oldValues) == 0:
			added[name] = true
		case len(newValues) == 0:
			dropped[name] = true
		case !sameConfValues(name, oldValues, newValues):
			changedLines = append(changedLines, fmt.Sprintf("  %s: %s => %s",
				name, joinMaskedValues(name, oldValues), joinMaskedValues(name, newValues)))
		}
	}

	// 一边掉旧名、一边加新名, 且两者是同一配置项的两种叫法: 归并成改名
	var renamedLines []string
	for _, name := range names {
		alias := confNameAliasIndex[name]
		if !dropped[name] || alias == "" || !added[alias] {
			continue
		}
		delete(dropped, name)
		delete(added, alias)
		renamedLines = append(renamedLines, fmt.Sprintf("  %s %s => %s %s",
			name, joinMaskedValues(name, oldDirectives[name]),
			alias, joinMaskedValues(alias, newDirectives[alias])))
	}

	addedLines := make([]string, 0, len(added))
	droppedLines := make([]string, 0, len(dropped))
	for _, name := range names {
		if added[name] {
			addedLines = append(addedLines, fmt.Sprintf("  %s %s",
				name, joinMaskedValues(name, newDirectives[name])))
		}
		if dropped[name] {
			droppedLines = append(droppedLines, fmt.Sprintf("  %s %s",
				name, joinMaskedValues(name, oldDirectives[name])))
		}
	}

	sections := []struct {
		title string
		lines []string
	}{
		{"renamed", renamedLines},
		{"value changed", changedLines},
		{"added by target version", addedLines},
		{"dropped by target version", droppedLines},
	}
	sb := strings.Builder{}
	for _, section := range sections {
		if len(section.lines) == 0 {
			continue
		}
		sb.WriteString(fmt.Sprintf("[%s] %d item(s)\n", section.title, len(section.lines)))
		for _, line := range section.lines {
			sb.WriteString(line)
			sb.WriteByte('\n')
		}
	}
	if sb.Len() == 0 {
		return "(no directive level change)"
	}
	return sb.String()
}

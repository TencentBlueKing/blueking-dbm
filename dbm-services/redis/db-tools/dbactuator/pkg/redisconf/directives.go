// Package redisconf 按目标版本模板重建 redis.conf: 读出 redis 实际生效的配置, 渲染目标版本配置,
// 叠加有名字的改写步骤, 跑完写盘前的不变量校验, 产出一份尚未落盘的 Plan.
//
// 本包不停起进程, 也不连实例. 什么时候写盘、写盘之外还要做什么(挪数据、等同步), 由调用方
// (版本升级、配置刷新等原子任务)决定; Plan.Changes 只描述落盘要做的动作, 每个动作可撤销.
package redisconf

import (
	"path/filepath"
	"slices"
	"strings"

	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// Directives 配置文件中 指令名(小写) -> 该指令出现的所有取值(按文件顺序)
type Directives map[string][]string

// ParseDirectives 解析 redis 配置文件.
//
// 只做 "取出某指令的取值" 用途, 不能用它把配置文件还原成 map 再和 dbconfig 逐 key 比较:
// rename-command / client-output-buffer-limit / save 这类指令在文件中是多行的,
// 而在 dbconfig 里是一个配置项(值内嵌换行), 两者形状不同。
func ParseDirectives(confData string) Directives {
	directives := make(Directives)
	for _, line := range strings.Split(confData, "\n") {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		fields := strings.SplitN(line, " ", 2)
		key := strings.ToLower(strings.TrimSpace(fields[0]))
		value := ""
		if len(fields) > 1 {
			value = strings.TrimSpace(fields[1])
		}
		directives[key] = append(directives[key], value)
	}
	return directives
}

// LastValue 取指令最后一次出现的值; config rewrite 会追加写, 以最后一次为准
func (d Directives) LastValue(key string) string {
	values := d[key]
	if len(values) == 0 {
		return ""
	}
	return values[len(values)-1]
}

// Has 指令是否出现过
func (d Directives) Has(key string) bool {
	return len(d[key]) > 0
}

// ReplicationDirectiveNames replicaof/slaveof: 同一指令在不同版本下的两种写法
var ReplicationDirectiveNames = []string{"replicaof", "slaveof"}

// ClusterNoFailoverDirectiveNames "禁止本节点被选为新主"在不同版本下的两种写法
var ClusterNoFailoverDirectiveNames = []string{"cluster-replica-no-failover", "cluster-slave-no-failover"}

// replicaSpellingSinceVersion replica 系列写法(replicaof / cluster-replica-*)从 redis 5.0 开始才有
const replicaSpellingSinceVersion = 5000000

// UsesReplicaSpelling 目标版本是否认 replica 系列写法.
//
// 解析不出版本时按"不认"处理: slave 系列写法所有版本都认, 反之会让实例起不来.
// tendisplus / TendisSSD 基于 4.x 以下内核, 解析出来的主版本也落在这一侧.
func UsesReplicaSpelling(pkgBaseName string) bool {
	baseVer, _, err := util.VersionParse(pkgBaseName)
	if err != nil {
		return false
	}
	return baseVer >= replicaSpellingSinceVersion
}

// StripDirectives 删掉配置文件里所有名为 names 之一的生效行, 注释行原样保留.
//
// 用于"覆盖一条配置项": 只往末尾追加的话, redis 行为是对的(以最后一条为准),
// 但文件里会同时留着两条指向不同主库的 replicaof, 之后任何人或任何工具读它都会读错.
func StripDirectives(confData string, names []string) string {
	lines := strings.Split(confData, "\n")
	kept := make([]string, 0, len(lines))
	for _, line := range lines {
		trimmed := strings.TrimSpace(line)
		if trimmed != "" && !strings.HasPrefix(trimmed, "#") {
			fields := strings.SplitN(trimmed, " ", 2)
			if slices.Contains(names, strings.ToLower(strings.TrimSpace(fields[0]))) {
				continue
			}
		}
		kept = append(kept, line)
	}
	return strings.Join(kept, "\n")
}

// AppendDirective 在配置文件末尾写一条配置项
func AppendDirective(confData, name, value string) string {
	if confData != "" && !strings.HasSuffix(confData, "\n") {
		confData += "\n"
	}
	return confData + name + " " + value + "\n"
}

// EffectiveReplicationOf 返回配置文件中最后生效的 replicaof/slaveof 取值,
// 没有主从关系时返回空.
//
// slaveof 与 replicaof 是同一指令的两种写法, redis 以文件中最后一次出现为准,
// 所以必须按行序判断: 旧配置文件可能同时有 redis_replicaof 原子任务追加的 slaveof
// 和之后 config rewrite 写的 replicaof, 按指令名优先级取值会和 redis 的实际行为相反,
// 也就看不出实例其实跟了另一台主.
//
// 返回的 name 是文件里原本用的写法, 补写时必须沿用: redis 5.0 以下不认 replicaof.
func EffectiveReplicationOf(confData string) (name string, value string) {
	for _, line := range strings.Split(confData, "\n") {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		fields := strings.SplitN(line, " ", 2)
		lineName := strings.ToLower(strings.TrimSpace(fields[0]))
		if !slices.Contains(ReplicationDirectiveNames, lineName) {
			continue
		}
		lineValue := ""
		if len(fields) > 1 {
			lineValue = strings.TrimSpace(fields[1])
		}
		// slaveof no one 是"取消主从", 和没有这条指令等价, 但它同样会覆盖前面的取值
		if lineValue == "" || strings.EqualFold(lineValue, "no one") {
			name, value = "", ""
			continue
		}
		name, value = lineName, lineValue
	}
	return name, value
}

// diskLoadModules 从旧配置文件的 loadmodule 行还原 module 列表.
// 用于 dbm 侧没有下发 module 信息时兜底, 避免升级后实例少加载 module.
func diskLoadModules(directives Directives) []LoadModuleItem {
	items := make([]LoadModuleItem, 0, len(directives["loadmodule"]))
	for _, soPath := range directives["loadmodule"] {
		soPath = strings.TrimSpace(soPath)
		if soPath == "" {
			continue
		}
		items = append(items, LoadModuleItem{SoFile: filepath.Base(soPath)})
	}
	return items
}

func confHasB2Module(confData string) bool {
	for _, soPath := range ParseDirectives(confData)["loadmodule"] {
		if strings.Contains(soPath, "libB2RedisModule") {
			return true
		}
	}
	return false
}

// Unquote 去掉 config rewrite 给字符串取值加的引号
func Unquote(value string) string {
	value = strings.TrimPrefix(value, "\"")
	return strings.TrimSuffix(value, "\"")
}

// resolvePathSymlinks 解析路径中的软链, 用于判断两个写法不同的路径是否落在同一处.
// 路径本身还不存在时逐级向上找到存在的祖先, 再把剩余部分拼回去.
func resolvePathSymlinks(path string) string {
	path = filepath.Clean(path)
	if resolved, err := filepath.EvalSymlinks(path); err == nil {
		return resolved
	}
	parent, rest := path, ""
	for {
		next := filepath.Dir(parent)
		if next == parent {
			return path
		}
		rest = filepath.Join(filepath.Base(parent), rest)
		parent = next
		if resolved, err := filepath.EvalSymlinks(parent); err == nil {
			return filepath.Join(resolved, rest)
		}
	}
}

// SamePathValue 判断配置文件里两个路径取值是否指向同一位置.
//
// 要同时容忍两件事: config rewrite 给取值加的引号, 以及 /data1 -> /data 这类软链.
// 同一个目录的两种写法不能被当成 "把数据目录搬走了".
func SamePathValue(a, b string) bool {
	a = Unquote(strings.TrimSpace(a))
	b = Unquote(strings.TrimSpace(b))
	if a == b {
		return true
	}
	if a == "" || b == "" {
		return false
	}
	if filepath.Clean(a) == filepath.Clean(b) {
		return true
	}
	return resolvePathSymlinks(a) == resolvePathSymlinks(b)
}

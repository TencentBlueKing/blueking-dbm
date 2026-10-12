package redisconf

import (
	"fmt"
	"os"
	"path/filepath"
	"slices"
	"strconv"
	"strings"

	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// Effective 一个端口在磁盘上的配置, 以及 redis 加载它之后实际看到的那份.
//
// 历史布局(include instance.conf、cluster-config-file 指向非默认文件等)都在这一层摊平成
// "redis 实际生效的取值", 渲染与校验只认 Expanded, 不再感知布局.
type Effective struct {
	File string
	// Raw 磁盘原文, 只用于备份和回滚
	Raw string
	// Expanded 展开 include 之后、redis 实际加载的那份文本
	Expanded string
	// Includes 原文 include 过的文件, 按展开顺序
	Includes []string
	// sources 指令名 -> 最后一次出现它的文件. 只记 include 进来的, 没记的就在 File 里
	sources map[string]string
}

// Source 指令最后一次出现在哪个文件里
func (e *Effective) Source(name string) string {
	if src, ok := e.sources[strings.ToLower(name)]; ok {
		return src
	}
	return e.File
}

// ConfFileOf 定位端口的 redis.conf.
//
// 只认 redis.conf: instance.conf 是老部署方式留下的, config rewrite 写的是 redis.conf,
// 重建 instance.conf 既无意义也有风险.
func ConfFileOf(port int) (string, error) {
	confFile := filepath.Join(consts.GetRedisDataDir(), "redis", strconv.Itoa(port), "redis.conf")
	if !util.FileExists(confFile) {
		return "", fmt.Errorf("redis conf(%s) not exists", confFile)
	}
	return confFile, nil
}

// LoadEffective 读取端口在磁盘上的配置, 并按 redis 语义展开 include
func LoadEffective(port int) (*Effective, error) {
	confFile, err := ConfFileOf(port)
	if err != nil {
		return nil, err
	}
	return LoadEffectiveFile(confFile)
}

// LoadEffectiveFile 同 LoadEffective, 直接给出配置文件路径
func LoadEffectiveFile(confFile string) (*Effective, error) {
	raw, err := os.ReadFile(confFile)
	if err != nil {
		return nil, fmt.Errorf("read redis conf(%s) failed,err:%v", confFile, err)
	}
	eff := &Effective{File: confFile, Raw: string(raw), sources: map[string]string{}}
	eff.Expanded, err = expandIncludes(confFile, eff.Raw, &eff.Includes, eff.sources)
	if err != nil {
		return nil, err
	}
	return eff, nil
}

// redisConfIncludeMaxDepth include 嵌套层数上限. redis 自己既不设限也不查循环
const redisConfIncludeMaxDepth = 8

// ExpandIncludes 按 redis 加载配置的方式展开 include: 在 include 所在行原地内联
// 被引用文件(递归), 其余行原样保留. 行序因此与 redis 实际看到的一致, LastValue 之类
// "后出现的覆盖先出现的" 判断不用感知 include.
//
// 没有 include 时原样返回 raw.
//
// 相对路径按 confFile 所在目录解析: redis 是相对进程 cwd 解析的, 而 su mysql -c 拉起时
// cwd 不可控, 找不到就报错, 不去猜. 通配符(redis 7 才支持)、循环、超深嵌套、读不到文件
// 一律报错 —— 这些现场按原样重建只会丢配置.
func ExpandIncludes(confFile, raw string) (expanded string, includes []string, err error) {
	expanded, err = expandIncludes(confFile, raw, &includes, nil)
	if err != nil {
		return "", nil, err
	}
	return expanded, includes, nil
}

func expandIncludes(confFile, raw string, includes *[]string, sources map[string]string) (string, error) {
	x := includeExpander{baseDir: filepath.Dir(confFile), includes: includes, sources: sources}
	return x.expand(confFile, raw, []string{resolvePathSymlinks(confFile)})
}

type includeExpander struct {
	baseDir  string
	includes *[]string
	sources  map[string]string
}

func (x *includeExpander) expand(curFile, data string, stack []string) (string, error) {
	lines := strings.Split(data, "\n")
	out := make([]string, 0, len(lines))
	for _, line := range lines {
		target, isInclude := confIncludeTarget(line)
		if !isInclude {
			x.recordSource(curFile, line, len(stack) > 1)
			out = append(out, line)
			continue
		}
		if target == "" {
			return "", fmt.Errorf("conf(%s) has an include without a path", curFile)
		}
		if strings.ContainsAny(target, "*?[") {
			return "", fmt.Errorf("conf(%s) include %q uses a glob pattern,not supported", curFile, target)
		}
		path := target
		if !filepath.IsAbs(path) {
			path = filepath.Join(x.baseDir, path)
		}
		path = filepath.Clean(path)
		if len(stack) > redisConfIncludeMaxDepth {
			return "", fmt.Errorf("conf(%s) include %s nested deeper than %d levels",
				curFile, path, redisConfIncludeMaxDepth)
		}
		resolved := resolvePathSymlinks(path)
		if slices.Contains(stack, resolved) {
			return "", fmt.Errorf("conf(%s) include %s forms a cycle", curFile, path)
		}
		content, err := os.ReadFile(path)
		if err != nil {
			return "", fmt.Errorf("conf(%s) include %s cannot be read,err:%v", curFile, path, err)
		}
		*x.includes = append(*x.includes, path)
		sub, err := x.expand(path, string(content), append(slices.Clone(stack), resolved))
		if err != nil {
			return "", err
		}
		out = append(out, strings.TrimSuffix(sub, "\n"))
	}
	return strings.Join(out, "\n"), nil
}

// recordSource 记下指令最后一次出现的文件. 主文件里的行会把前面 include 带进来的覆盖掉
func (x *includeExpander) recordSource(curFile, line string, included bool) {
	if x.sources == nil {
		return
	}
	trimmed := strings.TrimSpace(line)
	if trimmed == "" || strings.HasPrefix(trimmed, "#") {
		return
	}
	name := strings.ToLower(strings.Fields(trimmed)[0])
	if included {
		x.sources[name] = curFile
		return
	}
	delete(x.sources, name)
}

// confIncludeTarget 判断一行是否为生效的 include, 返回去引号后的路径
func confIncludeTarget(line string) (target string, isInclude bool) {
	trimmed := strings.TrimSpace(line)
	if trimmed == "" || strings.HasPrefix(trimmed, "#") {
		return "", false
	}
	fields := strings.Fields(trimmed)
	if !strings.EqualFold(fields[0], "include") {
		return "", false
	}
	return Unquote(strings.TrimSpace(trimmed[len(fields[0]):])), true
}

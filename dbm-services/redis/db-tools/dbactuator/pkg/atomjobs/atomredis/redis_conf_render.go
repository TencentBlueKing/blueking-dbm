package atomredis

import (
	"fmt"
	"path/filepath"
	"sort"
	"strconv"
	"strings"

	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
)

// RedisConfRenderParams 渲染 redis.conf 所需的实例维度事实, 尚未经过推导.
//
// dbconfig 中的配置项值可能仍是 {{address}} / {{port}} 这类占位符 (plat 级模板继承下来的),
// 由本结构体提供实例真实值, 经 Resolve 推导成占位符取值后完成替换.
type RedisConfRenderParams struct {
	IP        string
	Port      int
	Password  string
	Databases int
	// InstDir 实例目录 (如 /data/redis/30000), 对应 {{redis_data_dir}}
	InstDir string
	// DbType cluster_type, 用于决定 {{cluster_enabled}}, 以及是否需要算 tendisplus 的 rocks 取值
	DbType string
	// MaxMemory 对应 {{maxmemory}}. 安装场景固定为 "0" (由 dbmon 动态设置);
	// 升级重建配置场景需传入实例配置文件中已有的值, 否则会把内存上限清零.
	MaxMemory string
	// InstCount 本机实例个数, tendisplus 的 blockcache / write buffer 按实例数分摊
	InstCount uint64
}

// confPlaceholder 一个占位符及其最终取值
type confPlaceholder struct {
	name  string // 形如 {{address}}
	value string
}

// RedisConfRenderValues 已完成推导的占位符取值, 按替换顺序排列.
//
// 用有序切片而非 map: map 遍历是随机序, 若某个取值本身含 {{}} 会让替换结果不稳定.
type RedisConfRenderValues []confPlaceholder

// BuildRedisConfTemplate 把 dbconfig 的配置项 map 拼成 redis.conf 文本 (仍含 {{}} 占位符).
//
// 注意: 可重复出现的指令 (rename-command / client-output-buffer-limit / save 等) 在 dbconfig 中
// 是"一个配置项 + 值内嵌换行并重复 key 前缀"的形式, 例如
//
//	rename-command => "config confxx \nrename-command flushdb cleandb \n..."
//
// 所以这里按 "key value" 直接写出即可自然展开成多行, 不能把配置文件反向解析成 map 后逐 key 比较.
//
// 配置项按 key 排序输出, 保证同一份 dbconfig 渲染结果稳定 (便于升级场景 diff 复核).
// module 相关行固定追加在末尾, 以保证 libB2RedisModule 的 "appendonly no" 覆盖 dbconfig 取值.
func BuildRedisConfTemplate(confConfigs map[string]string, modules []LoadModuleItem, pkgBaseName string) string {
	keys := make([]string, 0, len(confConfigs))
	for key := range confConfigs {
		keys = append(keys, key)
	}
	sort.Strings(keys)

	sb := strings.Builder{}
	for _, rawKey := range keys {
		key := strings.TrimSpace(rawKey)
		lowerKey := strings.ToLower(key)
		value := strings.TrimSpace(confConfigs[rawKey])
		if key == "loadmodule" {
			continue
		}
		if key == "repl-diskless-sync" && strings.HasPrefix(pkgBaseName, "redis-2.8.17") {
			continue
		}
		// Tendisplus 特有配置项
		switch lowerKey {
		case "netiothreadnum":
			value = strconv.Itoa(util.GetTendisplusNetIOThreadNum())
		case "executorthreadnum":
			value = strconv.Itoa(util.GetTendisplusExeThreadNum())
		case "executorworkpoolsize":
			value = strconv.Itoa(util.GetTendisplusExeWorkPoolSize())
		case "rocks.max_background_jobs":
			value = strconv.Itoa(util.GetTendisplusMaxBGJobs())
		case "rocks.max_background_compactions":
			value = strconv.Itoa(util.GetMaxBgCompactions())
		case "migratesenderthreadnum":
			value = strconv.Itoa(util.GetMigrateSenderThreadNum())
		case "migratereceivethreadnum":
			value = strconv.Itoa(util.GetMigrateReceiverThreadNum())
		case "migrateclearthreadnum":
			value = strconv.Itoa(util.GetMigrateClearTheadNum())
		}
		if value == "" {
			if !strings.EqualFold(key, "save") {
				continue // 其他配置项值为空时不写入
			}
			value = "\"\"" // 针对 save "" 的情况
		}
		sb.WriteString(key)
		sb.WriteByte(' ')
		sb.WriteString(value)
		sb.WriteByte('\n')
	}
	// 加载module
	for _, moduleItem := range modules {
		if strings.Contains(moduleItem.SoFile, "libB2RedisModule") {
			// libB2RedisModule 相关module需要关闭 aof,否则会报错
			sb.WriteString("appendonly no\n")
		}
		sb.WriteString("loadmodule ")
		sb.WriteString(filepath.Join(consts.RedisModulePath, moduleItem.SoFile))
		sb.WriteByte('\n')
	}
	return sb.String()
}

// Resolve 把实例事实推导成占位符取值.
//
// 环境探测(读本机内存)集中在这里, 渲染阶段因此不再依赖运行环境, 也不会失败.
func (p RedisConfRenderParams) Resolve() (RedisConfRenderValues, error) {
	clusterEnabled := "no"
	if consts.IsClusterDbType(p.DbType) {
		clusterEnabled = "yes"
	}
	maxMemory := p.MaxMemory
	if maxMemory == "" {
		maxMemory = "0"
	}
	// 密码为空时渲染成 "" 而不是空串: 否则写出的是一条没有参数的 requirepass,
	// redis 解析配置文件时直接报 wrong number of arguments, 实例起不来
	password := p.Password
	if password == "" {
		password = `""`
	}
	values := RedisConfRenderValues{
		{"{{address}}", p.IP},
		{"{{port}}", strconv.Itoa(p.Port)},
		{"{{password}}", password},
		{"{{redis_data_dir}}", p.InstDir},
		{"{{databases}}", strconv.Itoa(p.Databases)},
		{"{{cluster_enabled}}", clusterEnabled},
		{"{{maxmemory}}", maxMemory},
	}
	// blockcache / write buffer 只有 tendisplus 模板会用到, cache 实例不必为此去读系统内存
	if consts.IsTendisplusInstanceDbType(p.DbType) {
		rocks, err := p.tendisplusRocksValues()
		if err != nil {
			return nil, err
		}
		values = append(values, rocks...)
	}
	return values, nil
}

// tendisplusRocksValues 按本机实例数分摊算出 rocksdb 的 blockcache / write buffer
func (p RedisConfRenderParams) tendisplusRocksValues() (RedisConfRenderValues, error) {
	instCount := p.InstCount
	if instCount == 0 {
		instCount = 1
	}
	instBlockcache, err := util.GetTendisplusBlockcache(instCount)
	if err != nil {
		return nil, err
	}
	writeBufferSize, err := util.GetTendisplusWriteBufferSize(instCount)
	if err != nil {
		return nil, err
	}
	return RedisConfRenderValues{
		{"{{rocks_blockcachemb}}", strconv.FormatUint(instBlockcache, 10)},
		{"{{rocks_write_buffer_size}}", strconv.FormatUint(writeBufferSize, 10)},
	}, nil
}

// RenderRedisConfData 把模板中的 {{}} 占位符替换成实例真实值.
//
// 这里不校验是否还有未替换的占位符: 历史模板 (如 TendisCache-3.2 的 {{masterauth}}) 存在
// 渲染器不认识的占位符, 安装路径一直是原样写入的, 不能在此改变行为.
// 需要严格校验的调用方 (升级重建配置) 请额外调用 CheckUnresolvedPlaceholder.
func RenderRedisConfData(tmpl string, values RedisConfRenderValues) string {
	confData := tmpl
	for _, ph := range values {
		confData = strings.ReplaceAll(confData, ph.name, ph.value)
	}
	return confData
}

// CheckUnresolvedPlaceholder 检查渲染结果中是否还有未替换的 {{}} 占位符.
// 升级重建配置时, 残留占位符会让新进程解析配置失败, 必须提前拒绝写入.
//
// 报错只带占位符本身: 配置里有密码, 不能把上下文原文抄进日志.
func CheckUnresolvedPlaceholder(confData string) error {
	idx := strings.Index(confData, "{{")
	if idx < 0 {
		return nil
	}
	placeholder := confData[idx:]
	if end := strings.Index(placeholder, "}}"); end >= 0 {
		placeholder = placeholder[:end+2]
	} else if len(placeholder) > 32 {
		placeholder = placeholder[:32]
	}
	return fmt.Errorf("unresolved placeholder %q in rendered conf", placeholder)
}

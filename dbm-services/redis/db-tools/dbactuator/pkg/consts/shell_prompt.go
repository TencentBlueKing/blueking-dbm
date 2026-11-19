package consts

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

// RedisShellPromptFileName shell 提示符脚本文件名
const RedisShellPromptFileName = "dbm_redis_prompt.sh"

// RedisShellPromptDefaultFilePath shell 提示符脚本默认路径
const RedisShellPromptDefaultFilePath = "/etc/profile.d/" + RedisShellPromptFileName

// RedisShellPromptFilePath shell 提示符脚本路径
// 默认写入 /etc/profile.d/dbm_redis_prompt.sh, 单元测试可注入临时目录
var RedisShellPromptFilePath = RedisShellPromptDefaultFilePath

// 提示符 label 前缀: 存储角色、proxy 类型与存储引擎
const (
	shellPromptPrefixMaster     = "master"
	shellPromptPrefixSlave      = "slave"
	shellPromptPrefixMixed      = "mixed"
	shellPromptEngineRedis      = "redis"
	shellPromptEngineTendisSSD  = "tendisssd"
	shellPromptEngineTendisPlus = "tendisplus"
)

// shellPromptRolePrefixes 精确角色前缀, 已写入角色提示符的机器不再降级为引擎名
var shellPromptRolePrefixes = []string{
	shellPromptPrefixMaster, shellPromptPrefixSlave, shellPromptPrefixMixed,
}

// shellPromptLabelReg 提示符 label 白名单字符, 拒绝引号/空白/shell 元字符, 防止注入登录脚本
var shellPromptLabelReg = regexp.MustCompile(`^[A-Za-z0-9._-]+$`)

// shellPromptLabelInFileReg 从脚本内容中提取已设置的 label
var shellPromptLabelInFileReg = regexp.MustCompile(`@([A-Za-z0-9._-]+) `)

// redisShellPromptTemplate 仅对交互式 shell 设置 PS1, 且不 export
// \t \u \W \$ 由 bash 每次渲染提示符时动态展开
const redisShellPromptTemplate = `# Managed by DBM Redis dbactuator. Do not edit manually.
case "$-" in
    *i*) PS1='[\t \u@%s \W]\$ ' ;;
esac
`

// ValidateShellPromptLabel 校验提示符 label 仅包含白名单字符 [A-Za-z0-9._-]
func ValidateShellPromptLabel(label string) error {
	if !shellPromptLabelReg.MatchString(label) {
		return fmt.Errorf("invalid redis shell prompt label(%q): only [A-Za-z0-9._-] is allowed", label)
	}
	return nil
}

// newShellPromptLabel 拼装 <prefix>-<ip> 并校验
func newShellPromptLabel(prefix, ip string) (string, error) {
	ip = strings.TrimSpace(ip)
	if ip == "" {
		return "", fmt.Errorf("redis shell prompt label error: ip is empty")
	}
	label := fmt.Sprintf("%s-%s", prefix, ip)
	if err := ValidateShellPromptLabel(label); err != nil {
		return "", err
	}
	return label, nil
}

// ProxyShellPromptLabel 生成 proxy 节点提示符 label, 如 predixy-1.1.1.1 / twemproxy-1.1.1.2
func ProxyShellPromptLabel(proxyRole, ip string) (string, error) {
	switch proxyRole {
	case MetaRolePredixy, MetaRoleTwemproxy:
		return newShellPromptLabel(proxyRole, ip)
	default:
		return "", fmt.Errorf("redis shell prompt label error: unsupported proxy role(%q)", proxyRole)
	}
}

// StorageRoleShellPromptLabel 按 meta_role 集合生成存储节点提示符 label
// 单角色: master-<ip> / slave-<ip>; 主从混部(正常不会出现): mixed-<ip>
func StorageRoleShellPromptLabel(metaRoles []string, ip string) (string, error) {
	roleSet := make(map[string]struct{}, len(metaRoles))
	for _, role := range metaRoles {
		if role = strings.TrimSpace(role); role != "" {
			roleSet[role] = struct{}{}
		}
	}
	if len(roleSet) == 0 {
		return "", fmt.Errorf("redis shell prompt label error: meta_role is empty")
	}
	if len(roleSet) == 1 {
		for role := range roleSet {
			switch role {
			case MetaRolePredixy, MetaRoleTwemproxy:
				return newShellPromptLabel(role, ip)
			case MetaRoleRedisMaster:
				return newShellPromptLabel(shellPromptPrefixMaster, ip)
			case MetaRoleRedisSlave:
				return newShellPromptLabel(shellPromptPrefixSlave, ip)
			default:
				return "", fmt.Errorf("redis shell prompt label error: unsupported meta_role(%q)", role)
			}
		}
	}
	_, hasMaster := roleSet[MetaRoleRedisMaster]
	_, hasSlave := roleSet[MetaRoleRedisSlave]
	if len(roleSet) == 2 && hasMaster && hasSlave {
		return newShellPromptLabel(shellPromptPrefixMixed, ip)
	}
	return "", fmt.Errorf("redis shell prompt label error: unsupported meta_role combination(%v)",
		sortedShellPromptRoles(roleSet))
}

// sortedShellPromptRoles 角色集合排序, 仅用于错误信息输出
func sortedShellPromptRoles(roleSet map[string]struct{}) []string {
	roles := make([]string, 0, len(roleSet))
	for role := range roleSet {
		roles = append(roles, role)
	}
	for i := 1; i < len(roles); i++ {
		for j := i; j > 0 && roles[j] < roles[j-1]; j-- {
			roles[j], roles[j-1] = roles[j-1], roles[j]
		}
	}
	return roles
}

// StorageEngineShellPromptLabel 存储节点无 meta_role 时的引擎兜底 label
// 如 redis-1.1.1.1 / tendisssd-1.1.1.1 / tendisplus-1.1.1.2
func StorageEngineShellPromptLabel(dbType, ip string) (string, error) {
	var engine string
	switch {
	case IsTendisSSDInstanceDbType(dbType):
		engine = shellPromptEngineTendisSSD
	case IsTendisplusInstanceDbType(dbType):
		engine = shellPromptEngineTendisPlus
	case IsRedisInstanceDbType(dbType):
		engine = shellPromptEngineRedis
	default:
		return "", fmt.Errorf("redis shell prompt label error: unsupported db_type(%q)", dbType)
	}
	return newShellPromptLabel(engine, ip)
}

// RenderRedisShellPrompt 渲染提示符脚本内容
func RenderRedisShellPrompt(label string) (string, error) {
	if err := ValidateShellPromptLabel(label); err != nil {
		return "", err
	}
	return fmt.Sprintf(redisShellPromptTemplate, label), nil
}

// ShellPromptIPFromLabel 从提示符 label 中提取 IP, 如 master-1.1.1.1 => 1.1.1.1
func ShellPromptIPFromLabel(label string) string {
	idx := strings.Index(label, "-")
	if idx < 0 {
		return ""
	}
	return label[idx+1:]
}

// isStorageRoleShellPromptLabel 是否是存储角色类(精确角色)提示符, 如 master-<ip>
func isStorageRoleShellPromptLabel(label string) bool {
	for _, prefix := range shellPromptRolePrefixes {
		if strings.HasPrefix(label, prefix+"-") {
			return true
		}
	}
	return false
}

// readRedisShellPromptLabel 读取提示符脚本中已设置的 label, 文件不存在或未匹配时返回空串
func readRedisShellPromptLabel(path string) string {
	content, err := os.ReadFile(path)
	if err != nil {
		return ""
	}
	matches := shellPromptLabelInFileReg.FindStringSubmatch(string(content))
	if len(matches) != 2 {
		return ""
	}
	return matches[1]
}

// SetRedisShellPrompt 原子写入提示符脚本
// force=false 时, 若已存在同 IP 的角色提示符(master/slave/mixed), 则保留不覆盖, 防止角色降级为引擎名
func SetRedisShellPrompt(label string, force bool) error {
	content, err := RenderRedisShellPrompt(label)
	if err != nil {
		return err
	}
	path := RedisShellPromptFilePath
	if !force {
		currentLabel := readRedisShellPromptLabel(path)
		if isStorageRoleShellPromptLabel(currentLabel) &&
			ShellPromptIPFromLabel(currentLabel) == ShellPromptIPFromLabel(label) {
			return nil
		}
	}
	if current, err := os.ReadFile(path); err == nil && string(current) == content {
		// 内容一致, 无需重写
		return nil
	}
	return writeRedisShellPromptFile(path, content)
}

// writeRedisShellPromptFile 先写临时文件再 rename, 避免并发或异常中断破坏已有脚本
func writeRedisShellPromptFile(path, content string) error {
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return fmt.Errorf("mkdir %s failed:%v", dir, err)
	}
	tmpFile, err := os.CreateTemp(dir, "."+RedisShellPromptFileName+".*")
	if err != nil {
		return fmt.Errorf("create temp file in %s failed:%v", dir, err)
	}
	tmpPath := tmpFile.Name()
	defer func() {
		if tmpPath != "" {
			os.Remove(tmpPath)
		}
	}()
	if _, err = tmpFile.WriteString(content); err != nil {
		tmpFile.Close()
		return fmt.Errorf("write temp file %s failed:%v", tmpPath, err)
	}
	if err = tmpFile.Close(); err != nil {
		return fmt.Errorf("close temp file %s failed:%v", tmpPath, err)
	}
	if err = os.Chmod(tmpPath, 0644); err != nil {
		return fmt.Errorf("chmod %s failed:%v", tmpPath, err)
	}
	if err = os.Rename(tmpPath, path); err != nil {
		return fmt.Errorf("rename %s to %s failed:%v", tmpPath, path, err)
	}
	tmpPath = ""
	return nil
}

// RemoveRedisShellPrompt 删除提示符脚本, 文件不存在时视为成功(幂等)
func RemoveRedisShellPrompt() error {
	err := os.Remove(RedisShellPromptFilePath)
	if err != nil && !os.IsNotExist(err) {
		return fmt.Errorf("remove %s failed:%v", RedisShellPromptFilePath, err)
	}
	return nil
}

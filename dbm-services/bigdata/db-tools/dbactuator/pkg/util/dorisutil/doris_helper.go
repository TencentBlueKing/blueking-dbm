package dorisutil

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"
	"fmt"
	"io"
	"net/http"
	"regexp"
	"strings"
)

// DefaultDorisProfile Doris 环境变量文件，由 doris init 的 WriteProfile 步骤生成，
// 内含 JAVA_HOME / JRE / CLASSPATH / DORIS_HOME / PATH
const DefaultDorisProfile = "/data/dorisenv/dorisprofile"

// LoadProfileCmd 加载 Doris 环境变量的命令前缀，用于 su - mysql -c "..." 的命令体开头。
//
// 为什么必须显式加载：
// TLinux 4 的 su 并非 --noprofile，它执行的是 ["-bash", "-c", ...]。
// TLinux 4 的 bash 对这种「通过 argv[0] 标识的非交互登录 shell」不加载 /etc/profile，
// 因此 su - mysql -c "cmd" 里的 cmd 拿不到 JAVA_HOME，表现为 start_fe.sh 找不到 java。
//
// 为什么直接加载 dorisprofile 而不是 /etc/profile：
//  1. /etc/profile 中的 "source /data/dorisenv/dorisprofile" 一行会被 node_operation.go 的
//     sed -i '/dorisprofile/d' 删除（节点清理），混部或重装场景下加载 /etc/profile 可能拿不到变量；
//  2. /etc/profile 会连带执行 /etc/profile.d/*.sh，这些脚本的 stderr 输出会被
//     osutil.ExecShellCommand 判为执行失败（stderr 非空即失败），直接加载可缩小面；
//  3. 与 node_operation.go 中 supervisor 启动命令的加载方式保持一致。
//
// 为什么用 . 而不是 source：
// source 是 bash 扩展，POSIX sh/dash 不识别。执行用户 mysql 可能由其他组件（如 DBM MySQL 的
// sysinit）先行创建，其登录 shell 不保证是 bash，用 source 可能直接报 source: not found。
const LoadProfileCmd = ". " + DefaultDorisProfile + ";"

// GetLocalNetwork 获取本地网络
func GetLocalNetwork() (string, error) {
	return osutil.ExecShellCommand(false, "ip a|grep eth1|grep inet |awk '{print $2}'")
}

// StartFeByHelper 通过helper启动fe
// 用 ExecShellCommandJ（仅 exit code 非 0 才算失败）：start_fe.sh 会把启动日志写到 stderr，
// 用 ExecShellCommand 会因「stderr 非空即失败」把正常启动判为失败。
// 启动结果由调用方的 CheckFrontEndStart 通过 HTTP 接口确认，不依赖 stderr 是否为空。
func StartFeByHelper(dorisHomeDir string, role string, masterIp string, rpcPort int) error {

	_, err := osutil.ExecShellCommandJ(false, fmt.Sprintf(
		"su - mysql -c \"%s %s/%s/bin/start_fe.sh --helper %s:%d --daemon\"",
		LoadProfileCmd, dorisHomeDir, role, masterIp, rpcPort))
	return err
}

// HttpGet 执行HTTP Get请求
func HttpGet(url string) ([]byte, error) {
	var responseBody []byte
	// 创建 GET 请求
	request, _ := http.NewRequest("GET", url, nil)
	// 发送请求并获取响应
	response, err := http.DefaultClient.Do(request)
	if err != nil {
		logger.Error("http get request failed %s", err.Error())
		return responseBody, err
	}
	defer response.Body.Close()
	// 检查响应状态码
	if response.StatusCode == 200 {
		logger.Debug("http get response code is 200")
	} else {
		logger.Error("http get failed, status code is %d", response.StatusCode)
	}
	// 读取响应体
	responseBody, err = io.ReadAll(response.Body)
	if err != nil {
		logger.Error("failed to read response body: %s", err.Error())
		return responseBody, err
	}
	return responseBody, nil
}

// DefaultString 返回 originalStr，如果 originalStr 为空串则返回 defaultStr
func DefaultString(originalStr, defaultStr string) string {
	if originalStr == "" {
		return defaultStr
	}
	return originalStr
}

// EscapeSQLString 对 SQL 字符串字面值做转义，用于安全地拼进 '...' 单引号字面值中。
// 遵循 MySQL/Doris 的字符串字面值转义规则：反斜杠 \ 转义为 \\，单引号 ' 转义为 \'。
// 该函数不负责给结果加外层单引号，调用方仍需自行包一层 '%s'。
// 注意：Doris 目前 SQL 层不支持 prepared statement 占位符（对 ALTER USER 等 DDL 更如此），
// 因此对涉及用户输入（如密码）的场景必须走本转义函数，避免注入或语法破坏。
func EscapeSQLString(s string) string {
	replacer := strings.NewReplacer(
		`\`, `\\`,
		`'`, `\'`,
	)
	return replacer.Replace(s)
}

// sqlIdentifierRe 合法 SQL 标识符：首字符为字母或下划线，其余为字母/数字/下划线，长度 1~64。
// 与 MySQL/Doris 的未引号标识符规则对齐，避免用户输入包含 `、' 、空格、; 等破坏 SQL 结构的字符。
var sqlIdentifierRe = regexp.MustCompile(`^[A-Za-z_][A-Za-z0-9_]{0,63}$`)

// ValidateSQLIdentifier 校验字符串是否为合法的 SQL 标识符（如用户名、库名、表名）。
// 该校验用于阻止将不受信任的输入直接拼入 SQL DDL 语句，防止注入和语法破坏。
func ValidateSQLIdentifier(name string) error {
	if !sqlIdentifierRe.MatchString(name) {
		return fmt.Errorf("invalid SQL identifier %q: must match ^[A-Za-z_][A-Za-z0-9_]{0,63}$", name)
	}
	return nil
}

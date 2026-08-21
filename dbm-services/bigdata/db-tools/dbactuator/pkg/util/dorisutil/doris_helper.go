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

// GetLocalNetwork 获取本地网络
func GetLocalNetwork() (string, error) {
	return osutil.ExecShellCommand(false, "ip a|grep eth1|grep inet |awk '{print $2}'")
}

// StartFeByHelper 通过helper启动fe
func StartFeByHelper(dorisHomeDir string, role string, masterIp string, rpcPort int) error {

	_, err := osutil.ExecShellCommand(false, fmt.Sprintf(
		"su - mysql -c \"%s/%s/bin/start_fe.sh --helper %s:%d --daemon\"",
		dorisHomeDir, role, masterIp, rpcPort))
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

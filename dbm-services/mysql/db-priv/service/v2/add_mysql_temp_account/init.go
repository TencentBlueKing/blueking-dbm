package add_mysql_temp_account

import (
	"crypto/sha1"
	"dbm-services/mysql/priv-service/service"
	"dbm-services/mysql/priv-service/service/v2/add_priv"
	"fmt"
	"strings"
)

type Param struct {
	RootId    string   `json:"root_id"`
	Addresses []string `json:"addresses"`
	BkCloudId int64    `json:"bk_cloud_id"`
}

func AddMySQLTempAccount(param *Param) (report map[string][]string, err error) {
	username := fmt.Sprintf("J_%s", param.RootId)
	password := password(param.RootId)
	oldPassword := oldPassword(param.RootId)

	accessHosts := []string{"%", "localhost"}

	dummyAddPrivParam := add_priv.PrivTaskPara{
		PrivTaskPara: &service.PrivTaskPara{
			User: username,
		},
	}

	report, err = dummyAddPrivParam.AddOnMySQL(
		accessHosts,
		map[int64][]string{param.BkCloudId: param.Addresses},
		map[string][]string{"*": []string{"ALL PRIVILEGES"}},
		password,
		oldPassword,
		true,
	)
	return report, err
}

// Password 复刻 MySQL 4.1+ 的 PASSWORD() 函数
// 算法：'*' + UPPER(HEX(SHA1(SHA1(password))))
// 返回长度固定 41 字符（1 个 '*' + 40 个十六进制字符）
// 空字符串输入返回空字符串（与 MySQL 行为一致）
func password(password string) string {
	if password == "" {
		return ""
	}
	first := sha1.Sum([]byte(password))
	second := sha1.Sum(first[:])
	return "*" + strings.ToUpper(fmt.Sprintf("%x", second))
}

// OldPassword 复刻 MySQL 4.1 之前的 OLD_PASSWORD() 函数
// 算法：私有的 nr/nr2 双 hash，输出 16 字符十六进制小写
// 空字符串输入返回空字符串
func oldPassword(password string) string {
	if password == "" {
		return ""
	}

	var nr uint32 = 1345345333
	var add uint32 = 7
	var nr2 uint32 = 0x12345671

	for i := 0; i < len(password); i++ {
		c := password[i]
		// 跳过空格和 tab（MySQL 官方实现有这个逻辑）
		if c == ' ' || c == '\t' {
			continue
		}
		tmp := uint32(c)
		nr ^= (((nr & 63) + add) * tmp) + (nr << 8)
		nr2 += (nr2 << 8) ^ nr
		add += tmp
	}

	// 取低 31 位（清掉符号位）
	result1 := nr & ((uint32(1) << 31) - 1)
	result2 := nr2 & ((uint32(1) << 31) - 1)

	return fmt.Sprintf("%08x%08x", result1, result2)
}

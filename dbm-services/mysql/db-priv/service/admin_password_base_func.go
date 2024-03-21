package service

import (
	crand "crypto/rand"
	"crypto/sha1"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"io/ioutil"
	"log/slog"
	"os"
	"time"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/priv-service/util"

	"github.com/spf13/viper"
)

func CheckOrGetPassword(psw string, security SecurityRule) (string, error) {
	// 密码为空，根据security生成随机密码
	// 密码不为空，根据security检查密码复杂度，security为空则不检查负责度（迁移密码无法修改，且密码复杂度不足的情况）
	var password string
	var err error
	if psw != "" {
		password = psw
		check := CheckPassword(security, []byte(psw))
		if !check.IsStrength {
			return "", errno.NotMeetComplexity
		}
	} else {
		// 没有传入密码，按照密码复杂度随机生成密码
		password, err = GenerateRandomString(security)
		if err != nil {
			slog.Error("GenerateRandomString", "error", err)
			return "", err
		}
	}
	return password, nil
}

func GetSecurityRule(securityName string) (SecurityRule, error) {
	var security SecurityRule
	rule, err := (&SecurityRulePara{Name: securityName}).GetSecurityRule()
	if err != nil {
		slog.Error("msg", "GetSecurityRule", err)
		return security, err
	}
	err = json.Unmarshal([]byte((*rule).Rule), &security)
	if err != nil {
		slog.Error("msg", "unmarshal error", err)
		return security, err
	}
	return security, nil
}

// RemoveLockedInstances 日常随机化剔除锁定的实例
func (m *ModifyAdminUserPasswordPara) RemoveLockedInstances() error {
	var locked []*Address
	var clusters []OneCluster
	where := fmt.Sprintf(" username='%s' and component='%s' and lock_until is not null ", m.UserName, m.Component)
	err := DB.Self.Model(&TbPasswords{}).Where(where).Select("ip,port,bk_cloud_id").Scan(&locked).Error
	if err != nil {
		slog.Error("msg", "get locked instances error", err)
		return err
	}
	if len(locked) == 0 {
		return nil
	}
	for _, cluster := range m.Clusters {
		if cluster.BkCloudId == nil {
			return errno.CloudIdRequired
		}
		var roles []InstanceList
		for _, role := range cluster.MultiRoleInstanceLists {
			var addresses []IpPort
			for _, address := range role.Addresses {
				for k, lock := range locked {
					if address.Ip == lock.Ip && address.Port == lock.Port && *cluster.BkCloudId == *lock.BkCloudId {
						break
					}
					if k == len(locked)-1 {
						addresses = append(addresses, address)
					}
				}
			}
			if len(addresses) > 0 {
				roles = append(roles, InstanceList{role.Role, addresses})
			}
		}
		if len(roles) > 0 {
			clusters = append(clusters, OneCluster{cluster.BkCloudId, cluster.ClusterType, roles})
		}
	}
	m.Clusters = clusters
	return nil
}

// NeedToBeRandomized 锁定到期的实例实例随机化
func (m *ModifyAdminUserPasswordPara) NeedToBeRandomized() error {
	var needs []*Address
	var clusters []OneCluster
	where := fmt.Sprintf(" username='%s' and component='%s' and lock_until <= now()", m.UserName, m.Component)
	err := DB.Self.Model(&TbPasswords{}).Where(where).Select("ip,port,bk_cloud_id").Scan(&needs).Error
	if err != nil {
		slog.Error("msg", "get locked instances error", err)
		return err
	}
	for _, cluster := range m.Clusters {
		if cluster.BkCloudId == nil {
			return errno.CloudIdRequired
		}
		var roles []InstanceList
		for _, role := range cluster.MultiRoleInstanceLists {
			var addresses []IpPort
			for _, address := range role.Addresses {
				for _, need := range needs {
					if address.Ip == need.Ip && address.Port == need.Port && *cluster.BkCloudId == *need.BkCloudId {
						addresses = append(addresses, address)
						break
					}
				}
			}
			if len(addresses) > 0 {
				roles = append(roles, InstanceList{role.Role, addresses})
			}
		}
		if len(roles) > 0 {
			clusters = append(clusters, OneCluster{cluster.BkCloudId, cluster.ClusterType, roles})
		}
	}
	m.Clusters = clusters
	return nil
}

func DecodePassword(slice []*TbPasswords) error {
	pswList := UniquePassword(slice)
	pswMap := make(map[string]string, len(pswList))
	for _, item := range pswList {
		// 避免在写入和读取数据库时乱码，存储hex进制
		bytes, err := hex.DecodeString(item)
		if err != nil {
			slog.Error("msg", "get hex decode error", err)
			return err
		}
		pswMap[item], err = SM4Decrypt(string(bytes))
		if err != nil {
			slog.Error("msg", "SM4Decrypt error", err)
			return err
		}
	}
	for k, lock := range slice {
		slice[k].Password = pswMap[lock.Password]
	}
	return nil
}

// SM4Encrypt 加密
func SM4Encrypt(input string) (string, error) {
	output, err := SM4(input, "encrypt")
	if err != nil {
		slog.Error("msg", "SM4Encrypt", err)
		return "", err
	}
	return hex.EncodeToString(output), nil
}

// SM4Decrypt 解密
func SM4Decrypt(input string) (string, error) {
	output, err := SM4(input, "decrypt")
	if err != nil {
		slog.Error("msg", "SM4Decrypt", err)
		return "", err
	}
	return base64.StdEncoding.EncodeToString(output), nil
}

// SM4 加密解密
func SM4(input string, vtype string) ([]byte, error) {
	salt := make([]byte, 16)
	_, err := io.ReadFull(crand.Reader, salt)
	if err != nil {
		slog.Error("msg", "get random string error", err)
		return nil, fmt.Errorf("get random string error: %s", err.Error())
	}
	name := fmt.Sprintf("%d.%x.%x.%s", sha1.Sum([]byte(input)), time.Now().UnixNano(), salt, vtype)
	inputName := fmt.Sprintf("%s.input", name)
	outputName := fmt.Sprintf("%s.output", name)

	//由于部分特殊字符可能导致命令行执行会失败，存入文件后解密或者机密
	//cmd := fmt.Sprintf(`echo -n '%s' | openssl  enc -e -sm4-ctr -pbkdf2 -k %s`, plain, viper.GetString("bk_app_secret"))
	//cmd := fmt.Sprintf(`echo -n '%s' | openssl  enc -d -sm4-ctr -pbkdf2 -k %s`, cipher, viper.GetString("bk_app_secret"))

	_, err = os.Stat(inputName)
	if err == nil || !os.IsNotExist(err) {
		slog.Error("msg", "check file exist", os.ErrExist)
		return nil, os.ErrExist
	}
	_, err = os.Stat(outputName)
	if err == nil || !os.IsNotExist(err) {
		slog.Error("msg", "check file exist", os.ErrExist)
		return nil, os.ErrExist
	}
	inputFile, err := os.OpenFile(inputName, os.O_CREATE|os.O_RDWR, 0644)
	if err != nil {
		slog.Error("msg", "file", inputName, "create file error", err)
		return nil, err
	}

	if _, err = inputFile.Write([]byte(input)); err != nil {
		_ = inputFile.Close()
		_ = os.Remove(inputName)
		slog.Error("msg", "file", inputName, "write file error")
		return nil, err
	}
	cmd := fmt.Sprintf(`openssl enc -in %s -out %s -sm4-ctr -pbkdf2 -k %s`, inputName, outputName,
		viper.GetString("bk_app_secret"))
	if vtype == "encrypt" {
		cmd = fmt.Sprintf("%s -e ", cmd)
	} else if vtype == "decrypt" {
		cmd = fmt.Sprintf("%s -d ", cmd)
	}
	_, err = util.ExecShellCommand(false, cmd)
	if err != nil {
		slog.Error("msg", "exec command error", err)
		_ = inputFile.Close()
		_ = os.Remove(inputName)
		_ = os.Remove(outputName)
		return nil, err
	}
	output, err := ioutil.ReadFile(outputName)
	if err != nil {
		slog.Error("msg", "file", outputName, "read file error", err)
		_ = inputFile.Close()
		_ = os.Remove(inputName)
		_ = os.Remove(outputName)
		return nil, err
	}
	_ = inputFile.Close()
	_ = os.Remove(inputName)
	_ = os.Remove(outputName)
	return output, nil
}

// UniquePassword 获取distinct的数据
func UniquePassword(slice []*TbPasswords) []string {
	res := make([]string, 0)
	mp := make(map[string]bool, len(slice))
	for _, e := range slice {
		if mp[e.Password] == false {
			mp[e.Password] = true
			res = append(res, e.Password)
		}
	}
	return res
}

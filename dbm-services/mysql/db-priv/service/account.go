package service

import (
	"fmt"
	"io/ioutil"
	"os"
	"strings"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/priv-service/util"

	"github.com/spf13/viper"
	"golang.org/x/exp/slog"
)

// AddAccount 新增账号
func (m *AccountPara) AddAccount(jsonPara string) error {
	var (
		account    *TbAccounts
		insertTime util.TimeFormat
		psw        string
		count      uint64
		err        error
	)

	if m.BkBizId == 0 {
		return errno.BkBizIdIsEmpty
	}
	if m.User == "" || m.Psw == "" {
		return errno.PasswordOrAccountNameNull
	}
	if m.ClusterType == nil {
		ct := mysql
		m.ClusterType = &ct
		// return errno.ClusterTypeIsEmpty
	}

	err = DB.Self.Model(&TbAccounts{}).Where(&TbAccounts{BkBizId: m.BkBizId, User: m.User, ClusterType: *m.ClusterType}).
		Count(&count).Error
	if err != nil {
		return err
	}
	if count != 0 {
		return errno.AccountExisted.AddBefore(m.User)
	}
	psw, err = DecryptPsw(m.Psw)
	if err != nil {
		return err
	}

	if psw == m.User {
		return errno.PasswordConsistentWithAccountName
	}

	psw, err = EncryptPswInDb(psw)
	if err != nil {
		return err
	}
	insertTime = util.NowTimeFormat()
	account = &TbAccounts{BkBizId: m.BkBizId, ClusterType: *m.ClusterType, User: m.User, Psw: psw, Creator: m.Operator,
		CreateTime: insertTime}
	err = DB.Self.Model(&TbAccounts{}).Create(&account).Error
	if err != nil {
		return err
	}

	log := PrivLog{BkBizId: m.BkBizId, Operator: m.Operator, Para: jsonPara, Time: insertTime}
	AddPrivLog(log)
	return nil
}

// ModifyAccountPassword 修改账号的密码
func (m *AccountPara) ModifyAccountPassword(jsonPara string) error {
	var (
		account    TbAccounts
		id         TbAccounts
		updateTime util.TimeFormat
		psw        string
		err        error
	)

	if m.BkBizId == 0 {
		return errno.BkBizIdIsEmpty
	}
	if m.Psw == "" {
		return errno.PasswordOrAccountNameNull
	}
	if m.Id == 0 {
		return errno.AccountIdNull
	}
	if m.ClusterType == nil {
		ct := mysql
		m.ClusterType = &ct
		// return errno.ClusterTypeIsEmpty
	}

	psw, err = DecryptPsw(m.Psw)
	if err != nil {
		return err
	}

	if psw == m.User {
		return errno.PasswordConsistentWithAccountName
	}

	psw, err = EncryptPswInDb(psw)
	if err != nil {
		return err
	}
	updateTime = util.NowTimeFormat()

	account = TbAccounts{Psw: psw, Operator: m.Operator, UpdateTime: updateTime}
	id = TbAccounts{Id: m.Id}
	result := DB.Self.Model(&id).Update(&account)

	if result.Error != nil {
		return result.Error
	}
	if result.RowsAffected == 0 {
		return errno.AccountNotExisted
	}

	log := PrivLog{BkBizId: m.BkBizId, Operator: m.Operator, Para: jsonPara, Time: updateTime}
	AddPrivLog(log)

	return nil
}

// DeleteAccount 删除账号
func (m *AccountPara) DeleteAccount(jsonPara string) error {
	if m.BkBizId == 0 {
		return errno.BkBizIdIsEmpty
	}
	if m.Id == 0 {
		return errno.AccountIdNull
	}
	if m.ClusterType == nil {
		ct := mysql
		m.ClusterType = &ct
		// return errno.ClusterTypeIsEmpty
	}

	sql := fmt.Sprintf("delete from tb_accounts where id=%d and bk_biz_id = %d and cluster_type='%s'",
		m.Id, m.BkBizId, *m.ClusterType)
	result := DB.Self.Exec(sql)
	if result.Error != nil {
		return result.Error
	}
	if result.RowsAffected == 0 {
		return errno.AccountNotExisted
	}

	log := PrivLog{BkBizId: m.BkBizId, Operator: m.Operator, Para: jsonPara, Time: util.NowTimeFormat()}
	AddPrivLog(log)
	return nil
}

// DecryptPsw 对使用公钥加密的密文，用私钥解密
func DecryptPsw(psw string) (string, error) {
	var (
		xrsa       *util.XRsa
		decryptPsw string
	)
	file, err := os.Open("./privkey.pem")
	if err != nil {
		return decryptPsw, err
	}
	defer file.Close()
	content, err := ioutil.ReadAll(file)
	if err != nil {
		return decryptPsw, err
	}
	xrsa, err = util.NewXRsa(nil, content)
	if err != nil {
		return decryptPsw, err
	}
	decryptPsw, err = xrsa.PrivateDecrypt(psw)
	if err != nil {
		return decryptPsw, err
	}
	return decryptPsw, nil
}

// EncryptPswInDb 明文加密
func EncryptPswInDb(psw string) (string, error) {
	// Psw 存储mysql_old_password,mysql_native_password两种密码
	type Psw struct {
		OldPsw string `gorm:"column:old_psw;not_null" json:"old_psw"`
		Psw    string `gorm:"column:psw;not_null" json:"psw"`
	}
	var result Psw
	// 获取2种密文：mysql_old_password,mysql_native_password，密码为 json 格式，新增加密方式，方便扩展
	err := DBVersion56.Self.Table("user").Select("OLD_PASSWORD(?) AS old_psw,PASSWORD(?) AS psw", psw, psw).Take(&result).
		Error

	if err != nil {
		slog.Error("msg", err)
		return "", errno.GenerateEncryptedPasswordErr
	}
	jsonString := fmt.Sprintf(`{"old_psw":"%s","psw":"%s"}`, result.OldPsw, result.Psw)
	return jsonString, nil
}

// AddPrivLog 记录操作日志，日志不对外
func AddPrivLog(log PrivLog) {
	log.Para = strings.Replace(log.Para, viper.GetString("bk_app_code"), "", -1)
	log.Para = strings.Replace(log.Para, viper.GetString("bk_app_secret"), "", -1)
	err := DB.Self.Create(&log).Error
	if err != nil {
		slog.Error("add log err", err)
	}
}

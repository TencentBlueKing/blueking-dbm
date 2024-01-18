package service

import (
	"encoding/hex"
	"fmt"
	"log/slog"
	"strings"
	"time"

	"github.com/jinzhu/gorm"

	"dbm-services/common/go-pubpkg/errno"

	"github.com/spf13/viper"
)

// AddAccount 新增账号
func (m *AccountPara) AddAccount(jsonPara string) error {
	var (
		account *TbAccounts
		psw     string
		count   uint64
		err     error
	)

	if m.BkBizId == 0 {
		return errno.BkBizIdIsEmpty
	}
	if m.User == "" || m.Psw == "" {
		return errno.PasswordOrAccountNameNull
	}
	if (*m.ClusterType == "sqlserver_single" || *m.ClusterType == "sqlserver_ha") && m.Sid == "" {
		return errno.SqlserverSidNull
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
	psw = m.Psw
	// 从旧系统迁移的，不检查是否帐号和密码不同
	if psw == m.User && !m.MigrateFlag {
		return errno.PasswordConsistentWithAccountName
	}
	// 从旧系统迁移的，存储的密码为mysql password()允许迁移，old_password()已过滤不迁移
	if m.PasswordFunc {
		psw = fmt.Sprintf(`{"old_psw":"","psw":"%s"}`, psw)
	} else if *m.ClusterType == mysql || *m.ClusterType == tendbcluster {
		psw, err = EncryptPswInDb(psw)
		if err != nil {
			return err
		}
	} else {
		// 兼容其他数据库类型比如，密码不存储mysql password函数，而是SM4，需要能够查询
		psw, err = SM4Encrypt(psw)
		if err != nil {
			slog.Error("SM4Encrypt", "error", err)
			return err
		}
		psw = fmt.Sprintf(`{"sm4":"%s"}`, psw)
	}
	account = &TbAccounts{BkBizId: m.BkBizId, ClusterType: *m.ClusterType, User: m.User, Psw: psw, Creator: m.Operator,
		CreateTime: time.Now(), Sid: m.Sid}
	err = DB.Self.Model(&TbAccounts{}).Create(&account).Error
	if err != nil {
		return err
	}

	log := PrivLog{BkBizId: m.BkBizId, Operator: m.Operator, Para: jsonPara, Time: time.Now()}
	AddPrivLog(log)
	return nil
}

// ModifyAccountPassword 修改账号的密码
func (m *AccountPara) ModifyAccountPassword(jsonPara string) error {
	var (
		account TbAccounts
		id      TbAccounts
		psw     string
		err     error
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

	if m.Psw == m.User {
		return errno.PasswordConsistentWithAccountName
	}

	if *m.ClusterType == mysql || *m.ClusterType == tendbcluster {
		psw, err = EncryptPswInDb(m.Psw)
		if err != nil {
			return err
		}
	} else {
		// 兼容其他数据库类型比如，密码不存储mysql password函数，而是SM4，需要能够查询
		psw, err = SM4Encrypt(psw)
		if err != nil {
			slog.Error("SM4Encrypt", "error", err)
			return err
		}
		psw = fmt.Sprintf(`{"sm4":"%s"}`, psw)
	}

	account = TbAccounts{Psw: psw, Operator: m.Operator, UpdateTime: time.Now()}
	id = TbAccounts{Id: m.Id}
	result := DB.Self.Model(&id).Update(&account)

	if result.Error != nil {
		return result.Error
	}
	if result.RowsAffected == 0 {
		return errno.AccountNotExisted
	}

	log := PrivLog{BkBizId: m.BkBizId, Operator: m.Operator, Para: jsonPara, Time: time.Now()}
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

	log := PrivLog{BkBizId: m.BkBizId, Operator: m.Operator, Para: jsonPara, Time: time.Now()}
	AddPrivLog(log)
	return nil
}

// GetAccount 获取账号
func (m *AccountPara) GetAccount() ([]*TbAccounts, int64, error) {
	var (
		accounts []*TbAccounts
		result   *gorm.DB
	)
	if m.BkBizId == 0 {
		return nil, 0, errno.BkBizIdIsEmpty
	}
	result = DB.Self.Model(&TbAccounts{}).Where(&TbAccounts{
		BkBizId: m.BkBizId, ClusterType: *m.ClusterType, User: m.User}).Select(
		"id,bk_biz_id,user,cluster_type,creator,create_time,update_time").Scan(&accounts)
	if result.Error != nil {
		return nil, 0, result.Error
	}
	return accounts, int64(len(accounts)), nil
}

// GetAccountIncludePsw 获取帐号以及密码
func (m *GetAccountIncludePswPara) GetAccountIncludePsw() ([]*TbAccounts, int64, error) {
	var (
		accounts []*TbAccounts
		result   *gorm.DB
	)
	if m.BkBizId == 0 {
		return nil, 0, errno.BkBizIdIsEmpty
	}
	if len(m.Users) == 0 {
		return nil, 0, errno.ErrUserIsEmpty
	}
	// mongodb 需要查询psw
	users := "'" + strings.Join(m.Users, "','") + "'"
	where := fmt.Sprintf("bk_biz_id=%d and cluster_type='%s' and user in (%s)", m.BkBizId, *m.ClusterType, users)
	result = DB.Self.Model(&TbAccounts{}).Where(where).
		Select("id,bk_biz_id,user,cluster_type,json_unquote(json_extract(psw,'$.sm4')) as psw," +
			"creator,create_time,update_time,sid").Scan(&accounts)
	if result.Error != nil {
		return nil, 0, result.Error
	}

	for k, v := range accounts {
		// 避免在写入和读取数据库时乱码，存储hex进制
		bytes, err := hex.DecodeString(v.Psw)
		if err != nil {
			slog.Error("msg", "get hex decode error", err)
			return nil, 0, fmt.Errorf("get hex decode error: %s", err.Error())
		}
		accounts[k].Psw, err = SM4Decrypt(string(bytes))
		if err != nil {
			slog.Error("SM4Decrypt", "error", err)
			return nil, 0, fmt.Errorf("SM4Decrypt error: %s", err.Error())
		}
	}
	return accounts, int64(len(accounts)), nil
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

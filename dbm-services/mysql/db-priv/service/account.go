package service

import (
	"dbm-services/mysql/priv-service/util"
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
func (m *AccountPara) AddAccount(jsonPara string, ticket string) (TbAccounts, error) {
	var (
		account *TbAccounts
		psw     string
		count   uint64
		err     error
		detail  TbAccounts
	)

	if m.BkBizId == 0 {
		return detail, errno.BkBizIdIsEmpty
	}
	if m.User == "" || m.Psw == "" {
		return detail, errno.PasswordOrAccountNameNull
	}
	if *m.ClusterType == sqlserver && m.Sid == "" {
		return detail, errno.SqlserverSidNull
	}
	if m.ClusterType == nil {
		ct := mysql
		m.ClusterType = &ct
		// return errno.ClusterTypeIsEmpty
	}
	err = DB.Self.Model(&TbAccounts{}).Where(&TbAccounts{BkBizId: m.BkBizId, User: m.User, ClusterType: *m.ClusterType}).
		Count(&count).Error
	if err != nil {
		return detail, err
	}
	if count != 0 {
		return detail, errno.AccountExisted.AddBefore(m.User)
	}
	innerAccount := make(map[string][]string)
	innerAccount[sqlserver] = []string{"mssql_exporter", "dbm_admin", "sa", "sqlserver"}
	innerAccount[mongodb] = []string{"dba", "apppdba", "monitor", "appmonitor"}
	innerAccount[mysql] = []string{"gcs_admin", "gcs_dba", "monitor", "gm", "admin", "repl", "dba_bak_all_sel",
		"yw", "partition_yw", "spider", "mysql.session", "mysql.sys", "gcs_spider", "sync", "monitor_all",
		"default", "mysql", "mysql.infoschema", "proxy", "root"}
	innerAccount[tendbcluster] = innerAccount[mysql]
	if !m.MigrateFlag {
		if util.HasElem(strings.ToLower(m.User), innerAccount[*m.ClusterType]) {
			return detail, errno.InternalAccountNameNotAllowed
		}
	}
	psw = m.Psw
	// 从旧系统迁移的，不检查是否帐号和密码不同
	if psw == m.User && !m.MigrateFlag {
		return detail, errno.PasswordConsistentWithAccountName
	}
	// 检查mysql账号名称长度
	if (*m.ClusterType == mysql || *m.ClusterType == tendbcluster) && !m.MigrateFlag {
		if len(m.User) > 16 {
			return detail, errno.AccountNameTooLong
		}
	}
	// 从旧系统迁移的，存储的密码为mysql password()允许迁移，old_password()已过滤不迁移
	if m.PasswordFunc {
		psw = fmt.Sprintf(`{"old_psw":"","psw":"%s"}`, psw)
	} else if *m.ClusterType == mysql || *m.ClusterType == tendbcluster {
		psw, err = EncryptPswInDb(psw)
		if err != nil {
			return detail, err
		}
	} else {
		// 兼容其他数据库类型比如mongo，密码不存储mysql password函数，而是SM4，需要能够查询
		psw, err = SM4Encrypt(psw)
		if err != nil {
			slog.Error("SM4Encrypt", "error", err)
			return detail, err
		}
		psw = fmt.Sprintf(`{"sm4":"%s"}`, psw)
	}
	vtime := time.Now()
	account = &TbAccounts{BkBizId: m.BkBizId, ClusterType: *m.ClusterType, User: m.User, Psw: psw, Creator: m.Operator,
		CreateTime: vtime, UpdateTime: vtime, Sid: m.Sid}
	err = DB.Self.Model(&TbAccounts{}).Create(&account).Error
	if err != nil {
		return detail, err
	}
	err = DB.Self.Model(&TbAccounts{}).First(&detail, account.Id).Error
	if err != nil {
		return detail, err
	}
	log := PrivLog{BkBizId: m.BkBizId, Ticket: ticket, Operator: m.Operator, Para: jsonPara, Time: vtime}
	AddPrivLog(log)
	return detail, nil
}

// ModifyAccountPassword 修改账号的密码
func (m *AccountPara) ModifyAccountPassword(jsonPara string, ticket string) error {
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

	log := PrivLog{BkBizId: m.BkBizId, Ticket: ticket, Operator: m.Operator, Para: jsonPara, Time: time.Now()}
	AddPrivLog(log)

	return nil
}

// DeleteAccount 删除账号
func (m *AccountPara) DeleteAccount(jsonPara string, ticket string) error {
	if m.BkBizId == 0 {
		return errno.BkBizIdIsEmpty
	}
	if m.Id == 0 {
		return errno.AccountIdNull
	}
	if m.ClusterType == nil {
		ct := mysql
		m.ClusterType = &ct
	}
	result := DB.Self.
		Where("id = ? AND bk_biz_id = ? AND cluster_type = ?", m.Id, m.BkBizId, *m.ClusterType).
		Delete(&TbAccounts{})
	if result.Error != nil {
		return result.Error
	}
	if result.RowsAffected == 0 {
		return errno.AccountNotExisted
	}
	log := PrivLog{BkBizId: m.BkBizId, Ticket: ticket, Operator: m.Operator, Para: jsonPara, Time: time.Now()}
	AddPrivLog(log)
	return nil
}

// escapeLike 转义 LIKE 查询中的通配符，防止通配符注入，需配合 escape '\\' 使用
func escapeLike(s string) string {
	return strings.NewReplacer(`\`, `\\`, `%`, `\%`, `_`, `\_`).Replace(s)
}

// GetAccountList 获取账号列表
func (m *GetAccountListPara) GetAccountList() ([]*TbAccounts, int, error) {
	var (
		accounts []*TbAccounts
	)
	// 使用占位符参数化拼接查询条件，避免 SQL 注入
	conditions := []string{"1=1"}
	var args []interface{}
	if m.BkBizId > 0 {
		conditions = append(conditions, "bk_biz_id = ?")
		args = append(args, m.BkBizId)
	}
	if m.ClusterType != nil {
		conditions = append(conditions, "cluster_type = ?")
		args = append(args, *m.ClusterType)
	}
	if m.UserLike != "" {
		conditions = append(conditions, `user like ? escape '\\'`)
		args = append(args, "%"+escapeLike(m.UserLike)+"%")
	}
	if m.User != "" {
		conditions = append(conditions, "user = ?")
		args = append(args, m.User)
	}
	if m.Id != nil {
		m.Ids = append(m.Ids, *m.Id)
	}
	if len(m.Ids) != 0 {
		conditions = append(conditions, "id in (?)")
		args = append(args, m.Ids)
	}
	where := strings.Join(conditions, " and ")
	cnt := Cnt{}
	vsql := fmt.Sprintf("select count(*) as cnt from tb_accounts where %s", where)
	err := DB.Self.Raw(vsql, args...).Scan(&cnt).Error
	if err != nil {
		slog.Error(vsql, "execute error", err)
		return nil, 0, err
	}
	if cnt.Count == 0 {
		return nil, 0, nil
	}
	if m.Limit == nil {
		vsql = fmt.Sprintf("select id, user, creator, bk_biz_id from tb_accounts where %s", where)
	} else {
		vsql = fmt.Sprintf("select id, user, creator, bk_biz_id from tb_accounts where %s limit ? offset ?", where)
		args = append(args, *m.Limit, *m.Offset)
	}
	err = DB.Self.Raw(vsql, args...).Scan(&accounts).Error
	if err != nil {
		slog.Error(vsql, "execute error", err)
		return nil, 0, err
	}
	return accounts, cnt.Count, nil
}

// GetAccountIncludePsw 获取帐号以及密码
func (m *GetAccountIncludePswPara) GetAccountIncludePsw() ([]*TbAccounts, int, error) {
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
	if m.ClusterType == nil {
		return nil, 0, errno.ClusterTypeIsEmpty
	}
	// mongodb 需要查询psw，使用占位符参数化查询，避免 SQL 注入
	result = DB.Self.Model(&TbAccounts{}).
		Where("bk_biz_id = ? and cluster_type = ? and user in (?)", m.BkBizId, *m.ClusterType, m.Users).
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
	return accounts, len(accounts), nil
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
	err := DBVersion56.Self.Table("user").Select("OLD_PASSWORD(?) AS old_psw,PASSWORD(?) AS psw", psw,
		psw).Take(&result).
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

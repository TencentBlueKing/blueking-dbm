package service

import (
	errors2 "errors"
	"fmt"
	"strings"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/priv-service/util"

	"github.com/jinzhu/gorm"
)

// QueryAccountRule 获取账号规则
func (m *BkBizId) QueryAccountRule() ([]*AccountRuleSplitUser, int64, error) {
	var (
		rules                []*Rule
		accounts             []*Account
		accountRuleSplitUser []*AccountRuleSplitUser
		count                int64
		result               *gorm.DB
		err                  error
	)
	if m.BkBizId == 0 {
		return nil, count, errno.BkBizIdIsEmpty
	}
	if m.ClusterType == nil {
		ct := mysql
		m.ClusterType = &ct
		// return nil, count, errno.ClusterTypeIsEmpty
	}
	err = DB.Self.Model(&TbAccounts{}).Where(&TbAccounts{BkBizId: m.BkBizId, ClusterType: *m.ClusterType}).Select(
		"id,bk_biz_id,user,creator,create_time").Scan(&accounts).Error
	if err != nil {
		return nil, count, err
	}
	accountRuleSplitUser = make([]*AccountRuleSplitUser, len(accounts))
	for k, v := range accounts {
		result = DB.Self.Model(&TbAccountRules{}).Where(&TbAccountRules{BkBizId: m.BkBizId, AccountId: (*v).Id,
			ClusterType: *m.ClusterType}).
			Select("id,account_id,bk_biz_id,dbname,priv,creator,create_time").Scan(&rules)
		accountRuleSplitUser[k] = &AccountRuleSplitUser{Account: v, Rules: rules}
		if err != nil {
			return nil, count, err
		}
		count += result.RowsAffected
	}
	// count账号规则的数目，不是账号的数目
	return accountRuleSplitUser, count, nil
}

// AddAccountRule 新增账号规则
func (m *AccountRulePara) AddAccountRule(jsonPara string) error {
	var (
		accountRule TbAccountRules
		insertTime  util.TimeFormat
		dbs         []string
		allTypePriv string
		dmlDdlPriv  string
		globalPriv  string
		err         error
	)
	ConstPrivType := []string{"dml", "ddl", "global"}

	err = m.ParaPreCheck()
	if err != nil {
		return err
	}

	dbs, err = util.String2Slice(m.Dbname)
	if err != nil {
		return err
	}

	err = AccountRuleExistedPreCheck(m.BkBizId, m.AccountId, *m.ClusterType, dbs)
	if err != nil {
		return err
	}

	for _, _type := range ConstPrivType {
		value, exists := m.Priv[_type]
		if exists {
			if _type == "dml" || _type == "ddl" {
				dmlDdlPriv = fmt.Sprintf("%s,%s", dmlDdlPriv, value)
			} else {
				globalPriv = value
			}
			allTypePriv = fmt.Sprintf("%s,%s", allTypePriv, value)
		}
	}

	dmlDdlPriv = strings.Trim(dmlDdlPriv, ",")
	allTypePriv = strings.Trim(allTypePriv, ",")

	tx := DB.Self.Begin()
	insertTime = util.NowTimeFormat()
	for _, db := range dbs {
		accountRule = TbAccountRules{BkBizId: m.BkBizId, ClusterType: *m.ClusterType, AccountId: m.AccountId, Dbname: db,
			Priv:       allTypePriv,
			DmlDdlPriv: dmlDdlPriv, GlobalPriv: globalPriv, Creator: m.Operator, CreateTime: insertTime}
		err = tx.Debug().Model(&TbAccountRules{}).Create(&accountRule).Error
		if err != nil {
			tx.Rollback()
			return err
		}
	}
	tx.Commit()

	log := PrivLog{BkBizId: m.BkBizId, Operator: m.Operator, Para: jsonPara, Time: insertTime}
	AddPrivLog(log)

	return nil
}

// ModifyAccountRule 修改账号规则
func (m *AccountRulePara) ModifyAccountRule(jsonPara string) error {
	var (
		accountRule TbAccountRules
		updateTime  util.TimeFormat
		dbname      string
		allTypePriv string
		dmlDdlPriv  string
		globalPriv  string
		err         error
	)

	ConstPrivType := []string{"dml", "ddl", "global"}

	err = m.ParaPreCheck()
	if err != nil {
		return err
	}
	if m.Id == 0 {
		return errno.AccountRuleIdNull
	}

	// 可以修改账号规则的db名、权限
	// 不能与已有账号规则冲突
	updateTime = util.NowTimeFormat()
	dbname = strings.TrimSpace(m.Dbname)
	if strings.Contains(dbname, " ") {
		return errno.OnlyOneDatabaseAllowed
	}

	err = DB.Self.Model(&TbAccountRules{}).Where(&TbAccountRules{BkBizId: m.BkBizId, AccountId: m.AccountId,
		Dbname: dbname, ClusterType: *m.ClusterType}).Take(&accountRule).Error
	/*
		修改后，新的"bk_biz_id+account_id+dbname"，是否会与已有规则冲突
		修改前检查是否存"bk_biz_id+account_id+dbname"，要排除本账号
		两种情况，检查通过：1、查询到本账号，说明没有修改dbname，只是修改权限 2、没有查询到记录，说明修改了dbname，但是新的账号规则与已有账号规则不冲突。
	*/

	// 修改后的账号规则与已有账号规则冲突
	if err == nil && accountRule.Id != m.Id {
		return errno.AccountRuleExisted
	}

	if err != nil && !errors2.Is(err, gorm.ErrRecordNotFound) {
		return err
	}

	for _, _type := range ConstPrivType {
		value, exists := m.Priv[_type]
		if exists {
			if _type == "dml" || _type == "ddl" {
				dmlDdlPriv = fmt.Sprintf("%s,%s", dmlDdlPriv, value)
			} else {
				globalPriv = value
			}
			allTypePriv = fmt.Sprintf("%s,%s", allTypePriv, value)
		}
	}

	dmlDdlPriv = strings.Trim(dmlDdlPriv, ",")
	allTypePriv = strings.Trim(allTypePriv, ",")

	/*
		通过结构体变量更新字段值, gorm库会忽略零值字段，0, nil,"", false这些值会被忽略掉，不会更新。
		实际可能需要将global_priv更新为""，map类型替代结构体。
		accountRule = TbAccountRules{Dbname: dbname, Priv:
		allTypePriv, DmlDdlPriv:dmlDdlPriv,GlobalPriv: globalPriv,
		Operator: m.Operator, UpdateTime: updateTime}
		err = DB.Self.Model(&TbAccountRules{Id: m.Id}).Update(&accountRule).Error
	*/
	accountRuleMap := map[string]interface{}{"dbname": dbname, "priv": allTypePriv, "dml_ddl_priv": dmlDdlPriv,
		"global_priv": globalPriv, "operator": m.Operator, "update_time": updateTime}
	result := DB.Self.Model(&TbAccountRules{Id: m.Id}).Update(accountRuleMap)
	if result.Error != nil {
		return result.Error
	}
	if result.RowsAffected == 0 {
		return errno.AccountRuleNotExisted
	}

	log := PrivLog{BkBizId: m.BkBizId, Operator: m.Operator, Para: jsonPara, Time: updateTime}
	AddPrivLog(log)

	return nil
}

// DeleteAccountRule 删除账号规则
func (m *DeleteAccountRuleById) DeleteAccountRule(jsonPara string) error {
	if m.BkBizId == 0 {
		return errno.BkBizIdIsEmpty
	}
	if len(m.Id) == 0 {
		return errno.AccountRuleIdNull
	}
	if m.ClusterType == nil {
		ct := mysql
		m.ClusterType = &ct
		// return errno.ClusterTypeIsEmpty
	}

	/*
		批量删除调整为execute sql。
			（1）当多个条件中存在主键，gorm生成的语句自动忽略非主键条件，导致条件丢失：
			result := DB.Self.Delete(&TbAccountRules{}, m.Id, m.BkBizId)
			result := DB.Self.Delete(&TbAccountRules{}, m.Id).Where("bk_biz_id=?", m.BkBizId)
			（2）delete where多个条件不支持：
			result := DB.Self.Delete(&TbAccountRules{}).Where("id IN (?) AND bk_biz_id = ?", strings.Join(temp, ","), m.BkBizId)
	*/

	var temp = make([]string, len(m.Id))
	for k, v := range m.Id {
		temp[k] = fmt.Sprintf("%d", v)
	}

	sql := fmt.Sprintf("delete from tb_account_rules where id in (%s) and bk_biz_id = %d and cluster_type = '%s'",
		strings.Join(temp, ","), m.BkBizId, *m.ClusterType)
	result := DB.Self.Exec(sql)
	if result.Error != nil {
		return result.Error
	}
	if result.RowsAffected == 0 {
		return errno.AccountRuleNotExisted
	}
	log := PrivLog{BkBizId: m.BkBizId, Operator: m.Operator, Para: jsonPara, Time: util.NowTimeFormat()}
	AddPrivLog(log)
	return nil
}

// AccountRuleExistedPreCheck 检查账号规则是否已存在
func AccountRuleExistedPreCheck(bkBizId, accountId int64, clusterType string, dbs []string) error {
	var (
		err         error
		count       uint64
		existedRule []string
	)

	// 账号是否存在，存在才可以申请账号规则
	err = DB.Self.Model(&TbAccounts{}).Where(&TbAccounts{BkBizId: bkBizId, ClusterType: clusterType, Id: accountId}).
		Count(&count).Error
	if err != nil {
		return err
	}
	if count == 0 {
		return errno.AccountNotExisted
	}

	// 检查账号规则是否已存在，"业务+账号+db"是否已存在,存在不再创建
	for _, db := range dbs {
		err = DB.Self.Model(&TbAccountRules{}).Where(&TbAccountRules{BkBizId: bkBizId, ClusterType: clusterType,
			AccountId: accountId, Dbname: db}).
			Count(&count).Error
		if err != nil {
			return err
		}
		if count != 0 {
			existedRule = append(existedRule, db)
		}
	}

	if len(existedRule) > 0 {
		return errno.Errno{Code: 51001, Message: fmt.Sprintf("Account rule of user on database(%s) is existed",
			strings.Join(existedRule, ",")), CNMessage: fmt.Sprintf("用户对数据库(%s)授权的账号规则已存在", strings.Join(existedRule, ","))}
	}
	return nil
}

// ParaPreCheck 入参AccountRulePara检查
func (m *AccountRulePara) ParaPreCheck() error {
	ConstPrivType := []string{"dml", "ddl", "global"}
	if m.BkBizId == 0 {
		return errno.BkBizIdIsEmpty
	}
	if m.AccountId == 0 {
		return errno.AccountIdNull
	}
	if m.Dbname == "" {
		return errno.DbNameNull
	}
	if m.ClusterType == nil {
		//return errno.ClusterTypeIsEmpty
		ct := mysql
		m.ClusterType = &ct
	}

	// 权限为空的情况
	// 1、"priv": {}
	// 2、"priv": {"dml":"","ddl":"","global":""}  or  "priv": {"dml":""} or ...

	nullFlag := true
	for _, _type := range ConstPrivType {
		value, exists := m.Priv[_type]
		if exists {
			if value != "" {
				nullFlag = false
				break
			}
		}
	}

	if len(m.Priv) == 0 || nullFlag {
		return errno.PrivNull
	}
	return nil
}

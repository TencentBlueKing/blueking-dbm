package service

import (
	"dbm-services/mysql/priv-service/util"
	errors2 "errors"
	"fmt"
	"log/slog"
	"strings"
	"time"

	"github.com/jinzhu/gorm"

	"dbm-services/common/go-pubpkg/errno"
)

// QueryAccountRule 获取账号规则
func (m *QueryRulePara) QueryAccountRule() ([]*AccountRuleSplitUser, int, error) {
	var (
		rules                []*Rule
		accounts             []*Account
		accountRuleSplitUser []*AccountRuleSplitUser
		filterAccount        []*Account
		filterAccountIds     string
		count                int
		err                  error
		ruleIds              string
		accountIds           string
		where                string
		noRuleAccount        []*Account
	)
	slog.Info("QueryRulePara", *m)
	if m.BkBizId == 0 {
		return nil, count, errno.BkBizIdIsEmpty
	}
	if m.ClusterType == nil {
		ct := mysql
		m.ClusterType = &ct
		// return nil, count, errno.ClusterTypeIsEmpty
	}
	base := fmt.Sprintf("bk_biz_id=%d and cluster_type='%s'", m.BkBizId, *m.ClusterType)
	where = base
	for _, id := range m.RuleIds {
		ruleIds = fmt.Sprintf("%s,%d", ruleIds, id)
	}
	if ruleIds != "" {
		ruleIds = strings.TrimPrefix(ruleIds, ",")
		where = fmt.Sprintf("%s and id in (%s)", where, ruleIds)
	}
	if m.Dbname != "" {
		where = fmt.Sprintf("%s and dbname like '%%%s%%'", where, m.Dbname)
	}
	if m.User != "" {
		err = DB.Self.Table("tb_accounts").Where(fmt.Sprintf("%s and user like '%%%s%%'", base,
			m.User)).Select("id,bk_biz_id,user,creator,create_time").Find(&filterAccount).Error
		if err != nil {
			return nil, count, err
		}
		if len(filterAccount) == 0 {
			return nil, count, nil
		}
		for _, item := range filterAccount {
			filterAccountIds = fmt.Sprintf("%s,%d", filterAccountIds, (*item).Id)
		}
		filterAccountIds = strings.TrimPrefix(filterAccountIds, ",")
		where = fmt.Sprintf("%s and account_id in (%s)", where, filterAccountIds)
	}
	if len(m.Privs) > 0 {
		for _, priv := range m.Privs {
			where = fmt.Sprintf("%s and priv like '%%%s%%'", where, priv)
		}
	}
	cnt := Cnt{}
	vsql := fmt.Sprintf("select count(*) as cnt from tb_account_rules where %s", where)
	err = DB.Self.Raw(vsql).Scan(&cnt).Error
	if err != nil {
		slog.Error(vsql, "execute error", err)
		return nil, 0, err
	}
	if m.Limit != nil && m.Offset != nil {
		err = DB.Self.Table("tb_account_rules").Where(where).
			Select("id,account_id,bk_biz_id,dbname,priv,creator,create_time").Limit(*m.Limit).Offset(
			*m.Offset).Order("account_id, id").Find(&rules).Error
	} else if m.Limit == nil && m.Offset == nil {
		err = DB.Self.Table("tb_account_rules").Where(where).
			Select("id,account_id,bk_biz_id,dbname,priv,creator,create_time").Order(
			"account_id, id").Find(&rules).Error
	} else if m.Limit != nil && m.Offset == nil {
		err = DB.Self.Table("tb_account_rules").Where(where).
			Select("id,account_id,bk_biz_id,dbname,priv,creator,create_time").Limit(*m.Limit).Order(
			"account_id, id").Find(&rules).Error
	} else {
		return accountRuleSplitUser, 0, fmt.Errorf("offset not null but limit null")
	}
	if err != nil {
		slog.Error("query account rule error", "where", where)
		return nil, 0, err
	}
	// 没有查到帐号规则
	if len(rules) != 0 {
		accountRuleRelate := make(map[int64][]*Rule)
		uniqAccount := make(map[int64]struct{})
		for _, rule := range rules {
			id := (*rule).AccountId
			accountRuleRelate[id] = append(accountRuleRelate[id], rule)
			if _, isExists := uniqAccount[id]; isExists == false {
				uniqAccount[id] = struct{}{}
				accountIds = fmt.Sprintf("%s,%d", accountIds, id)
			}
		}
		accountIds = strings.TrimPrefix(accountIds, ",")
		accountWhere := fmt.Sprintf("%s and id in (%s)", base, accountIds)
		err = DB.Self.Table("tb_accounts").Where(accountWhere).Select(
			"id,bk_biz_id,user,creator,create_time").Order("id").Scan(&accounts).Error
		if err != nil {
			slog.Error("msg", "query account error", err)
			return nil, 0, err
		}
		for _, account := range accounts {
			accountRuleSplitUser = append(accountRuleSplitUser,
				&AccountRuleSplitUser{Account: account, Rules: accountRuleRelate[account.Id]})
		}
	}
	// 显示没有规则的账号（由于提高效率分页用于账号规则，将没有规则的账号展示在首页）,没有任何过滤条件或者仅有user过滤条件时会展示
	if m.NoRuleUser == true {
		where = base
		if m.User != "" {
			where = fmt.Sprintf("%s and id in (%s)", base, filterAccountIds)
		}
		vsql = fmt.Sprintf("select id,bk_biz_id,user,creator,create_time from tb_accounts where id not in "+
			"(select distinct(account_id) from tb_account_rules where %s) and %s;", base, where)
		err = DB.Self.Raw(vsql).Scan(&noRuleAccount).Error
		if err != nil {
			slog.Error("msg", "query account error", err)
			return nil, 0, err
		}
	}
	for _, account := range noRuleAccount {
		accountRuleSplitUser = append(accountRuleSplitUser,
			&AccountRuleSplitUser{Account: account, Rules: nil})
	}
	return accountRuleSplitUser, cnt.Count, nil
}

// AddAccountRule 新增账号规则
func (m *AccountRulePara) AddAccountRule(jsonPara string, ticket string) ([]TbAccountRules, error) {
	var (
		accountRule TbAccountRules
		dbs         []string
		allTypePriv string
		dmlDdlPriv  string
		globalPriv  string
		err         error
		rules       []TbAccountRules
	)
	// dml: select，insert，update，delete
	// ddl: create，alter，drop，index，execute，create view
	// global:
	// 		(1)非常规权限：file, trigger, event, create routine, alter routine, replication client，replication slave
	// 		(2)所有权限： all privileges (如果选择这个权限，其他权限不可选)
	// for sqlserver:
	// dml: db_datawriter, db_datareader
	// owner: db_owner
	var ConstPrivType []string
	if *m.ClusterType == sqlserver {
		ConstPrivType = []string{"dml", "owner"}
	} else {
		ConstPrivType = []string{"dml", "ddl", "global"}
	}

	err = m.ParaPreCheck()
	if err != nil {
		return nil, err
	}

	dbs, err = util.String2Slice(m.Dbname)
	if err != nil {
		return nil, err
	}

	_, err = AccountRulePreCheck(m.BkBizId, m.AccountId, *m.ClusterType, dbs, false)
	if err != nil {
		return nil, err
	}

	for _, _type := range ConstPrivType {
		value, exists := m.Priv[_type]
		if exists && value != "" {
			if _type == "dml" || _type == "ddl" {
				dmlDdlPriv = fmt.Sprintf("%s,%s", dmlDdlPriv, value)
			} else {
				globalPriv = value
			}
			allTypePriv = fmt.Sprintf("%s,%s", allTypePriv, value)
		}
	}
	dmlDdlPriv = strings.Trim(dmlDdlPriv, ",")
	globalPriv = strings.Trim(globalPriv, ",")
	allTypePriv = strings.Trim(allTypePriv, ",")
	vtime := time.Now()
	tx := DB.Self.Begin()
	for _, db := range dbs {
		accountRule = TbAccountRules{BkBizId: m.BkBizId, ClusterType: *m.ClusterType, AccountId: m.AccountId, Dbname: db,
			Priv:       allTypePriv,
			DmlDdlPriv: dmlDdlPriv, GlobalPriv: globalPriv, Creator: m.Operator, CreateTime: vtime,
			UpdateTime: vtime}
		err = tx.Debug().Model(&TbAccountRules{}).Create(&accountRule).Error
		if err != nil {
			tx.Rollback()
			return nil, err
		}
		rules = append(rules, accountRule)
	}
	err = tx.Commit().Error
	if err != nil {
		return nil, err
	}
	log := PrivLog{BkBizId: m.BkBizId, Ticket: ticket, Operator: m.Operator, Para: jsonPara, Time: vtime}
	AddPrivLog(log)
	return rules, nil
}

// AddAccountRuleDryRun 新增账号规则检查
func (m *AccountRulePara) AddAccountRuleDryRun() (bool, error) {
	err := m.ParaPreCheck()
	if err != nil {
		return false, err
	}
	dbs, err := util.String2Slice(m.Dbname)
	if err != nil {
		return false, err
	}
	allowForce, err := AccountRulePreCheck(m.BkBizId, m.AccountId, *m.ClusterType, dbs, true)
	if err != nil {
		return allowForce, err
	}
	return true, nil
}

// ModifyAccountRule 修改账号规则
func (m *AccountRulePara) ModifyAccountRule(jsonPara string, ticket string) error {
	var (
		accountRule TbAccountRules
		dbname      string
		allTypePriv string
		dmlDdlPriv  string
		globalPriv  string
		err         error
	)

	var ConstPrivType []string
	if *m.ClusterType == sqlserver {
		ConstPrivType = []string{"dml", "owner"}
	} else {
		ConstPrivType = []string{"dml", "ddl", "global"}
	}

	err = m.ParaPreCheck()
	if err != nil {
		return err
	}
	if m.Id == 0 {
		return errno.AccountRuleIdNull
	}

	// 可以修改账号规则的db名、权限
	// 不能与已有账号规则冲突
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
		if exists && value != "" {
			if _type == "dml" || _type == "ddl" {
				dmlDdlPriv = fmt.Sprintf("%s,%s", dmlDdlPriv, value)
			} else {
				globalPriv = value
			}
			allTypePriv = fmt.Sprintf("%s,%s", allTypePriv, value)
		}
	}

	dmlDdlPriv = strings.Trim(dmlDdlPriv, ",")
	globalPriv = strings.Trim(globalPriv, ",")
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
		"global_priv": globalPriv, "operator": m.Operator, "update_time": time.Now()}
	result := DB.Self.Model(&TbAccountRules{Id: m.Id}).Update(accountRuleMap)
	if result.Error != nil {
		return result.Error
	}
	if result.RowsAffected == 0 {
		return errno.AccountRuleNotExisted
	}

	log := PrivLog{BkBizId: m.BkBizId, Ticket: ticket, Operator: m.Operator, Para: jsonPara, Time: time.Now()}
	AddPrivLog(log)
	return nil
}

// DeleteAccountRule 删除账号规则
func (m *DeleteAccountRuleById) DeleteAccountRule(jsonPara string, ticket string) error {
	if m.BkBizId == 0 {
		return errno.BkBizIdIsEmpty
	}
	if len(m.Id) == 0 {
		return errno.AccountRuleIdNull
	}
	if m.ClusterType == nil {
		ct := mysql
		m.ClusterType = &ct
	}

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
	log := PrivLog{BkBizId: m.BkBizId, Ticket: ticket, Operator: m.Operator, Para: jsonPara, Time: time.Now()}
	AddPrivLog(log)
	return nil
}

// AccountRulePreCheck 检查账号规则是否存在，db
func AccountRulePreCheck(bkBizId, accountId int64, clusterType string, dbs []string, dryRun bool) (bool, error) {
	var (
		err         error
		count       uint64
		existedRule []string
		duplicateDb []string
		rules       []*TbAccountRules
		message     string
		allowForce  bool // 检查失败，但是仍然允许强制提交
	)
	// 账号是否存在，存在才可以申请账号规则
	err = DB.Self.Model(&TbAccounts{}).Where(&TbAccounts{BkBizId: bkBizId, ClusterType: clusterType, Id: accountId}).
		Count(&count).Error
	if err != nil {
		return allowForce, err
	}
	if count == 0 {
		return allowForce, errno.AccountNotExisted
	}

	// 检查填写的db是否重复
	var UniqMap = make(map[string]struct{})
	for _, db := range dbs {
		if _, isExists := UniqMap[db]; isExists == true {
			duplicateDb = append(duplicateDb, db)
			continue
		}
		UniqMap[db] = struct{}{}
	}
	// 检查账号规则是否已存在，"业务+账号+db"已存在需要提示
	err = DB.Self.Model(&TbAccountRules{}).Where(&TbAccountRules{BkBizId: bkBizId, ClusterType: clusterType,
		AccountId: accountId}).Scan(&rules).Error
	if err != nil {
		return allowForce, err
	}

	for _, db := range dbs {
		for _, rule := range rules {
			if db == rule.Dbname {
				existedRule = append(existedRule, db)
				break
			}
		}
	}
	allowForce = true
	if len(existedRule) > 0 {
		allowForce = false
		message = fmt.Sprintf("用户对数据库(%s)授权的账号规则已存在\n",
			strings.Join(existedRule, ","))
	}
	if len(duplicateDb) > 0 {
		allowForce = false
		message = fmt.Sprintf("%s重复填写数据库(%s) \n", message,
			strings.Join(duplicateDb, ","))
	}

	if (clusterType == mysql || clusterType == tendbcluster) && dryRun {
		var dblist []string
		for _, rule := range rules {
			dblist = append(dblist, rule.Dbname)
		}
		// db范围是否存在交接
		result := CrossCheckBetweenDbList(dbs, dblist)
		if result != "" {
			message = fmt.Sprintf("%s帐号规则中的数据库交集检查:\n%s", message, result)
		}
	}
	if len(message) > 0 {
		return allowForce, fmt.Errorf("帐号规则预检查失败:\n%s", message)
	}
	return allowForce, nil
}

// CrossCheckBetweenDbList db范围是否存在交接
func CrossCheckBetweenDbList(newDbs []string, exist []string) string {
	var errMsg []string
	var UniqMap = make(map[string]struct{})
	// 新增规则的db之间、以及与已经存在的规则是否包含关系
	for _, newDb := range newDbs {
		for _, existDb := range exist {
			if newDb == existDb {
				continue
			}
			if CrossCheck(newDb, existDb) {
				// （已授权的数据库+准备授权的数据库）和准备授权的数据库有包含关系
				msg := fmt.Sprintf("新增规则中的数据库[`%s`]与已存在的规则中的数据库[`%s`]存在交集，授权时可能冲突",
					newDb, existDb)
				errMsg = append(errMsg, msg)
				continue
			}
		}
	}
	slog.Error("msg", "check1", errMsg)
	for _, newDb := range newDbs {
		for _, newDb2 := range newDbs {
			if newDb == newDb2 {
				continue
			}
			if CrossCheck(newDb, newDb2) {
				_, isExists := UniqMap[fmt.Sprintf("%s|%s", newDb, newDb2)]
				_, isExists2 := UniqMap[fmt.Sprintf("%s|%s", newDb2, newDb)]
				if !isExists && !isExists2 {
					UniqMap[fmt.Sprintf("%s|%s", newDb, newDb2)] = struct{}{}
				}
			}
		}
	}
	slog.Error("msg", "check1", errMsg)
	for db := range UniqMap {
		d := strings.Split(db, "|")
		msg := fmt.Sprintf("新增规则中的数据库[`%s`]与新增规则中的数据库[`%s`]存在交集，授权时可能冲突",
			d[0], d[1])
		errMsg = append(errMsg, msg)
	}
	if len(errMsg) > 0 {
		return strings.Join(errMsg, "\n")
	}
	return ""
}

// ParaPreCheck 入参AccountRulePara检查
func (m *AccountRulePara) ParaPreCheck() error {
	var ConstPrivType []string
	if *m.ClusterType == sqlserver {
		ConstPrivType = []string{"dml", "owner"}
	} else {
		ConstPrivType = []string{"dml", "ddl", "global", "mongo_user", "mongo_manager"}
	}

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

	var allTypePriv string
	nullFlag := true
	for _, _type := range ConstPrivType {
		value, exists := m.Priv[_type]
		if exists {
			if value != "" {
				allTypePriv = fmt.Sprintf("%s,%s", allTypePriv, value)
				nullFlag = false
			}
		}
	}
	if len(m.Priv) == 0 || nullFlag {
		return errno.PrivNull
	}
	allTypePriv = strings.Trim(allTypePriv, ",")
	slog.Info("msg", "allTypePriv", allTypePriv, "type", *m.ClusterType)
	if *m.ClusterType == tendbcluster {
		privs, ok := AllowedSpiderPriv(allTypePriv)
		if !ok {
			return fmt.Errorf("can not grant %s privileges in tendbcluster", privs)
		}
	}
	return nil
}

func AllowedSpiderPriv(source string) (string, bool) {
	var notAllowed string
	source = strings.ToLower(source)
	privs := strings.Split(source, ",")
	for _, p := range privs {
		p = strings.Trim(p, " ")
		if !(p == "select" || p == "insert" || p == "update" || p == "delete" || p == "execute" || p == "file" || p == "reload" ||
			p == "process" || p == "show databases") {
			notAllowed = fmt.Sprintf("%s;%s", notAllowed, p)
		}
	}
	notAllowed = strings.Trim(notAllowed, ";")
	if len(notAllowed) > 0 {
		return notAllowed, false
	}
	return notAllowed, true
}

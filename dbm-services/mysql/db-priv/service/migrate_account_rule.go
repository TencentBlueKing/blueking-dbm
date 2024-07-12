package service

import (
	"dbm-services/common/go-pubpkg/errno"
	"fmt"
	"log/slog"
	"strings"
	"time"

	"github.com/spf13/viper"

	"dbm-services/mysql/priv-service/util"
)

// MigrateAccountRule 迁移帐号规则
func (m *MigratePara) MigrateAccountRule(jsonPara string, ticket string) ([]PrivRule, []PrivRule, []PrivRule, []PrivRule, []int, error) {
	apps, errOuter := m.CheckPara()
	if errOuter != nil {
		return nil, nil, nil, nil, nil, errOuter
	}
	exclude := make([]AppUser, 0)
	var appWhere string
	for app := range apps {
		appWhere = fmt.Sprintf("%s,'%s'", appWhere, app)
	}
	appWhere = strings.TrimPrefix(appWhere, ",")
	GcsDb = &Database{
		Self: openDB(m.GcsDb.User, m.GcsDb.Psw, fmt.Sprintf("%s:%s", m.GcsDb.Host, m.GcsDb.Port), m.GcsDb.Name),
	}
	defer GcsDb.Self.Close()
	// 检查scr、gcs中的账号规则，mysql和spider分开检查
	var dbmodule string
	if m.Range == "mysql" {
		dbmodule = " not like 'spider%' "
	} else if m.Range == "spider" {
		dbmodule = " like 'spider%' "
	} else {
		return nil, nil, nil, nil, nil, fmt.Errorf("不支持range值[%s]，支持mysql、spider", m.Range)
	}

	users, errMsg := CheckOldPriv(m.Key, appWhere, m.SapPassword, &exclude, dbmodule)
	passTips := "all check pass"
	// 仅检查，不迁移
	if m.Mode == "check" {
		if len(errMsg) > 0 {
			return nil, nil, nil, nil, nil, errno.CheckNotPass.Add("\n" + strings.Join(errMsg, "\n"))
		} else {
			return nil, nil, nil, nil, nil, nil
		}
	} else if m.Mode == "run" {
		// 检查通过迁移，检查不通过不迁移
		if len(errMsg) > 0 {
			return nil, nil, nil, nil, nil, errno.CheckNotPass.Add("\n" + strings.Join(errMsg, "\n"))
		} else {
			slog.Info(passTips)
		}
	} else if m.Mode == "force-run" {
		// 检查不通过，剔除不能迁移的帐号以及其规则，迁移剩余的账号规则
		if len(errMsg) > 0 {
			errMsg = append(errMsg, "[some check not pass, but force run]")
			if len(exclude) > 0 {
				errMsg = append(errMsg, "some accounts and rules belonging to them can't be migrated")
				slog.Warn("user can not be migrated", "users", exclude)
			}
			slog.Warn(fmt.Sprintf("some check not pass, but force run"))
		} else {
			slog.Info(passTips)
		}
	}

	AddPrivLog(PrivLog{BkBizId: 0, Ticket: ticket, Operator: "migrator", Para: jsonPara, Time: time.Now()})

	// 获取需要迁移的scr、gcs中的账号规则
	// db_module包含spider属于spider的权限规则；其他迁移到mysql下
	mysqlUids, uids, exUids, errOuter := FilterMigratePriv(appWhere, &exclude)
	if errOuter != nil {
		slog.Error("get privilege uid to migrate", "err", errOuter)
		errMsg = append(errMsg, fmt.Sprintf("get privilege uid to migrate error: %s", errOuter.Error()))
		return nil, nil, nil, nil, nil, errno.MigrateFail.Add("\n" + strings.Join(errMsg, "\n"))
	}

	// 根据选择的迁移范围迁移
	// 返回迁移成功的规则、迁移失败的规则、以及经过检查不能迁移的uid
	if m.Range == "mysql" {
		success, fail, errs := MigrateForMysqlOrSpider(apps, mysqlUids, m.Range, users)
		errs = append(errMsg, errs...)
		if len(errs) > 0 {
			slog.Info("migrate account rule fail")
			return success, fail, nil, nil, exUids, errno.MigrateFail.Add("\n" + strings.Join(errs, "\n"))
		}
		slog.Info("migrate account rule success")
		return success, fail, nil, nil, exUids, nil
	} else if m.Range == "spider" {
		success, fail, errs := MigrateForMysqlOrSpider(apps, uids, m.Range, users)
		errs = append(errMsg, errs...)
		if len(errs) > 0 {
			slog.Info("migrate account rule fail")
			return nil, nil, success, fail, exUids, errno.MigrateFail.Add("\n" + strings.Join(errs, "\n"))
		}
		slog.Info("migrate account rule success")
		return nil, nil, success, fail, exUids, nil
	} else {
		return nil, nil, nil, nil, nil, fmt.Errorf("不支持range值[%s]，支持mysql、spider", m.Range)
	}
}

// MigrateForMysqlOrSpider 迁移帐号和规则
func MigrateForMysqlOrSpider(apps map[string]int64, uids []string, vtype string, users []PrivModule) ([]PrivRule, []PrivRule, []string) {
	// 获取需要迁移的权限账号
	var dbType string
	var errs []string
	if vtype == "mysql" {
		dbType = mysql
	} else if vtype == "spider" {
		dbType = tendbcluster
	}
	var uidsSuccess, uidsFail []PrivRule
	// 迁移帐号
	err := DoAddAccounts(apps, users, dbType)
	if err != nil {
		slog.Error("DoAddAccounts", "dbType", vtype, "err", err)
		return uidsSuccess, uidsFail, []string{fmt.Sprintf("%s DoAddAccounts error: %s", vtype, err.Error())}
	}
	// 获取需要迁移的规则
	mysqlRules, err := GetRules(uids)
	if err != nil {
		slog.Error("GetRules", "dbType", vtype, "err", err)
		return uidsSuccess, uidsFail, []string{fmt.Sprintf("%s GetRules error: %s", vtype, err.Error())}
	}
	// 迁移账号规则
	// 遇到迁移失败的规则，提示并且跳过，继续迁移
	for _, rule := range mysqlRules {
		// 格式化权限
		priv, errInner := FormatPriv(rule.Privileges)
		if errInner != nil {
			slog.Error("format privileges error", rule.Privileges, errInner, "rule", rule)
			errs = append(errs, errInner.Error())
			uidsFail = append(uidsFail, PrivRule{rule.App, rule.User, rule.Dbname})
			continue
		}
		// 迁移规则
		errInner = DoAddAccountRule(rule, apps, dbType, priv)
		if errInner != nil {
			slog.Error("add account rule error", rule, errInner, "rule", rule)
			errs = append(errs, errInner.Error())
			uidsFail = append(uidsFail, PrivRule{rule.App, rule.User, rule.Dbname})
			continue
		}
		uidsSuccess = append(uidsSuccess, PrivRule{rule.App, rule.User, rule.Dbname})
	}
	// 返回迁移成功的规则以及失败的规则的uid
	return uidsSuccess, uidsFail, errs
}

// CheckPara 检查迁移帐号规则的参数
func (m *MigratePara) CheckPara() (map[string]int64, error) {
	tips := "apps为空，请设置需要迁移的app列表，多个app用逗号间隔，格式如\nAPPS='{\"test\":1, \"test2\":2}',名称区分大小写"
	if m.Apps == "" {
		slog.Error(tips)
		return nil, fmt.Errorf(tips)
	}
	apps, err := util.JsonToMap(m.Apps)
	if err != nil {
		slog.Error("apps格式错误，格式如'{\"test\":1, \"test2\":2}'", err)
		return nil, fmt.Errorf(tips)
	}
	if len(apps) == 0 {
		slog.Error(tips)
		return nil, fmt.Errorf(tips)
	}
	if m.Key == "" {
		slog.Error("key为空，请设置")
		return nil, fmt.Errorf("key为空，请设置")
	}
	if m.SapPassword == "" {
		slog.Error("sap_password为空，请设置")
		return nil, fmt.Errorf("sap_password为空，请设置")
	}
	if m.Mode != "check" && m.Mode != "run" && m.Mode != "force-run" {
		slog.Error(fmt.Sprintf(
			"mode值为:%s，请设置，可选模式\ncheck --- 仅检查不实施\nrun --- 检查并且迁移\nforce-run --- 强制执行", m.Mode))
		return nil, fmt.Errorf(
			"mode值为:%s,可选模式\ncheck --- 仅检查不实施\nrun --- 检查并且迁移\nforce-run --- 强制执行", m.Mode)
	}
	if !(m.Range == "mysql" || m.Range == "spider") {
		return nil, fmt.Errorf("不支持range值[%s]，支持mysql、spider", m.Range)
	}
	return apps, nil
}

// CheckOldPriv 检查旧的密码格式
func CheckOldPriv(key, appWhere, sap string, exclude *[]AppUser, dbmodule string) ([]PrivModule, []string) {
	slog.Info("begin check different privileges")
	// 检查是否存在多种权限，需要合并
	err1 := CheckDifferentPrivileges(appWhere, dbmodule)
	slog.Info("end check different privileges")
	slog.Info("CheckDifferentPrivileges", "error", err1)
	slog.Info("CheckDifferentPrivileges", "exclude", exclude)
	slog.Info("begin check privileges format")
	// 检查权限格式是否正确
	err2 := CheckPrivilegesFormat(appWhere, exclude, dbmodule)
	slog.Info("end check privileges format")
	slog.Info("CheckPrivilegesFormat", "error", err2)
	slog.Info("CheckPrivilegesFormat", "exclude", exclude)
	// 检查密码，并且获取帐号以及密码
	users, err3 := CheckAndGetPassword(key, appWhere, sap, exclude, dbmodule)
	slog.Info("CheckAndGetPassword", "error", err3)
	slog.Info("CheckAndGetPassword", "exclude", exclude)
	err := append(err1, err2...)
	err = append(err, err3...)
	return users, err
}

// MigrateAccountRuleInDbm DBM一个业务下的集群拆分到另一个业务，账号规则也需要迁移
func (m *MigrateInDbmPara) MigrateAccountRuleInDbm(jsonPara string, ticket string) ([]string, []string, error) {
	var targetAccounts []*TbAccounts
	var sourceAccounts []*TbAccounts
	var sourceRules []*TbAccountRules
	var conflictUsers []string
	var migrateUsers []string
	var userPara string
	var userIdFilter string
	var where, checkWhere, ruleWhere string
	var dbType string
	AddPrivLog(PrivLog{BkBizId: m.TargetBiz, Ticket: ticket, Operator: "dbm_clone", Para: jsonPara, Time: time.Now()})
	if m.ClusterType == nil {
		return nil, nil, errno.ClusterTypeIsEmpty
	}
	if *m.ClusterType == tendbha || *m.ClusterType == tendbsingle {
		dbType = mysql
	} else if *m.ClusterType == tendbcluster {
		dbType = tendbcluster
	} else {
		return nil, nil, errno.NotSupportedClusterType
	}
	if m.SourceBiz == 0 || m.TargetBiz == 0 {
		return nil, nil, errno.BkBizIdIsEmpty
	}
	base := fmt.Sprintf("bk_biz_id=%d and cluster_type='%s'", m.SourceBiz, dbType)
	where = base
	if len(m.Users) > 0 {
		userPara = strings.Join(m.Users, "','")
		where = fmt.Sprintf("%s and user in ('%s')", base, userPara)
	}
	// 查询有哪些账号需要迁移
	err := DB.Self.Model(&TbAccounts{}).Where(where).Scan(&sourceAccounts).Order("id").Error
	if err != nil {
		return nil, nil, err
	}
	if len(sourceAccounts) == 0 {
		return nil, nil, fmt.Errorf("no user to be cloned")
	}
	// 实际需要迁移的user
	for _, v := range sourceAccounts {
		migrateUsers = append(migrateUsers, (*v).User)
		userIdFilter = fmt.Sprintf("%s,%d", userIdFilter, (*v).Id)
	}
	userIdFilter = strings.TrimPrefix(userIdFilter, ",")
	userPara = strings.Join(migrateUsers, "','")
	// 检查目标业务下待迁移账号是否已经存在，存在不迁移
	checkWhere = fmt.Sprintf("bk_biz_id=%d and cluster_type='%s' and user in ('%s')", m.TargetBiz, dbType, userPara)
	err = DB.Self.Model(&TbAccounts{}).Where(checkWhere).Scan(&targetAccounts).Error
	if err != nil {
		return nil, nil, err
	}
	if len(targetAccounts) > 0 {
		for _, v := range targetAccounts {
			conflictUsers = append(conflictUsers, (*v).User)
		}
		return conflictUsers, nil, fmt.Errorf("some users already exist in target biz:%d", m.TargetBiz)
	}

	ruleWhere = fmt.Sprintf("%s and account_id in (%s)", base, userIdFilter)
	err = DB.Self.Model(&TbAccountRules{}).Where(ruleWhere).Scan(&sourceRules).Error
	if err != nil {
		return nil, nil, err
	}

	type MaxId struct {
		MaxId int `gorm:"column:max_id"`
	}
	maxId := MaxId{}
	queryMax := fmt.Sprintf("select auto_increment as max_id from information_schema.tables "+
		"where table_Schema ='%s' and table_name ='tb_accounts';", viper.GetString("db.name"))
	err = DB.Self.Raw(queryMax).Scan(&maxId).Error
	if err != nil {
		return nil, nil, err
	}
	diff := int64(maxId.MaxId) - (*sourceAccounts[0]).Id + 100
	tx := DB.Self.Begin()
	vtime := time.Now()
	// 读取的行数据，填充目标业务、更新账号id值、账号规则中的account_id等
	// 批量插入
	for _, v := range sourceAccounts {
		(*v).BkBizId = m.TargetBiz
		(*v).Id = (*v).Id + diff
		(*v).CreateTime = vtime
		(*v).UpdateTime = vtime
		(*v).Creator = "migrator"
		(*v).Operator = "migrator"
		err = tx.Model(&TbAccounts{}).Create(v).Error
		if err != nil {
			tx.Rollback()
			return nil, nil, err
		}
	}
	for _, v := range sourceRules {
		(*v).BkBizId = m.TargetBiz
		(*v).Id = 0
		(*v).AccountId = (*v).AccountId + diff
		(*v).CreateTime = vtime
		(*v).UpdateTime = vtime
		(*v).Creator = "migrator"
		(*v).Operator = "migrator"
		err = tx.Model(&TbAccountRules{}).Create(v).Error
		if err != nil {
			tx.Rollback()
			return nil, nil, err
		}
	}
	err = tx.Commit().Error
	if err != nil {
		return nil, nil, err
	}
	return nil, migrateUsers, nil
}

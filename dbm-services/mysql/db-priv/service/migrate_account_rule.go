package service

import (
	"fmt"
	"log/slog"
	"strings"

	"dbm-services/mysql/priv-service/util"
)

// MigrateAccountRule 迁移帐号规则
func (m *MigratePara) MigrateAccountRule() ([]PrivRule, []PrivRule, []PrivRule, []PrivRule, []int, error) {
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
	// 检查scr、gcs中的账号规则，mysql和spider的一起检查
	pass := CheckOldPriv(m.Key, appWhere, &exclude)
	notPassTips := "some check not pass, please check logs"
	passTips := "all check pass"
	// 仅检查，不迁移
	if m.Mode == "check" {
		if !pass {
			slog.Error(notPassTips)
			return nil, nil, nil, nil, nil, fmt.Errorf(notPassTips)
		} else {
			slog.Info(passTips)
			return nil, nil, nil, nil, nil, nil
		}
	} else if m.Mode == "run" {
		// 检查通过迁移，检查不通过不迁移
		if !pass {
			slog.Error(fmt.Sprintf("%s, do not migrate", notPassTips))
			return nil, nil, nil, nil, nil, fmt.Errorf("%s, do not migrate", notPassTips)
		} else {
			slog.Info(passTips)
		}
	} else if m.Mode == "force-run" {
		// 检查不通过，剔除不能迁移的帐号以及其规则，迁移剩余的账号规则
		if !pass {
			slog.Warn(fmt.Sprintf("%s, but force run", notPassTips))
			slog.Warn("user can not be migrated", "users", exclude)
		} else {
			slog.Info(passTips)
		}
	}

	// 获取需要迁移的scr、gcs中的账号规则
	// db_module为spider_master/spider_slave属于spider的权限规则，
	// 其他不明确的，同时迁移到mysql和spider下
	mysqlUids, uids, exUids, errOuter := FilterMigratePriv(appWhere, &exclude)
	if errOuter != nil {
		slog.Error("get privilege uid to migrate", "err", errOuter)
		return nil, nil, nil, nil, nil, fmt.Errorf("get privilege uid to migrate error: %s", errOuter.Error())
	}

	// 经过检查不能迁移
	tipsCannotMigrate := "some accounts and rules belonging to them can't be migrated"

	var failFlag bool
	if m.Mode == "force-run" && len(exUids) > 0 {
		failFlag = true
	}
	if m.Range == "mysql" {
		success, fail, errs := MigrateForMysqlOrSpider(apps, m.Key, mysqlUids, m.Range)
		if failFlag {
			errs = append(errs, tipsCannotMigrate)
		}
		if len(errs) > 0 {
			slog.Info("migrate account rule fail")
			return success, fail, nil, nil, exUids, fmt.Errorf("errors: %s", strings.Join(errs, "\n"))
		}
		slog.Info("migrate account rule success")
		return success, fail, nil, nil, exUids, nil
	} else if m.Range == "spider" {
		success, fail, errs := MigrateForMysqlOrSpider(apps, m.Key, uids, m.Range)
		if failFlag {
			errs = append(errs, tipsCannotMigrate)
		}
		if len(errs) > 0 {
			slog.Info("migrate account rule fail")
			return nil, nil, success, fail, exUids, fmt.Errorf("errors: %s", strings.Join(errs, "\n"))
		}
		slog.Info("migrate account rule success")
		return nil, nil, success, fail, exUids, nil
	} else if m.Range == "all" {
		success, fail, errs := MigrateForMysqlOrSpider(apps, m.Key, mysqlUids, "mysql")
		successSpider, failSpider, errs1 := MigrateForMysqlOrSpider(apps, m.Key, mysqlUids, "spider")
		errs = append(errs, errs1...)
		if failFlag {
			errs = append(errs, tipsCannotMigrate)
		}
		if len(errs) > 0 {
			slog.Info("migrate account rule fail")
			return success, fail, successSpider, failSpider, exUids, fmt.Errorf(
				"errors: %s", strings.Join(errs, "\n"))
		}
		slog.Info("migrate account rule success")
		return success, fail, successSpider, failSpider, exUids, nil
	} else {
		return nil, nil, nil, nil, nil, fmt.Errorf("不支持range值[%s]，支持all、mysql、spider", m.Range)
	}
}

func MigrateForMysqlOrSpider(apps map[string]int64, vkey string, uids []string, vtype string) ([]PrivRule, []PrivRule, []string) {
	// 获取需要迁移的权限账号
	var dbType string
	var errs []string
	if vtype == "mysql" {
		dbType = mysql
	} else if vtype == "spider" {
		dbType = tendbcluster
	}
	var uidsSuccess, uidsFail []PrivRule
	mysqlUsers, err := GetUsers(vkey, uids)
	if err != nil {
		slog.Error("GetUsers", "dbType", vtype, "err", err)
		return uidsSuccess, uidsFail, []string{fmt.Sprintf("%s GetUsers error: %s", vtype, err.Error())}
	}

	err = DoAddAccounts(apps, mysqlUsers, dbType)
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
		priv, errInner := FormatPriv(rule.Privileges)
		if errInner != nil {
			slog.Error("format privileges error", rule.Privileges, errInner, "rule", rule)
			errs = append(errs, errInner.Error())
			uidsFail = append(uidsFail, PrivRule{rule.App, rule.User, rule.Dbname})
			continue
		}
		errInner = DoAddAccountRule(rule, apps, dbType, priv)
		if errInner != nil {
			slog.Error("add account rule error", rule, errInner, "rule", rule)
			errs = append(errs, errInner.Error())
			uidsFail = append(uidsFail, PrivRule{rule.App, rule.User, rule.Dbname})
			continue
		}
		uidsSuccess = append(uidsSuccess, PrivRule{rule.App, rule.User, rule.Dbname})
	}
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
	if m.Mode != "check" && m.Mode != "run" && m.Mode != "force-run" {
		slog.Error(fmt.Sprintf(
			"mode值为:%s，请设置，可选模式\ncheck --- 仅检查不实施\nrun --- 检查并且迁移\nforce-run --- 强制执行", m.Mode))
		return nil, fmt.Errorf(
			"mode值为:%s,可选模式\ncheck --- 仅检查不实施\nrun --- 检查并且迁移\nforce-run --- 强制执行", m.Mode)
	}
	if !(m.Range == "all" || m.Range == "mysql" || m.Range == "spider") {
		return nil, fmt.Errorf("不支持range值[%s]，支持all、mysql、spider", m.Range)
	}
	return apps, nil
}

// CheckOldPriv 检查旧的密码格式
func CheckOldPriv(key, appWhere string, exclude *[]AppUser) bool {
	err1 := CheckDifferentPasswordsForOneUser(key, appWhere, exclude)
	err2 := CheckEmptyPassword(key, appWhere, exclude)
	// 如果原本的用户名与密码相同允许创建，dbm兼容
	// err3 := CheckPasswordConsistentWithUser(key, appWhere, exclude)
	err3 := CheckPasswordMaybeOldPassword(key, appWhere, exclude)
	err4 := CheckDifferentPrivileges(appWhere)
	err5 := CheckPrivilegesFormat(appWhere, exclude)
	if err1 != nil || err2 != nil || err3 != nil || err4 != nil || err5 != nil {
		return false
	}
	return true
}

package service

import (
	"fmt"
	"log/slog"
	"strings"

	"dbm-services/mysql/priv-service/util"
)

// MigrateAccountRule 迁移帐号规则
func (m *MigratePara) MigrateAccountRule() error {
	apps, err := m.CheckPara()
	if err != nil {
		return err
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
	// 检查scr、gcs中的账号规则
	pass := CheckOldPriv(m.Key, appWhere, &exclude)
	notPassTips := "some check not pass, please check logs"
	passTips := "all check pass"
	// 仅检查，不迁移
	if m.Mode == "check" {
		if !pass {
			slog.Error(notPassTips)
			return fmt.Errorf(notPassTips)
		} else {
			slog.Info(passTips)
			return nil
		}
	} else if m.Mode == "run" {
		// 检查通过迁移，检查不通过不迁移
		if !pass {
			slog.Error(fmt.Sprintf("%s, do not migrate", notPassTips))
			return fmt.Errorf("%s, do not migrate", notPassTips)
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
	mysqlUids, uids, exUids, err := FilterMigratePriv(appWhere, &exclude)
	if err != nil {
		slog.Error("FilterMigratePriv", "err", err)
		return fmt.Errorf("FilterMigratePriv error: %s", err.Error())
	}
	// 获取需要迁移的权限账号
	mysqlUsers, err := GetUsers(m.Key, mysqlUids)
	if err != nil {
		slog.Error("GetUsers", "err", err)
		return fmt.Errorf("GetUsers error: %s", err.Error())
	}

	allUsers, err := GetUsers(m.Key, uids)
	if err != nil {
		slog.Error("GetUsers", "err", err)
		return fmt.Errorf("GetUsers error: %s", err.Error())
	}

	// 迁移账号
	// 遇到帐号迁移失败就终止
	err = DoAddAccounts(apps, allUsers, tendbcluster)
	if err != nil {
		slog.Error("DoAddAccounts", err)
		return fmt.Errorf("DoAddAccounts error: %s", err.Error())
	}
	err = DoAddAccounts(apps, mysqlUsers, mysql)
	if err != nil {
		slog.Error("DoAddAccounts", err)
		return fmt.Errorf("DoAddAccounts error: %s", err.Error())
	}
	slog.Info("migrate account success")

	// 获取需要迁移的规则
	mysqlRules, err := GetRules(mysqlUids)
	if err != nil {
		slog.Error("GetRules", "err", err)
		return fmt.Errorf("GetRules error: %s", err.Error())
	}

	allRules, err := GetRules(uids)
	if err != nil {
		slog.Error("GetRules", "err", err)
		return fmt.Errorf("GetRules error: %s", err.Error())
	}

	// 迁移账号规则
	// 遇到迁移失败的规则，提示并且跳过，继续迁移
	var ruleFail bool
	for _, rule := range mysqlRules {
		priv, errInner := FormatPriv(rule.Privileges)
		if errInner != nil {
			slog.Error("format privileges error", rule.Privileges, errInner, "rule", rule)
			ruleFail = true
			continue
		}
		errInner = DoAddAccountRule(rule, apps, "mysql", priv)
		if errInner != nil {
			slog.Error("add account rule error", rule, errInner, "rule", rule)
			ruleFail = true
		}
	}

	for _, rule := range allRules {
		// 格式化权限
		priv, errInner := FormatPriv(rule.Privileges)
		if errInner != nil {
			slog.Error("format privileges", rule.Privileges, errInner)
			ruleFail = true
			continue
		}
		// 添加帐号
		errInner = DoAddAccountRule(rule, apps, "tendbcluster", priv)
		if errInner != nil {
			slog.Error("add account rule error", rule, errInner, "rule", rule)
			ruleFail = true
		}
	}
	// 经过检查不能迁移
	tipsCannotMigrate := "some accounts and rules belonging to them can't be migrated"
	// 可以迁移但是迁移失败
	tipsMigrateFail := "some rules migrate failed"
	tipsCheckLog := "check log"

	if m.Mode == "force-run" && len(exclude) > 0 {
		slog.Error("users can't be migrated", "users", exclude)
		slog.Error("rules can't be migrated", "uids in gcs", exUids)
		if ruleFail {
			return fmt.Errorf("force-run mode, %s, %s, %s", tipsCannotMigrate, tipsMigrateFail, tipsCheckLog)
		}
		return fmt.Errorf("force-run mode, %s，%s", tipsCannotMigrate, tipsCheckLog)
	}
	if ruleFail {
		return fmt.Errorf("%s, %s", tipsMigrateFail, tipsCheckLog)
	}
	slog.Info("migrate account rule success")
	return nil
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

package service

import (
	"dbm-services/mysql/priv-service/util"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"strconv"
	"strings"

	"golang.org/x/exp/slog"
)

var GcsDb *Database

type Count struct {
	AppUser
	Dbname string `json:"dbname" gorm:"column:dbname"`
	Cnt    int64  `json:"cnt" gorm:"column:cnt"`
}

type AppUser struct {
	App  string `json:"app" gorm:"column:app"`
	User string `json:"user" gorm:"column:user"`
}

// PrivModule scr、gcs账号规则的结构
type PrivModule struct {
	Uid        int64  `json:"uid" gorm:"column:uid"`
	App        string `json:"app" gorm:"column:app"`
	DbModule   string `json:"db_module" gorm:"column:db_module"`
	Module     string `json:"module" gorm:"column:module"`
	User       string `json:"user" gorm:"column:user"`
	Dbname     string `json:"dbname" gorm:"column:dbname"`
	Psw        string `json:"psw" gorm:"column:psw"`
	Privileges string `json:"privileges" gorm:"column:privileges"`
	Comment    string `json:"comment"  gorm:"column:comment"`
}

// MigratePara 迁移帐号规则的入参
type MigratePara struct {
	GcsDb DbConf `json:"gcs_db"`
	Apps  string `json:"apps" `
	Key   string `json:"key"`
	Mode  string `json:"mode"`
}

// DbConf 帐号规则所在数据库的配置
type DbConf struct {
	User string `json:"user"`
	Psw  string `json:"password"`
	Name string `json:"name"`
	Host string `json:"host"`
	Port string `json:"port"`
}

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
	defer GcsDb.Close()
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
		// 检查不通过，剔除不能迁移的帐号规则，迁移剩余的账号规则
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
	mysqlUids, uids, err := FilterMigratePriv(appWhere, &exclude)
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
	for _, rule := range mysqlRules {
		priv, errInner := FormatPriv(rule.Privileges)
		if errInner != nil {
			slog.Error("format privileges", rule.Privileges, errInner)
			continue
		}
		errInner = DoAddAccountRule(rule, apps, "mysql", priv)
		if errInner != nil {
			slog.Error("AddAccountAndRule error", rule, errInner)
		}
	}

	for _, rule := range allRules {
		// 格式化权限
		priv, errInner := FormatPriv(rule.Privileges)
		if errInner != nil {
			slog.Error("format privileges", rule.Privileges, errInner)
			continue
		}
		// 添加帐号
		errInner = DoAddAccountRule(rule, apps, "tendbcluster", priv)
		if errInner != nil {
			slog.Error("AddAccountAndRule error", rule, errInner)
		}
	}
	slog.Info("migrate account rule success")
	if m.Mode == "force-run" {
		return fmt.Errorf("force-run ")
	}
	return nil
}

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

func CheckOldPriv(key, appWhere string, exclude *[]AppUser) bool {
	err1 := CheckDifferentPasswordsForOneUser(key, appWhere, exclude)
	err2 := CheckEmptyPassword(key, appWhere, exclude)
	err3 := CheckPasswordConsistentWithUser(key, appWhere, exclude)
	err4 := CheckDifferentPrivileges(appWhere, exclude)
	err5 := CheckPrivilegesFormat(appWhere, exclude)
	if err1 != nil || err2 != nil || err3 != nil || err4 != nil || err5 != nil {
		return false
	}
	return true
}

func CheckDifferentPasswordsForOneUser(key, appWhere string, exclude *[]AppUser) error {
	slog.Info("check 1: different passwords for one user")
	count := make([]*Count, 0)
	vsql := fmt.Sprintf("select app,user,count(distinct(AES_DECRYPT(psw,'%s'))) as cnt "+
		" from tb_app_priv_module where app in (%s) group by app,user order by 1,2", key, appWhere)
	err := GcsDb.Self.Debug().Raw(vsql).Scan(&count).Error
	if err != nil {
		slog.Error(vsql, "execute error", err)
		return err
	}

	check1 := make([]string, 0)
	for _, distinct := range count {
		if distinct.Cnt > 1 {
			check1 = append(check1,
				fmt.Sprintf("%s    %s     %d",
					distinct.App, distinct.User, distinct.Cnt))
			*exclude = append(*exclude, AppUser{distinct.App, distinct.User})
		}
	}
	if len(check1) > 0 {
		msg := "app:    user:     different_passwords_count:"
		msg = fmt.Sprintf("\n%s\n%s", msg, strings.Join(check1, "\n"))
		slog.Error(msg)
		slog.Error("[ check 1 Fail ]")
		return fmt.Errorf("different passwords for one user")
	} else {
		slog.Info("[ check 1 Success ]")
	}
	return nil
}

func CheckEmptyPassword(key, appWhere string, exclude *[]AppUser) error {
	vsql := fmt.Sprintf("select distinct app,user "+
		" from tb_app_priv_module where app in (%s) and psw=AES_ENCRYPT('','%s');", appWhere, key)
	slog.Info("check 2: empty password")
	err := CheckPasswordValue(vsql, exclude, 2)
	if err != nil {
		slog.Error("CheckPassword", "error", err)
		return err
	}
	return nil
}

func CheckPasswordConsistentWithUser(key, appWhere string, exclude *[]AppUser) error {
	vsql := fmt.Sprintf("select distinct app,user "+
		" from tb_app_priv_module where app in (%s) and user=AES_DECRYPT(psw,'%s');", appWhere, key)
	slog.Info("check 3: password consistent with user")
	err := CheckPasswordValue(vsql, exclude, 3)
	if err != nil {
		slog.Error("CheckPassword", "error", err)
		return err
	}
	return nil
}

func CheckPasswordValue(vsql string, exclude *[]AppUser, round int) error {
	psw := make([]*PrivModule, 0)
	err := GcsDb.Self.Debug().Raw(vsql).Scan(&psw).Error
	if err != nil {
		slog.Error(vsql, "execute error", err)
		return err
	}
	if len(psw) > 0 {
		msg := fmt.Sprintf("app:    user: ")
		for _, user := range psw {
			*exclude = append(*exclude, AppUser{user.App, user.User})
			msg = fmt.Sprintf("%s\n%s    %s", msg, user.App, user.User)
		}
		slog.Error(msg)
		slog.Error(fmt.Sprintf("[ check %d Fail ]", round))
		return fmt.Errorf("password check fail")
	} else {
		slog.Info(fmt.Sprintf("[ check %d Success ]", round))
	}
	return nil
}

func CheckDifferentPrivileges(appWhere string, exclude *[]AppUser) error {
	slog.Info("check 4: different privileges for [app user dbname]")
	vsql := fmt.Sprintf("select app,user,dbname,count(distinct(privileges)) as cnt "+
		" from tb_app_priv_module where app in (%s) group by app,user,dbname order by 1,2,3", appWhere)
	count := make([]*Count, 0)
	err := GcsDb.Self.Debug().Raw(vsql).Scan(&count).Error
	if err != nil {
		slog.Error(vsql, "execute error", err)
		return err
	}
	check := make([]string, 0)
	for _, distinct := range count {
		if distinct.Cnt > 1 {
			check = append(check,
				fmt.Sprintf("%s    %s     %s     %d",
					distinct.App, distinct.User, distinct.Dbname, distinct.Cnt))
			*exclude = append(*exclude, AppUser{distinct.App, distinct.User})
		}
	}
	if len(check) > 0 {
		msg := "app:    user:     dbname:     different_privileges_count:"
		msg = fmt.Sprintf("\n%s\n%s", msg, strings.Join(check, "\n"))
		slog.Error(msg)
		slog.Error("[ check 4 Fail ]")
		return fmt.Errorf("different privileges")
	} else {
		slog.Info("[ check 4 Success ]")
	}
	return nil
}

func CheckPrivilegesFormat(appWhere string, exclude *[]AppUser) error {
	UniqMap := make(map[string]struct{})
	privPass := true
	slog.Info("check 5: check privileges format")
	vsql := fmt.Sprintf("select uid,app,user,privileges "+
		" from tb_app_priv_module where app in (%s)", appWhere)
	rules := make([]*PrivModule, 0)
	err := GcsDb.Self.Debug().Raw(vsql).Scan(&rules).Error
	if err != nil {
		slog.Error(vsql, "execute error", err)
		return err
	}
	for _, rule := range rules {
		_, err = FormatPriv(rule.Privileges)
		if err != nil {
			privPass = false
			slog.Error("msg", "uid", rule.Uid, "app", rule.App, "user", rule.User, "privileges", rule.Privileges, "error", err)
		}
		s := fmt.Sprintf("%s|%s", rule.App, rule.User)
		if _, isExists := UniqMap[s]; isExists == true {
			continue
		}
		UniqMap[s] = struct{}{}
		*exclude = append(*exclude, AppUser{rule.App, rule.User})
	}
	if !privPass {
		slog.Error("[ check 5 Fail ]")
		return fmt.Errorf("wrong privileges")
	} else {
		slog.Info("[ check 5 Success ]")
	}
	return nil
}

func FilterMigratePriv(appWhere string, exclude *[]AppUser) ([]string, []string, error) {
	all := make([]*PrivModule, 0)
	uids := make([]string, 0)
	mysqlUids := make([]string, 0)
	vsql := fmt.Sprintf("select uid,app,db_module,user "+
		" from tb_app_priv_module where app in (%s);", appWhere)
	err := GcsDb.Self.Debug().Raw(vsql).Scan(&all).Error
	if err != nil {
		slog.Error(vsql, "execute error", err)
		return mysqlUids, uids, err
	}

	for _, module := range all {
		var excludeFlag bool
		for _, v := range *exclude {
			if module.App == v.App && module.User == v.User {
				excludeFlag = true
				break
			}
		}
		if excludeFlag == false {
			suid := strconv.FormatInt(module.Uid, 10)
			uids = append(uids, suid)
			if module.DbModule != "spider_master" && module.DbModule != "spider_slave" {
				mysqlUids = append(mysqlUids, suid)
			}
		}
	}
	if len(uids) == 0 {
		slog.Warn("no rule should be migrated")
	}
	return mysqlUids, uids, err
}

func GetUsers(key string, uids []string) ([]*PrivModule, error) {
	users := make([]*PrivModule, 0)
	vsql := fmt.Sprintf("select distinct app,user,AES_DECRYPT(psw,'%s') as psw"+
		" from tb_app_priv_module where uid in (%s);",
		key, strings.Join(uids, ","))
	err := GcsDb.Self.Debug().Raw(vsql).Scan(&users).Error
	if err != nil {
		slog.Error(vsql, "execute error", err)
		return users, err
	}
	return users, nil
}

func GetRules(uids []string) ([]*PrivModule, error) {
	users := make([]*PrivModule, 0)
	vsql := fmt.Sprintf("select distinct app,user,privileges,dbname "+
		" from tb_app_priv_module where uid in (%s);", strings.Join(uids, ","))
	err := GcsDb.Self.Debug().Raw(vsql).Scan(&users).Error
	if err != nil {
		slog.Error(vsql, "execute error", err)
		return users, err
	}
	return users, nil
}

// FormatPriv
// SELECT,INSERT,UPDATE,DELETE 转换为 {"dml":"select,update","ddl":"create","global":"REPLICATION SLAVE"}
func FormatPriv(source string) (map[string]string, error) {
	target := make(map[string]string, 4)
	if source == "" {
		return target, fmt.Errorf("privilege is null")
	}
	source = strings.ToLower(source)
	privs := strings.Split(source, ",")
	var dml, ddl, global []string
	var allPrivileges bool
	for _, p := range privs {
		p = strings.TrimPrefix(p, " ")
		p = strings.TrimSuffix(p, " ")
		if p == "select" || p == "insert" || p == "update" || p == "delete" {
			dml = append(dml, p)
		} else if p == "create" || p == "alter" || p == "drop" || p == "index" || p == "execute" || p == "create view" {
			ddl = append(ddl, p)
		} else if p == "file" || p == "trigger" || p == "event" || p == "create routine" || p == "alter routine" ||
			p == "replication client" || p == "replication slave" {
			global = append(global, p)
		} else if p == "all privileges" {
			global = append(global, p)
			allPrivileges = true
		} else {
			return target, fmt.Errorf("privilege: %s not allowed", p)
		}
	}
	if allPrivileges && (len(global) > 1 || len(dml) > 0 || len(ddl) > 0) {
		return target, fmt.Errorf("[all privileges] should not be granted with others")
	}
	target["dml"] = strings.Join(dml, ",")
	target["ddl"] = strings.Join(ddl, ",")
	target["global"] = strings.Join(global, ",")
	return target, nil
}

func DoAddAccounts(apps map[string]int64, users []*PrivModule, clusterType string) error {
	for _, user := range users {
		psw := base64.StdEncoding.EncodeToString([]byte(user.Psw))
		account := AccountPara{BkBizId: apps[user.App], User: user.User,
			Psw: psw, Operator: "migrate", ClusterType: &clusterType, MigrateFlag: true}
		log, _ := json.Marshal(account)
		err := account.AddAccount(string(log))
		if err != nil {
			slog.Error("add account error", account, err)
			return err
		}
	}
	return nil
}

func DoAddAccountRule(rule *PrivModule, apps map[string]int64, clusterType string, priv map[string]string) error {
	account := AccountPara{BkBizId: apps[rule.App], User: rule.User, ClusterType: &clusterType}
	items, cnt, err := account.GetAccount()
	if err != nil {
		return fmt.Errorf("add rule failed when get account: %s", err.Error())
	}
	if cnt == 0 {
		slog.Error("msg", "account query nothing return", account)
		return fmt.Errorf("account not found")
	}
	rulePara := AccountRulePara{BkBizId: apps[rule.App], ClusterType: &clusterType, AccountId: items[0].Id,
		Dbname: rule.Dbname, Priv: priv, Operator: "migrate"}
	log, _ := json.Marshal(rulePara)
	err = rulePara.AddAccountRule(string(log))
	if err != nil {
		return fmt.Errorf("add rule failed: %s", err.Error())
	}
	return nil
}

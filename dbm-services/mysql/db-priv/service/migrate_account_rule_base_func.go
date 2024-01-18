package service

import (
	"encoding/json"
	"fmt"
	"log/slog"
	"regexp"
	"sort"
	"strconv"
	"strings"
)

// FilterMigratePriv 过滤不能迁移的帐号规则
func FilterMigratePriv(appWhere string, exclude *[]AppUser) ([]string, []string, []int, error) {
	all := make([]*PrivModule, 0)
	uids := make([]string, 0)
	mysqlUids := make([]string, 0)
	exUids := make([]int, 0)

	// 获取所有的帐号规则
	vsql := fmt.Sprintf("select uid,app,db_module,user "+
		" from tb_app_priv_module where app in (%s);", appWhere)
	err := GcsDb.Self.Debug().Raw(vsql).Scan(&all).Error
	if err != nil {
		slog.Error(vsql, "execute error", err)
		return mysqlUids, uids, exUids, err
	}

	for _, module := range all {
		var excludeFlag bool
		// 剔除不能迁移的帐号规则
		for _, v := range *exclude {
			if module.App == v.App && module.User == v.User {
				excludeFlag = true
				break
			}
		}
		if !excludeFlag {
			suid := strconv.Itoa(module.Uid)
			uids = append(uids, suid)
			// gcs spider_master 、spider_slave 的帐号规则不被添加到dbm tendbha的帐号规则中
			if module.DbModule != "spider_master" && module.DbModule != "spider_slave" {
				mysqlUids = append(mysqlUids, suid)
			}
		} else {
			exUids = append(exUids, module.Uid)
		}
	}
	if len(uids) == 0 && len(mysqlUids) == 0 {
		slog.Warn("no rule should be migrated")
	}
	return mysqlUids, uids, exUids, err
}

// GetRules 获取规则
func GetRules(uids []string) ([]*PrivModule, error) {
	users := make([]*PrivModule, 0)
	if len(uids) == 0 {
		return users, nil
	}
	// 获取规则，整合权限
	vsql := fmt.Sprintf("select app,user,group_concat(privileges) as privileges,dbname "+
		" from tb_app_priv_module where uid in (%s) group by app,user,dbname;", strings.Join(uids, ","))
	err := GcsDb.Self.Debug().Raw(vsql).Scan(&users).Error
	if err != nil {
		slog.Error(vsql, "execute error", err)
		return users, err
	}
	return users, nil
}

// FormatPriv 格式化权限
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
		// dml权限
		if p == "select" || p == "insert" || p == "update" || p == "delete" {
			dml = append(dml, p)
			// ddl权限
		} else if p == "create" || p == "alter" || p == "drop" || p == "index" || p == "execute" || p == "create view" {
			ddl = append(ddl, p)
			// global 权限
		} else if p == "file" || p == "trigger" || p == "event" || p == "create routine" || p == "alter routine" ||
			p == "replication client" || p == "replication slave" {
			global = append(global, p)
			// global 权限
		} else if p == "all privileges" {
			global = append(global, p)
			allPrivileges = true
		} else if p != "" {
			return target, fmt.Errorf("privilege: %s not allowed", p)
		}
	}
	// all privileges 与其他权限互斥
	if allPrivileges && (len(RemoveRepeate(global)) > 1 || len(dml) > 0 || len(ddl) > 0) {
		return target, fmt.Errorf("[all privileges] should not be granted with others")
	}
	target["dml"] = strings.Join(RemoveRepeate(dml), ",")
	target["ddl"] = strings.Join(RemoveRepeate(ddl), ",")
	target["global"] = strings.Join(RemoveRepeate(global), ",")
	return target, nil
}

// DoAddAccounts 创建帐号
func DoAddAccounts(apps map[string]int64, users []PrivModule, clusterType string) error {
	for _, user := range users {
		account := AccountPara{BkBizId: apps[user.App], User: user.User,
			Psw: user.Psw, Operator: "migrate", ClusterType: &clusterType, MigrateFlag: true}
		// 如果是password()格式，特殊处理
		if MysqlPassword(user.Psw) {
			account = AccountPara{BkBizId: apps[user.App], User: user.User,
				Psw: user.Psw, Operator: "migrate", ClusterType: &clusterType,
				MigrateFlag: true, PasswordFunc: true}
		}
		log, _ := json.Marshal(account)
		// 添加帐号
		err := account.AddAccount(string(log))
		if err != nil {
			slog.Error("add account error", account, err)
			return err
		}
	}
	return nil
}

// DoAddAccountRule 创建帐号规则
func DoAddAccountRule(rule *PrivModule, apps map[string]int64, clusterType string, priv map[string]string) error {
	account := AccountPara{BkBizId: apps[rule.App], User: rule.User, ClusterType: &clusterType}
	items, cnt, err := account.GetAccount()
	if err != nil {
		return fmt.Errorf("add rule failed when get account: %s", err.Error())
	}
	// 创建规则前先确认规则所属的帐号已经存在
	if cnt == 0 {
		slog.Error("msg", "account query nothing return", account)
		return fmt.Errorf("account not found")
	}
	rulePara := AccountRulePara{BkBizId: apps[rule.App], ClusterType: &clusterType, AccountId: items[0].Id,
		Dbname: rule.Dbname, Priv: priv, Operator: "migrate"}
	log, _ := json.Marshal(rulePara)
	// 添加帐号规则
	err = rulePara.AddAccountRule(string(log))
	if err != nil {
		return fmt.Errorf("add rule failed: %s", err.Error())
	}
	return nil
}

// CheckAndGetPassword 检查以及获取密码
func CheckAndGetPassword(key, appWhere string, exclude *[]AppUser) ([]PrivModule, []string) {
	users := make([]*PrivModule, 0)
	var errMsg []string
	var migrateUsers []PrivModule
	type Psw struct {
		Psw string `gorm:"column:psw;not_null" json:"psw"`
	}
	vsql := fmt.Sprintf("select app,user,AES_DECRYPT(psw,'%s') as psw"+
		" from tb_app_priv_module where app in (%s)", key, appWhere)
	if len(*exclude) > 0 {
		var where string
		for _, ex := range *exclude {
			where = fmt.Sprintf("%sor (app='%s' and user='%s') ", where, ex.App, ex.User)
		}
		where = strings.TrimPrefix(where, "or ")
		vsql = fmt.Sprintf("%s and not (%s)", vsql, where)
	}
	err := GcsDb.Self.Debug().Raw(vsql).Scan(&users).Error
	if err != nil {
		slog.Error(vsql, "execute sql error", err)
		return migrateUsers, []string{fmt.Sprintf("execute sql error: %s", err.Error())}
	}
	var emptyList []AppUser
	var oldPasswordList []AppUser
	var diffentPassword []AppUser
	tmp := make(map[string][]string)
	for _, user := range users {
		userPsw := fmt.Sprintf("%s|||%s", user.App, user.User)
		tmp[userPsw] = append(tmp[userPsw], user.Psw)
	}
	slog.Info("users map", "users", tmp)
	// 去重
	vmap := make(map[string][]string)
	for k, v := range tmp {
		unique := RemoveRepeate(v)
		vmap[k] = unique
	}
	slog.Info("users密码去重", "users", vmap)
	for k, v := range vmap {
		vlist := strings.Split(k, "|||")
		a := vlist[0]
		u := vlist[1]
		empty := false
		oldPassword := false
		var passwordFuncList []string
		var plainList []string
		for _, psw := range v {
			if psw == "" {
				empty = true
				break
			} else if MysqlOldPassword(psw) {
				oldPassword = true
				break
			} else if MysqlPassword(psw) {
				passwordFuncList = append(passwordFuncList, psw)
			} else {
				plainList = append(plainList, psw)
			}
		}
		// 密码为空不迁移
		if empty {
			slog.Error("密码为空", "app", a, "user", u)
			emptyList = append(emptyList, AppUser{a, u})
		} else if oldPassword {
			// 密码为old_password()不迁移
			slog.Error("密码为old_password", "app", a, "user", u)
			oldPasswordList = append(oldPasswordList, AppUser{a, u})
		} else if len(passwordFuncList) == 1 && len(plainList) == 1 {
			// 同时存在明文和password()两种格式
			var en Psw
			// 获取明文对应的password()值
			errInner := DBVersion56.Self.Table("user").Select("PASSWORD(?) AS psw", plainList[0]).Take(&en).
				Error
			if errInner != nil {
				slog.Error("use password() func", "errror", errInner)
				return migrateUsers, append(errMsg, fmt.Sprintf("use password() func error: %s",
					errInner.Error()))
			}
			// 明文和password()的密码相同
			if en.Psw == passwordFuncList[0] {
				slog.Warn("包含plain and password()，但是密码相同", "app", a, "user", u)
				migrateUsers = append(migrateUsers, PrivModule{App: a, User: u, Psw: plainList[0]})
			} else {
				slog.Error("包含plain and password()，但是密码不同", "app", a, "user", u)
				diffentPassword = append(diffentPassword, AppUser{a, u})
			}
		} else if len(plainList) == 1 && len(passwordFuncList) == 0 {
			migrateUsers = append(migrateUsers, PrivModule{App: a, User: u, Psw: plainList[0]})
		} else if len(passwordFuncList) == 1 && len(plainList) == 0 {
			migrateUsers = append(migrateUsers, PrivModule{App: a, User: u, Psw: passwordFuncList[0]})
		} else {
			slog.Error("密码不同", "app", a, "user", u)
			diffentPassword = append(diffentPassword, AppUser{a, u})
		}
	}
	// exclude用于过滤掉不可迁移的帐号以及帐号下的规则
	if len(emptyList) > 0 {
		errMsg = append(errMsg, fmt.Sprintf("密码为空不可迁移:%v", emptyList))
		*exclude = append(*exclude, emptyList...)
	}
	if len(oldPasswordList) > 0 {
		errMsg = append(errMsg, fmt.Sprintf("密码为old_password不可迁移:%v", oldPasswordList))
		*exclude = append(*exclude, oldPasswordList...)
	}
	if len(diffentPassword) > 0 {
		errMsg = append(errMsg, fmt.Sprintf("同账号存在不同的密码不可迁移:%v", diffentPassword))
		*exclude = append(*exclude, diffentPassword...)
	}
	return migrateUsers, errMsg
}

// CheckDifferentPrivileges 同账号有不同的权限范围
func CheckDifferentPrivileges(appWhere string) []string {
	var errMsg []string
	vsql := fmt.Sprintf("select app,user,dbname,count(distinct(privileges)) as cnt "+
		" from tb_app_priv_module where app in (%s) group by app,user,dbname order by 1,2,3", appWhere)
	count := make([]*Count, 0)
	err := GcsDb.Self.Debug().Raw(vsql).Scan(&count).Error
	if err != nil {
		slog.Error(vsql, "execute sql error", err)
		return []string{fmt.Sprintf("execute sql error: %s", err.Error())}
	}
	check := make([]string, 0)
	for _, distinct := range count {
		if distinct.Cnt > 1 {
			check = append(check,
				fmt.Sprintf("%s    %s     %s     %d",
					distinct.App, distinct.User, distinct.Dbname, distinct.Cnt))
		}
	}
	if len(check) > 0 {
		// 权限不同的规则可以合并
		slog.Error("app+user+dbname存在不同的权限，将被合并")
		errMsg = append(errMsg, "app+user+dbname存在不同的权限，将被合并")
		errMsg = append(errMsg, "app:    user:     dbname:     different_privileges_count:")
		errMsg = append(errMsg, check...)
		return errMsg
	}
	return nil
}

// CheckPrivilegesFormat 检查权限格式
func CheckPrivilegesFormat(appWhere string, exclude *[]AppUser) []string {
	var errMsg []string
	UniqMap := make(map[string]struct{})
	vsql := fmt.Sprintf("select uid,app,user,dbname,privileges "+
		" from tb_app_priv_module where app in (%s)", appWhere)
	rules := make([]*PrivModule, 0)
	err := GcsDb.Self.Debug().Raw(vsql).Scan(&rules).Error
	if err != nil {
		slog.Error(vsql, "execute sql error", err)
		return []string{fmt.Sprintf("execute sql error: %s", err.Error())}
	}
	check := make([]string, 0)
	// 找出需要过滤的app+user
	for _, rule := range rules {
		// 检查权限格式是否正确、是否存在冲突等
		_, err = FormatPriv(rule.Privileges)
		if err != nil {
			slog.Error("msg", "uid", rule.Uid, "app", rule.App, "user", rule.User, "dbname", rule.Dbname,
				"privileges", rule.Privileges, "error", err)
			check = append(check, fmt.Sprintf("%d    %s     %s     %s     %s     %s",
				rule.Uid, rule.App, rule.User, rule.Dbname, rule.Privileges, err.Error()))
			s := fmt.Sprintf("%s|%s", rule.App, rule.User)
			// 去重
			if _, isExists := UniqMap[s]; isExists == true {
				continue
			}
			UniqMap[s] = struct{}{}
			*exclude = append(*exclude, AppUser{rule.App, rule.User})
		}
	}
	if len(check) > 0 {
		slog.Error("权限格式检查未通过")
		errMsg = append(errMsg, "权限格式检查未通过")
		errMsg = append(errMsg, "uid:    app:     user:     dbname:     privileges:     error:")
		errMsg = append(errMsg, check...)
		return errMsg
	}
	return nil
}

// MysqlOldPassword mysql old_password的格式
func MysqlOldPassword(psw string) bool {
	// 16进制数
	re := regexp.MustCompile(`^[0123456789abcdef]{16}$`)
	return re.MatchString(psw)
}

// MysqlPassword mysql password的格式
func MysqlPassword(psw string) bool {
	// 16进制数，以*开头
	re := regexp.MustCompile(`^\*[0123456789ABCDEF]{40}$`)
	return re.MatchString(psw)
}

// RemoveRepeate 去重
func RemoveRepeate(arr []string) (newArr []string) {
	newArr = make([]string, 0)
	sort.Strings(arr)
	for i := 0; i < len(arr); i++ {
		repeat := false
		for j := i + 1; j < len(arr); j++ {
			if arr[i] == arr[j] {
				repeat = true
				break
			}
		}
		if !repeat {
			newArr = append(newArr, arr[i])
		}
	}
	return
}

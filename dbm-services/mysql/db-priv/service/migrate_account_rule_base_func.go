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
func FilterMigratePriv(appWhere string, exclude *[]AppUser) ([]string, []string, []string, error) {
	all := make([]*PrivModule, 0)
	uids := make([]string, 0)
	mysqlUids := make([]string, 0)
	exUids := make([]string, 0)

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
			suid := strconv.FormatInt(module.Uid, 10)
			uids = append(uids, suid)
			// gcs spider_master 、spider_slave 的帐号规则不被添加到dbm tendbha的帐号规则中
			if module.DbModule != "spider_master" && module.DbModule != "spider_slave" {
				mysqlUids = append(mysqlUids, suid)
			}
		} else {
			exUids = append(exUids, strconv.FormatInt(module.Uid, 10))
		}
	}
	if len(uids) == 0 && len(mysqlUids) == 0 {
		slog.Warn("no rule should be migrated")
	}
	return mysqlUids, uids, exUids, err
}

// GetUsers 获取帐号
func GetUsers(key string, uids []string) ([]*PrivModule, error) {
	users := make([]*PrivModule, 0)
	if len(uids) == 0 {
		return users, nil
	}
	// 从帐号规则中提取帐号信息
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

// GetRules 获取规则
func GetRules(uids []string) ([]*PrivModule, error) {
	users := make([]*PrivModule, 0)
	if len(uids) == 0 {
		return users, nil
	}
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
	// allPrivileges 与其他权限互斥
	if allPrivileges && (len(global) > 1 || len(dml) > 0 || len(ddl) > 0) {
		return target, fmt.Errorf("[all privileges] should not be granted with others")
	}
	target["dml"] = strings.Join(RemoveRepeate(dml), ",")
	target["ddl"] = strings.Join(RemoveRepeate(ddl), ",")
	target["global"] = strings.Join(RemoveRepeate(global), ",")
	return target, nil
}

// DoAddAccounts 创建帐号
func DoAddAccounts(apps map[string]int64, users []*PrivModule, clusterType string) error {
	for _, user := range users {
		account := AccountPara{BkBizId: apps[user.App], User: user.User,
			Psw: user.Psw, Operator: "migrate", ClusterType: &clusterType, MigrateFlag: true}
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

// CheckDifferentPasswordsForOneUser 不同帐号规则中帐号的密码不同
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

// CheckEmptyPassword 密码不能为空
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

/*
// CheckPasswordConsistentWithUser 用户名与密码不能相同
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
*/

// CheckPasswordMaybeOldPassword 检查是否为mysql的old_password格式，此类密码不迁移，从业务侧获取明文迁移
func CheckPasswordMaybeOldPassword(key, appWhere string, exclude *[]AppUser) error {
	vsql := fmt.Sprintf("select distinct app,user,AES_DECRYPT(psw,'%s') as psw "+
		"from tb_app_priv_module where length(AES_DECRYPT(psw,'%s'))=16 and  app in (%s) ;", key, key, appWhere)
	slog.Info("check 3: old_password not allowed to be migrated")
	err := CheckPasswordValue(vsql, exclude, 3)
	if err != nil {
		slog.Error("CheckPassword", "error", err)
		return err
	}
	return nil
}

// CheckPasswordValue 检查账户的密码
func CheckPasswordValue(vsql string, exclude *[]AppUser, round int) error {
	psw := make([]*PrivModule, 0)
	temp := make([]*PrivModule, 0)
	err := GcsDb.Self.Debug().Raw(vsql).Scan(&psw).Error
	if err != nil {
		slog.Error(vsql, "execute error", err)
		return err
	}
	if round == 2 {
		temp = append(temp, psw...)
	} else if round == 3 {
		for _, v := range psw {
			// 检查是否有old_password
			if MysqlOldPassword(v.Psw) {
				temp = append(temp, v)
			}
		}
	}
	if len(temp) > 0 {
		msg := fmt.Sprintf("app:    user: ")
		for _, user := range temp {
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

// CheckDifferentPrivileges 同账号有不同的权限范围
func CheckDifferentPrivileges(appWhere string) error {
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
			// 权限不同的规则可以合并，不需要剔除
			// *exclude = append(*exclude, AppUser{distinct.App, distinct.User})
		}
	}
	if len(check) > 0 {
		msg := "app:    user:     dbname:     different_privileges_count:"
		msg = fmt.Sprintf("\n%s\n%s", msg, strings.Join(check, "\n"))
		slog.Error(msg)
		slog.Error("different privileges will be merged")
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
	// 找出需要过滤的app+user
	for _, rule := range rules {
		// 检查权限格式是否正确、是否存在冲突等
		_, err = FormatPriv(rule.Privileges)
		if err != nil {
			privPass = false
			slog.Error("msg", "uid", rule.Uid, "app", rule.App, "user", rule.User, "privileges", rule.Privileges, "error", err)
			s := fmt.Sprintf("%s|%s", rule.App, rule.User)
			// 去重
			if _, isExists := UniqMap[s]; isExists == true {
				continue
			}
			UniqMap[s] = struct{}{}
			*exclude = append(*exclude, AppUser{rule.App, rule.User})
		}
	}
	if !privPass {
		slog.Error("[ check 5 Fail ]")
		return fmt.Errorf("wrong privileges")
	} else {
		slog.Info("[ check 5 Success ]")
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
	// 16进制数
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

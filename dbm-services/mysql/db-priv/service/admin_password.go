package service

import (
	"dbm-services/common/go-pubpkg/errno"
	"encoding/base64"
	"fmt"
	"strings"
	"sync"

	"golang.org/x/exp/slog"
)

// GetPassword 查询密码
func (m *GetPasswordPara) GetPassword() ([]*TbPasswords, error) {
	var passwords []*TbPasswords
	var where string
	if len(m.Users) == 0 {
		return passwords, errno.NameNull
	}
	var filterUser, filterInstance []string
	for _, user := range m.Users {
		if user.UserName == "" {
			return passwords, errno.NameNull
		}
		if user.Component == "" {
			return passwords, errno.ComponentNull
		}
		// 查询mysql管理密码用专用的接口查看
		if user.UserName == "ADMIN" && user.Component == "mysql" {
			return passwords, errno.UseApiForMysqlAdmin
		}
		filterUser = append(filterUser, fmt.Sprintf("(username='%s' and component='%s')", user.UserName, user.Component))
	}
	userWhere := strings.Join(filterUser, " or ")
	where = userWhere

	for _, item := range m.Instances {
		filterInstance = append(filterInstance, fmt.Sprintf("(ip='%s' and port=%d)", item.Ip, item.Port))
	}
	instanceWhere := strings.Join(filterInstance, " or ")
	if instanceWhere != "" {
		where = fmt.Sprintf(" (%s) and (%s)", where, instanceWhere)
	}
	err := DB.Self.Model(&TbPasswords{}).Where(where).Scan(&passwords).Error
	if err != nil {
		return passwords, err
	}
	err = DecodePassword(passwords)
	if err != nil {
		return passwords, err
	}
	return passwords, nil
}

// ModifyPassword 修改tb_passwords表中密码
func (m *ModifyPasswordPara) ModifyPassword() error {
	if m.UserName == "" {
		return errno.NameNull
	}
	if m.Component == "" {
		return errno.ComponentNull
	}
	var psw, encrypt string
	var security SecurityRule
	plain, err := base64.StdEncoding.DecodeString(m.Psw)
	if err != nil {
		slog.Error("msg", "base64 decode error", err)
		return err
	}
	m.Psw = string(plain)
	if m.SecurityRuleName != "" {
		security, err = GetSecurityRule(m.SecurityRuleName)
		if err != nil {
			slog.Error("msg", "GetSecurityRule", err)
			return err
		}
		psw, err = CheckOrGetPassword(m.Psw, security)
		if err != nil {
			slog.Error("msg", "CheckOrGetPassword", err)
			return err
		}
	} else {
		if m.Psw == "" {
			return errno.RuleNameNull
		} else {
			psw = m.Psw
		}
	}
	encrypt, err = SM4Encrypt(psw)
	tx := DB.Self.Begin()
	for _, item := range m.Instances {
		// 平台通用账号的密码，不允许修改
		if item.Ip == "0.0.0.0" && item.Port == 0 {
			return errno.PlatformPasswordNotAllowedModified
		}
		// 更新tb_passwords中实例的密码
		sql := fmt.Sprintf("replace into tb_passwords(ip,port,username,password,component,operator) "+
			"values('%s',%d,'%s','%s','%s','%s')",
			item.Ip, item.Port, m.UserName, encrypt, m.Component, m.Operator)
		err = tx.Debug().Exec(sql).Error
		if err != nil {
			slog.Error("msg", sql, err)
			tx.Rollback()
			return err
		}
	}
	err = tx.Commit().Error
	if err != nil {
		return err
	}
	return nil
}

// DeletePassword 删除tb_passwords表中密码
func (m *GetPasswordPara) DeletePassword() error {
	if len(m.Users) == 0 {
		return errno.NameNull
	}
	if len(m.Instances) == 0 {
		return fmt.Errorf("instances should not be null")
	}
	var where string
	var filterUser, filterInstance []string
	for _, user := range m.Users {
		if user.UserName == "" {
			return errno.NameNull
		}
		if user.Component == "" {
			return errno.ComponentNull
		}
		filterUser = append(filterUser, fmt.Sprintf("(username='%s' and component='%s')", user.UserName, user.Component))
	}
	userWhere := strings.Join(filterUser, " or ")
	where = userWhere
	for _, item := range m.Instances {
		// 平台通用账号的密码，不允许删除
		if item.Ip == "0.0.0.0" && item.Port == 0 {
			return errno.PlatformPasswordNotAllowedModified
		}
		filterInstance = append(filterInstance, fmt.Sprintf("(ip='%s' and port=%d)", item.Ip, item.Port))
	}
	instanceWhere := strings.Join(filterInstance, " or ")
	if instanceWhere != "" {
		where = fmt.Sprintf(" (%s) and (%s)", where, instanceWhere)
	}
	sql := fmt.Sprintf("delete from tb_passwords where %s", where)
	err := DB.Self.Exec(sql).Error
	if err != nil {
		slog.Error("msg", "sql", sql, "error", err)
		return err
	}
	return nil
}

// GetMysqlAdminPassword 查询mysql管理密码
func (m *GetAdminUserPasswordPara) GetMysqlAdminPassword() ([]*TbPasswords, error) {
	var passwords []*TbPasswords
	if m.UserName != "ADMIN" {
		return passwords, errno.NameNull
	}
	if m.Component == "" {
		return passwords, errno.ComponentNull
	}
	//  mysql实例中ADMIN用户的密码，仅能查看人为修改密码且在有效期的密码，不可以查看随机化生成的密码
	where := fmt.Sprintf(" username='%s' and component='%s' and lock_until is not null", m.UserName, m.Component)
	var filter []string
	for _, item := range m.Instances {
		filter = append(filter, fmt.Sprintf("(ip='%s' and port=%d)", item.Ip, item.Port))
	}
	filters := strings.Join(filter, " or ")
	if filters != "" {
		where = fmt.Sprintf(" %s and %s ", where, filters)
	}
	err := DB.Self.Model(&TbPasswords{}).Where(where).Scan(&passwords).Error
	if err != nil {
		return passwords, err
	}
	err = DecodePassword(passwords)
	if err != nil {
		return passwords, err
	}
	return passwords, nil
}

// ModifyMysqlAdminPassword 修改mysql实例中用户的密码，可用于随机化密码
func (m *ModifyAdminUserPasswordPara) ModifyMysqlAdminPassword() (BatchResult, error) {
	var errMsg Err
	var success Resource
	var fail Resource
	var batch BatchResult
	var wg sync.WaitGroup
	var security SecurityRule
	var passwordInput string
	var errCheck error
	tokenBucket := make(chan int, 10)
	// 后台定时任务，1、randmize_daily比如每天执行一次，随机化没有被锁住的实例 2、randmize_expired比如每分钟执行一次随机化锁定过期的实例
	// 前台页面，单据已提示实例密码被锁定是否修改，用户确认修改，因此不检查是否锁定
	if m.Async && m.Range == "randmize_expired" {
		errCheck = m.NeedToBeRandomized()
		if errCheck != nil {
			return batch, errCheck
		}
	} else if m.Async && m.Range == "randmize_daily" {
		errCheck = m.RemoveLockedInstances()
		if errCheck != nil {
			return batch, errCheck
		}
	} else if m.Async {
		return batch, fmt.Errorf("[ %s ] not supported randmize range", m.Range)
	}

	if m.UserName == "" {
		return batch, errno.NameNull
	}
	if m.Component == "" {
		return batch, errno.ComponentNull
	}

	plain, errCheck := base64.StdEncoding.DecodeString(m.Psw)
	if errCheck != nil {
		slog.Error("msg", "base64 decode error", errCheck)
		return batch, errCheck
	}
	m.Psw = string(plain)

	// 传入安全规则，1、如果传入密码，根据安全规则校验密码复杂度，2、如果没有传入密码，根据安全规则随机生成密码
	// 不允许没有不传入安全规则，并且不传入密码
	if m.SecurityRuleName != "" {
		security, errCheck = GetSecurityRule(m.SecurityRuleName)
		if errCheck != nil {
			slog.Error("msg", "GetSecurityRule", errCheck)
			return batch, errCheck
		}
		if m.Psw != "" {
			passwordInput, errCheck = CheckOrGetPassword(m.Psw, security)
			if errCheck != nil {
				slog.Error("msg", "CheckOrGetPassword", errCheck)
				return batch, errCheck
			}
		}
	} else {
		if m.Psw == "" {
			return batch, errno.RuleNameNull
		} else {
			passwordInput = m.Psw
		}
	}

	for _, cluster := range m.Clusters {
		if cluster.BkCloudId == nil {
			return batch, errno.CloudIdRequired
		}
		if cluster.ClusterType == nil {
			return batch, errno.ClusterTypeIsEmpty
		}
		var psw, encrypt string
		var errOuter error
		if passwordInput == "" {
			psw, errOuter = CheckOrGetPassword("", security)
			if errOuter != nil {
				slog.Error("msg", "CheckOrGetPassword", errOuter)
				return batch, errOuter
			}
		} else {
			psw = passwordInput
		}
		// 加密
		encrypt, errOuter = SM4Encrypt(psw)
		if errOuter != nil {
			slog.Error("SM4Encrypt", "error", errOuter)
			return batch, errOuter
		}
		for _, instanceList := range cluster.MultiRoleInstanceLists {
			var base []string
			role := instanceList.Role
			if *cluster.ClusterType == tendbcluster && role == machineTypeSpider {
				base = append(base, flushPriv, setBinlogOff, setDdlByCtlOFF)
			} else if *cluster.ClusterType == tendbcluster && role == tdbctl {
				base = append(base, flushPriv, setBinlogOff, setTcAdminOFF)
			} else {
				base = append(base, flushPriv, setBinlogOff)
			}
			for _, address := range instanceList.Addresses {
				wg.Add(1)
				tokenBucket <- 0
				go func(base []string, role, psw, encrypt string, address Address, cluster OneCluster) {
					defer func() {
						<-tokenBucket
						wg.Done()
					}()
					// 获取修改密码的语句
					sqls := base
					hostPort := fmt.Sprintf("%s:%d", address.Ip, address.Port)
					mysqlVersion, err := GetMySQLVersion(hostPort, *cluster.BkCloudId)
					if err != nil {
						slog.Error("mysqlVersion", err)
						AddError(&errMsg, hostPort, err)
						return
					}
					userLocalhost := fmt.Sprintf("GRANT ALL PRIVILEGES ON *.* TO '%s'@'localhost' "+
						"IDENTIFIED BY '%s' WITH GRANT OPTION", m.UserName, psw)
					userIp := fmt.Sprintf("GRANT ALL PRIVILEGES ON *.* TO '%s'@'%s' "+
						"IDENTIFIED BY '%s' WITH GRANT OPTION", m.UserName, address.Ip, psw)
					if !(*cluster.ClusterType == tendbcluster && role == machineTypeSpider) &&
						MySQLVersionParse(mysqlVersion, "") >=
							MySQLVersionParse("8.0.0", "") {
						userLocalhost = fmt.Sprintf("ALTER USER '%s'@'localhost' "+
							"IDENTIFIED WITH mysql_native_password BY '%s'", m.UserName, psw)
						userIp = fmt.Sprintf("ALTER USER '%s'@'%s' "+
							"IDENTIFIED WITH mysql_native_password BY '%s'", m.UserName, address.Ip, psw)
					}
					sqls = append(sqls, userLocalhost, userIp, setBinlogOn, flushPriv)
					// 到实例更新密码
					var queryRequest = QueryRequest{[]string{hostPort}, sqls, true, 60, *cluster.BkCloudId}
					_, err = OneAddressExecuteSql(queryRequest)
					if err != nil {
						AddResource(&fail, address)
						slog.Error("OneAddressExecuteSql", err)
						AddError(&errMsg, hostPort, err)
						return
					}
					// 更新tb_passwords中实例的密码
					sql := fmt.Sprintf("replace into tb_passwords(ip,port,username,password,component,operator) "+
						"values('%s',%d,'%s','%s','%s','%s')",
						address.Ip, address.Port, m.UserName, encrypt, m.Component, m.Operator)
					if m.LockUntil != "" {
						sql = fmt.Sprintf("replace into tb_passwords(ip,port,username,password,component,"+
							"operator,lock_until) values('%s',%d,'%s','%s','%s','%s','%s')",
							address.Ip, address.Port, m.UserName, encrypt, m.Component, m.Operator, m.LockUntil)
					}
					result := DB.Self.Exec(sql)
					if result.Error != nil {
						AddResource(&fail, address)
						AddError(&errMsg, hostPort, result.Error)
						return
					}
					AddResource(&success, address)
					return
				}(base, role, psw, encrypt, address, cluster)
			}
		}
	}
	wg.Wait()
	close(tokenBucket)
	// 随机化成功的实例以及随机化失败的实例
	batch = BatchResult{Success: success.resources, Fail: fail.resources}
	if len(errMsg.errs) > 0 {
		errOuter := errno.ModifyUserPasswordFail.Add("\n" + strings.Join(errMsg.errs, "\n"))
		return batch, errOuter
	}
	return batch, nil
}

// GetMysqlPlatformPassword 查看mysql平台密码,内部接口
func (m *GetPasswordPara) GetMysqlPlatformPassword() (map[string]string, error) {
	if len(m.Instances) != 1 || m.Instances[0].Ip != "0.0.0.0" || m.Instances[0].Port != 0 {
		return nil, fmt.Errorf("instance format error")
	}
	users, err := m.GetPassword()
	if err != nil {
		return nil, err
	}
	resp := make(map[string]string, len(users))

	vmap := map[string]string{"ADMIN": "tbinlogdumper", "dba_bak_all_sel": "backup",
		"MONITOR_ALL": "monitor_access_all", "MONITOR": "monitor", "mysql": "os_mysql",
		"repl": "repl", "yw": "yw", "proxy": "proxy"}
	for _, user := range users {
		value, ok := vmap[user.UserName]
		if ok {
			resp[value+"_pwd"] = user.Password
			resp[value+"_user"] = user.UserName
			if user.UserName == "MONITOR_ALL" {
				resp[value+"_user"] = "MONITOR"
			}
		} else {
			slog.Error("msg", user.UserName, "not platform user")
			return nil, fmt.Errorf("%s not platform user", user.UserName)
		}
	}
	return resp, nil
}

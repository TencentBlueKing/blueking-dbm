package service

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"log/slog"
	"strings"
	"sync"
	"time"

	"golang.org/x/time/rate"

	"dbm-services/common/go-pubpkg/errno"
)

// GetPassword 查询密码
func (m *GetPasswordPara) GetPassword() ([]*TbPasswords, int, error) {
	var passwords []*TbPasswords
	var where string
	if len(m.Users) == 0 {
		return passwords, 0, errno.NameNull
	}
	var filterUser, filterInstance []string
	for _, user := range m.Users {
		if user.UserName == "" {
			return passwords, 0, errno.NameNull
		}
		if user.Component == "" {
			return passwords, 0, errno.ComponentNull
		}
		// 查询mysql管理密码，请用专用的接口
		if user.UserName == "ADMIN" && user.Component == "mysql" {
			return passwords, 0, errno.UseApiForMysqlAdmin
		}
		filterUser = append(filterUser, fmt.Sprintf("(username='%s' and component='%s')", user.UserName, user.Component))
	}
	userWhere := strings.Join(filterUser, " or ")
	where = userWhere

	for _, item := range m.Instances {
		// 查询可以只填写ip，port与bk_biz_id选填
		if item.Port != nil && item.BkCloudId != nil {
			filterInstance = append(filterInstance, fmt.Sprintf("(ip='%s' and port=%d and bk_cloud_id=%d)",
				item.Ip, *item.Port, *item.BkCloudId))
		} else if item.Port != nil && item.BkCloudId == nil {
			filterInstance = append(filterInstance, fmt.Sprintf("(ip='%s' and port=%d)", item.Ip, *item.Port))
		} else {
			filterInstance = append(filterInstance, fmt.Sprintf("(ip='%s')", item.Ip))
		}
	}
	instanceWhere := strings.Join(filterInstance, " or ")
	if instanceWhere != "" {
		where = fmt.Sprintf(" (%s) and (%s)", where, instanceWhere)
	}
	if m.BeginTime != "" && m.EndTime != "" {
		where = fmt.Sprintf(" %s and update_time>='%s' and update_time<='%s'", where, m.BeginTime, m.EndTime)
	}
	if m.BkBizId != nil {
		where = fmt.Sprintf(" %s and bk_biz_id = %d ", where, *m.BkBizId)
	}
	var err error
	cnt := Cnt{}
	vsql := fmt.Sprintf("select count(*) as cnt from tb_passwords where %s", where)
	err = DB.Self.Raw(vsql).Scan(&cnt).Error
	if err != nil {
		slog.Error(vsql, "execute error", err)
		return nil, 0, err
	}

	// 分页
	if m.Limit != nil && m.Offset != nil {
		err = DB.Self.Model(&TbPasswords{}).Where(where).Order("update_time DESC").Limit(*m.Limit).Offset(
			*m.Offset).Find(&passwords).Error
	} else if m.Limit == nil && m.Offset == nil {
		err = DB.Self.Model(&TbPasswords{}).Where(where).Order("update_time DESC").Find(&passwords).Error
	} else if m.Limit != nil && m.Offset == nil {
		err = DB.Self.Model(&TbPasswords{}).Where(where).Order(
			"update_time DESC").Limit(*m.Limit).Find(&passwords).Error
	} else {
		// offset在limit为0时没有意义
		return passwords, 0, fmt.Errorf("offset not null but limit null")
	}
	if err != nil {
		slog.Error("msg", "query passwords error", err)
		return passwords, 0, err
	}
	// 解码
	err = DecodePassword(passwords)
	if err != nil {
		slog.Error("msg", "DecodePassword", err)
		return passwords, 0, err
	}
	return passwords, cnt.Count, nil
}

// ModifyPassword 修改tb_passwords表中密码
func (m *ModifyPasswordPara) ModifyPassword(jsonPara string, ticket string) error {
	if m.UserName == "" {
		return errno.NameNull
	}
	if m.Component == "" {
		return errno.ComponentNull
	}
	AddPrivLog(PrivLog{BkBizId: 0, Ticket: ticket, Operator: m.Operator, Para: jsonPara, Time: time.Now()})
	var psw, encrypt string
	var security SecurityRule
	// base64解码
	plain, err := base64.StdEncoding.DecodeString(m.Psw)
	if err != nil {
		slog.Error("msg", "base64 decode error", err)
		return err
	}
	m.Psw = string(plain)
	if m.SecurityRuleName != "" {
		// 获取密码复杂度规则
		security, err = GetSecurityRule(m.SecurityRuleName)
		if err != nil {
			slog.Error("msg", "GetSecurityRule", err)
			return err
		}
		// 检查传入的密码复杂度，或者生成密码
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
	if err != nil {
		slog.Error("SM4Encrypt", "error", err)
		return err
	}
	tx := DB.Self.Begin()
	for _, item := range m.Instances {
		if item.Port == nil {
			return errno.PortRequired
		}
		// 平台通用账号的密码，不允许修改
		if item.Ip == "0.0.0.0" && *item.Port == 0 && !m.InitPlatform {
			return errno.PlatformPasswordNotAllowedModified
		}
		if item.BkCloudId == nil {
			return errno.CloudIdRequired
		}
		// 更新tb_passwords中实例的密码
		sql := fmt.Sprintf("replace into tb_passwords(ip,port,bk_cloud_id,username,password,component,operator) "+
			"values('%s',%d,%d,'%s','%s','%s','%s')",
			item.Ip, *item.Port, *item.BkCloudId, m.UserName, encrypt, m.Component, m.Operator)
		if m.BkBizId != nil {
			sql = fmt.Sprintf("replace into tb_passwords(ip,port,bk_cloud_id,username,password,component,bk_biz_id,operator) "+
				"values('%s',%d,%d,'%s','%s','%s',%d,'%s')",
				item.Ip, *item.Port, *item.BkCloudId, m.UserName, encrypt, m.Component, *m.BkBizId, m.Operator)
		}
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
func (m *GetPasswordPara) DeletePassword(jsonPara string, ticket string) error {
	if len(m.Users) == 0 {
		return errno.NameNull
	}
	if len(m.Instances) == 0 {
		return fmt.Errorf("instances should not be null")
	}
	AddPrivLog(PrivLog{BkBizId: 0, Ticket: ticket, Operator: m.Operator, Para: jsonPara, Time: time.Now()})
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
		if item.Ip == "0.0.0.0" && *item.Port == 0 {
			return errno.PlatformPasswordNotAllowedModified
		}
		if item.BkCloudId == nil {
			return errno.CloudIdRequired
		}
		if item.Port == nil {
			return errno.PortRequired
		}
		filterInstance = append(filterInstance, fmt.Sprintf("(ip='%s' and port=%d and bk_cloud_id=%d)",
			item.Ip, *item.Port, *item.BkCloudId))
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
// 支持sqlserver admin账号的查询
func (m *GetAdminUserPasswordPara) GetMysqlAdminPassword() ([]*TbPasswords, int, error) {
	var passwords []*TbPasswords
	if m.UserName != "ADMIN" && m.UserName != "dbm_admin" {
		return passwords, 0, errno.NameNull
	}
	//  mysql实例中ADMIN用户的密码，仅能查看人为修改密码且在有效期的密码，不可以查看随机化生成的密码
	where := fmt.Sprintf(" username='%s' and component in ('%s','%s', '%s') and lock_until is not null and "+
		"lock_until > now()", m.UserName, mysql, tendbcluster, sqlserver)
	var filter []string
	for _, item := range m.Instances {
		if item.Port != nil {
			filter = append(filter, fmt.Sprintf("(ip='%s' and port=%d)", item.Ip, *item.Port))
		} else {
			filter = append(filter, fmt.Sprintf("(ip='%s')", item.Ip))
		}
	}
	filters := strings.Join(filter, " or ")
	if filters != "" {
		where = fmt.Sprintf(" %s and (%s) ", where, filters)
	}
	if m.BkBizId != nil {
		where = fmt.Sprintf(" %s and bk_biz_id = %d ", where, *m.BkBizId)
	}
	if m.BeginTime != "" && m.EndTime != "" {
		where = fmt.Sprintf(" %s and update_time>='%s' and update_time<='%s' ",
			where, m.BeginTime, m.EndTime)
	}
	var err error
	// 分页
	if m.Limit != nil && m.Offset != nil {
		err = DB.Self.Model(&TbPasswords{}).Where(where).Order("update_time DESC").Limit(*m.Limit).Offset(
			*m.Offset).Find(&passwords).Error
	} else if m.Limit == nil && m.Offset == nil {
		err = DB.Self.Model(&TbPasswords{}).Where(where).Order("update_time DESC").Find(&passwords).Error
	} else if m.Limit != nil && m.Offset == nil {
		err = DB.Self.Model(&TbPasswords{}).Where(where).Order(
			"update_time DESC").Limit(*m.Limit).Find(&passwords).Error
	} else {
		return passwords, 0, fmt.Errorf("offset not null but limit null")
	}
	if err != nil {
		slog.Error("msg", "query passwords error", err)
		return passwords, 0, err
	}
	err = DecodePassword(passwords)
	if err != nil {
		slog.Error("msg", "DecodePassword", err)
		return passwords, 0, err
	}
	return passwords, len(passwords), nil
}

// ModifyAdminPassword 修改mysql实例中用户的密码，可用于随机化密码
func (m *ModifyAdminUserPasswordPara) ModifyAdminPassword() (BatchResult, error) {
	var errMsg Err
	var success Resource
	var fail Resource
	var batch BatchResult
	var wg sync.WaitGroup
	var security SecurityRule
	var passwordInput string
	var errCheck error

	limit := rate.Every(time.Millisecond * 100) // QPS：10
	burst := 10                                 // 桶容量 10
	limiter := rate.NewLimiter(limit, burst)

	if m.UserName == "" {
		return batch, errno.NameNull
	}
	if m.Component == "" {
		return batch, errno.ComponentNull
	}
	// 后台定时任务，1、randmize_daily比如每天执行一次，随机化没有被锁住的实例 2、randmize_expired比如每分钟执行一次随机化锁定过期的实例
	// 前台页面，单据已提示实例密码被锁定是否修改，用户确认修改，因此不检查是否锁定

	if m.Async && m.Range == "randmize_expired" {
		// 过滤出需要随机化的实例
		errCheck = m.NeedToBeRandomized()
		if errCheck != nil {
			slog.Error("msg", "NeedToBeRandomized", errCheck)
			return batch, errCheck
		}
	} else if m.Async && m.Range == "randmize_daily" {
		// 去除密码被锁定的实例，不参与日常随机化
		errCheck = m.RemoveLockedInstances()
		if errCheck != nil {
			return batch, errCheck
		}
	} else if m.Async {
		return batch, fmt.Errorf("[ %s ] not supported randmize range", m.Range)
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
			slog.Error("msg", errno.CloudIdRequired)
			return batch, errno.CloudIdRequired
		}
		if cluster.ClusterType == nil {
			slog.Error("msg", errno.ClusterTypeIsEmpty)
			return batch, errno.ClusterTypeIsEmpty
		}
		if cluster.BkBizId == nil {
			return batch, errno.BkBizIdIsEmpty
		}
		// 一个集群中的各个实例使用同一个密码
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
		err := limiter.Wait(context.Background())
		if err != nil {
			AddError(&errMsg, "get parallel resource", err)
			continue
		}
		wg.Add(1)
		go func(psw, encrypt string, cluster OneCluster) {
			defer func() {
				wg.Done()
			}()
			// 如果是sqlserver授权，走sqlserver授权通道
			if m.Component == "sqlserver" {
				m.ModifyAdminPasswordForSqlserver(
					psw, encrypt, cluster, &errMsg, &success, &fail,
				)
			} else {
				// 默认走mysql授权通道
				m.ModifyAdminPasswordForMysql(
					psw, encrypt, cluster, &errMsg, &success, &fail,
				)
			}
		}(psw, encrypt, cluster)
	}
	wg.Wait()
	// 随机化成功的实例以及随机化失败的实例，返回格式与入参Clusters相同，便于失败重试
	batch = BatchResult{Success: success.resources, Fail: fail.resources}
	if len(errMsg.errs) > 0 {
		errOuter := errno.ModifyUserPasswordFail.Add("\n" + strings.Join(errMsg.errs, "\n"))
		slog.Error("msg", "modify error", errOuter)
		return batch, errOuter
	}
	return batch, nil
}

// ModifyAdminPasswordForSqlserver 专属sqlserver 修改admin密码函数
func (m *ModifyAdminUserPasswordPara) ModifyAdminPasswordForSqlserver(
	psw string,
	encrypt string,
	cluster OneCluster,
	errMsg *Err,
	success *Resource,
	fail *Resource,
) {

	var successList []InstanceList
	var failList []InstanceList
	for _, instanceList := range cluster.MultiRoleInstanceLists {
		// 理论上只循环一次
		ok := InstanceList{instanceList.Role, []IpPort{}}
		notOK := InstanceList{instanceList.Role, []IpPort{}}

		for _, address := range instanceList.Addresses {
			// 获取集群内所有的instance信息
			hostPort := fmt.Sprintf("%s:%d", address.Ip, address.Port)
			sqls := []string{fmt.Sprintf("ALTER LOGIN [%s] WITH PASSWORD=N'%s'", m.UserName, psw)}
			// 远程变更密码
			var queryRequest = QueryRequest{
				[]string{hostPort},
				sqls,
				true,
				60,
				*cluster.BkCloudId,
			}
			_, err := OneAddressExecuteSqlserverSql(queryRequest)
			if err != nil {
				notOK.Addresses = append(notOK.Addresses, address)
				slog.Error("msg", "OneAddressExecuteSqlserverSql", err)
				AddError(errMsg, hostPort, err)
				continue
			}

			// 更新tb_passwords中实例的密码
			sql := fmt.Sprintf("replace into tb_passwords(ip,port,bk_cloud_id,bk_biz_id,username,"+
				"password,component,operator) values('%s',%d,%d,%d,'%s','%s','%s','%s')",
				address.Ip, address.Port, *cluster.BkCloudId,
				*cluster.BkBizId, m.UserName, encrypt, m.Component, m.Operator)
			if m.LockHour != 0 {
				sql = fmt.Sprintf("replace into tb_passwords(ip,port,bk_cloud_id,bk_biz_id,username,"+
					"password,component,operator,lock_until) values('%s',%d,%d,%d,'%s','%s','%s','%s',date_add("+
					"now(),INTERVAL %d hour))",
					address.Ip, address.Port, *cluster.BkCloudId, *cluster.BkBizId,
					m.UserName, encrypt, m.Component, m.Operator, m.LockHour)
			}
			result := DB.Self.Exec(sql)
			if result.Error != nil {
				notOK.Addresses = append(notOK.Addresses, address)
				slog.Error("msg", "sql", sql, "excute sql error", result.Error)
				AddError(errMsg, hostPort, result.Error)
				continue
			}
			// 录入正确日志
			ok.Addresses = append(ok.Addresses, address)
		}
		if len(ok.Addresses) > 0 {
			successList = append(successList, ok)
		}
		if len(notOK.Addresses) > 0 {
			failList = append(failList, notOK)
		}
	}
	if len(successList) > 0 {
		AddResource(success, OneCluster{cluster.BkCloudId, cluster.ClusterType, cluster.BkBizId,
			successList})
	}
	if len(failList) > 0 {
		AddResource(fail, OneCluster{cluster.BkCloudId, cluster.ClusterType, cluster.BkBizId,
			failList})
	}
}

// ModifyAdminPasswordForMysql 专属mysql 修改admin密码函数
func (m *ModifyAdminUserPasswordPara) ModifyAdminPasswordForMysql(
	psw string,
	encrypt string,
	cluster OneCluster,
	errMsg *Err,
	success *Resource,
	fail *Resource,
) {
	var successList []InstanceList
	var failList []InstanceList
	for _, instanceList := range cluster.MultiRoleInstanceLists {
		var base []string
		ok := InstanceList{instanceList.Role, []IpPort{}}
		notOK := InstanceList{instanceList.Role, []IpPort{}}
		role := instanceList.Role
		if *cluster.ClusterType == tendbcluster && role == tdbctl {
			base = append(base, flushPriv, setBinlogOff, setTcAdminOFF)
		} else {
			base = append(base, flushPriv, setBinlogOff)
		}
		for _, address := range instanceList.Addresses {
			// 获取修改密码的语句
			sqls := base
			hostPort := fmt.Sprintf("%s:%d", address.Ip, address.Port)
			mysqlVersion, err := GetMySQLVersion(hostPort, *cluster.BkCloudId)
			if err != nil {
				notOK.Addresses = append(notOK.Addresses, address)
				slog.Error("mysqlVersion", err)
				AddError(errMsg, hostPort, err)
				continue
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
			var queryRequest = QueryRequest{[]string{hostPort}, sqls, true,
				60, *cluster.BkCloudId}
			_, err = OneAddressExecuteSql(queryRequest)
			if err != nil {
				notOK.Addresses = append(notOK.Addresses, address)
				slog.Error("msg", "OneAddressExecuteSql", err)
				AddError(errMsg, hostPort, err)
				continue
			}
			// 更新tb_passwords中实例的密码
			sql := fmt.Sprintf("replace into tb_passwords(ip,port,bk_cloud_id,username,"+
				"password,component,bk_biz_id,operator) values('%s',%d,%d,'%s','%s','%s',%d,'%s')",
				address.Ip, address.Port, *cluster.BkCloudId, m.UserName, encrypt, m.Component,
				*cluster.BkBizId, m.Operator)
			if m.LockHour != 0 {
				sql = fmt.Sprintf("replace into tb_passwords(ip,port,bk_cloud_id,username,"+
					"password,component,bk_biz_id,operator,lock_until) values("+
					"'%s',%d,%d,'%s','%s','%s',%d,'%s',date_add(now(),INTERVAL %d hour))",
					address.Ip, address.Port, *cluster.BkCloudId, m.UserName, encrypt, m.Component,
					*cluster.BkBizId, m.Operator, m.LockHour)
			}
			result := DB.Self.Exec(sql)
			if result.Error != nil {
				notOK.Addresses = append(notOK.Addresses, address)
				slog.Error("msg", "sql", sql, "excute sql error", result.Error)
				AddError(errMsg, hostPort, result.Error)
				continue
			}
			ok.Addresses = append(ok.Addresses, address)
		}
		// 修改密码成功的实例列表
		if len(ok.Addresses) > 0 {
			successList = append(successList, ok)
		}
		// 修改密码失败的实例列表
		if len(notOK.Addresses) > 0 {
			failList = append(failList, notOK)
		}
	}
	// 修改密码成功的实例列表，包含集群信息
	if len(successList) > 0 {
		AddResource(success, OneCluster{cluster.BkCloudId, cluster.ClusterType,
			cluster.BkBizId, successList})
	}
	// 修改密码失败的实例列表，包含集群信息
	if len(failList) > 0 {
		AddResource(fail, OneCluster{cluster.BkCloudId, cluster.ClusterType,
			cluster.BkBizId, failList})
	}
}

// MigratePlatformPassword 从dbconfig迁移帐号信息，内部使用
func (m *PlatformPara) MigratePlatformPassword() error {
	// 从dbconfig获取账号信息
	// migrate platform users for redis/mysql (not include mango)
	var users []ComponentPlatformUser
	// 从dbconfig获取mysql帐号
	err := GetMysqlInitUser(&users, m.DbConfig)
	if err != nil {
		slog.Error("msg", "GetMysqlInitUser", err)
		return fmt.Errorf("GetMysqlInitUser: %s", err.Error())
	}
	err = GetProxyInitUser(&users, m.DbConfig)
	if err != nil {
		slog.Error("msg", "GetProxyInitUser", err)
		return fmt.Errorf("GetProxyInitUser: %s", err.Error())
	}
	// 从dbconfig获取redis os帐号信息
	err = GetRedisOsUser(&users, m.DbConfig)
	if err != nil {
		slog.Error("msg", "GetRedisOsUser", err)
		return fmt.Errorf("GetRedisOsUser: %s", err.Error())

	}
	slog.Info("msg", "migrate users", users)
	for _, component := range users {
		for _, user := range component.NamePassword {
			defaultInt := int64(0)
			para := &ModifyPasswordPara{UserName: user.Name, Component: component.Component, Operator: "migrate",
				Instances:    []Address{{"0.0.0.0", &defaultInt, &defaultInt}},
				InitPlatform: true, Psw: base64.StdEncoding.EncodeToString([]byte(user.Password))}
			jsonPara, _ := json.Marshal(*para)
			err = para.ModifyPassword(string(jsonPara), "modify_password")
			if err != nil {
				slog.Error("modify platform user password", "error", err)
				return fmt.Errorf("modify platform user password error: %s", err.Error())
			}
		}
	}
	slog.Info("migrate success")
	return nil
}

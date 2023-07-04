package service

import (
	"encoding/json"
	errors2 "errors"
	"fmt"
	"regexp"
	"strconv"
	"strings"
	"sync"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/priv-service/util"

	"github.com/asaskevich/govalidator"
	"github.com/jinzhu/gorm"
	"github.com/spf13/viper"
	"golang.org/x/exp/slog"
)

// GetAccountRuleInfo 根据账号名获取账号信息，根据账号 id 以及授权数据库获取账号规则
func GetAccountRuleInfo(bkBizId int64, clusterType string, user, dbname string) (TbAccounts, TbAccountRules, error) {
	var account TbAccounts
	var accountRule TbAccountRules
	if clusterType == tendbha || clusterType == tendbsingle {
		clusterType = mysql
	}
	err := DB.Self.Table("tb_accounts").Where(&TbAccounts{BkBizId: bkBizId, ClusterType: clusterType, User: user}).
		Take(&account).Error
	if errors2.Is(err, gorm.ErrRecordNotFound) {
		return account, accountRule, fmt.Errorf("账号%s不存在", user)
	} else if err != nil {
		return account, accountRule, err
	}
	err = DB.Self.Model(&TbAccountRules{}).Where(
		&TbAccountRules{BkBizId: bkBizId, ClusterType: clusterType, AccountId: account.Id, Dbname: dbname}).
		Take(&accountRule).Error
	if errors2.Is(err, gorm.ErrRecordNotFound) {
		return account, accountRule, fmt.Errorf("账号规则(账号:%s,数据库:%s)不存在", user, dbname)
	} else if err != nil {
		return account, accountRule, err
	}
	return account, accountRule, nil
}

// ImportBackendPrivilege 生成 mysql 授权语句，mysql 执行授权语句
func ImportBackendPrivilege(account TbAccounts, accountRule TbAccountRules, address string, proxyIPs []string,
	sourceIps []string, clusterType string, tendbhaMasterDomain bool, bkCloudId int64) error {
	var backendSQL []string
	mysqlVersion, err := GetMySQLVersion(address, bkCloudId)
	if err != nil {
		slog.Error("mysqlVersion", err)
		return err
	}
	if tendbhaMasterDomain {
		backendSQL, err = GenerateBackendSQL(account, accountRule, proxyIPs, mysqlVersion, address, clusterType,
			tendbhaMasterDomain, bkCloudId)
		if err != nil {
			slog.Error("backendSQL", err)
			return err
		}
	} else {
		backendSQL, err = GenerateBackendSQL(account, accountRule, sourceIps, mysqlVersion, address, clusterType,
			tendbhaMasterDomain, bkCloudId)
		if err != nil {
			slog.Error("backendSQL", err)
			return err
		}
	}
	var queryRequest = QueryRequest{[]string{address}, backendSQL, true, 60, bkCloudId}
	_, err = OneAddressExecuteSql(queryRequest)
	if err != nil {
		slog.Error("OneAddressExecuteSql", err)
		return err
	}
	return nil
}

// GenerateBackendSQL 生成 mysql 授权语句
func GenerateBackendSQL(account TbAccounts, rule TbAccountRules, ips []string, mysqlVersion string, address string,
	clusterType string, tendbhaMasterDomain bool, bkCloudId int64) ([]string, error) {
	var multiPsw MultiPsw
	var wg sync.WaitGroup
	var errOuter error
	// ResultTemp 授权语句集合
	type ResultTemp struct {
		mu         sync.RWMutex
		backendSQL []string
	}
	var result ResultTemp
	finishChan := make(chan bool, 1)
	errorChan := make(chan error, 1)
	tokenBucket := make(chan int, 10)
	if errOuter = json.Unmarshal([]byte(account.Psw), &multiPsw); errOuter != nil {
		return nil, errOuter
	}

	// For almost all cases, we do not need to binlog grants.
	// Meanwhile, binlogging grants can cause problems, eg. when starting a MySQL 8.0 replica for MySQL 5.7,
	// because MySQL 8.0 does not recognize "GRANT ... IDENTIFIED BY ...".

	if clusterType == tendbcluster {
		result.backendSQL = append(result.backendSQL, flushPriv, setBinlogOff, setDdlByCtlOFF)
	} else if clusterType == tdbctl {
		// 仅AddPrivWithoutAccountRule内部接口使用
		result.backendSQL = append(result.backendSQL, flushPriv, setBinlogOff, setTcAdminOFF)
		clusterType = tendbsingle
	} else {
		result.backendSQL = append(result.backendSQL, flushPriv, setBinlogOff)
	}

	containConnLogDBFlag := ContainConnLogDB(rule.Dbname)
	needInsertConnLogFlag := containConnLogDBFlag && !strings.Contains(strings.ToLower(rule.DmlDdlPriv), "insert")
	/*
		非管理用户登录时记录审计日志
		mysql> show global variables like 'init_connect'
		Variable_name: init_connect
		Value: set @user=user(),@cur_user=current_user();insert into
		test.conn_log values(connection_id(),now(),@user,@cur_user,'127.0.0.1');

		如果用户权限不包含对test.conn_log的授权，由于用户默认拥有对test库的增删改查权限，登录不会报错。
		实例安装时默认给所有用户访问test的权限，从mysql.db可以看出。

		BUG：如果授权的库表范围包含test.conn_log,但是又没有插入权限，比如如下权限：
			GRANT SELECT ON `%`.* TO 'temp'@'localhost' identified by 'temp';
			由于用户权限优先级高于mysql.db，mysql.db的权限被"覆盖"，用户无法插入test.conn_log,登录失败 ERROR 1184。

			mysql> show databases;
			ERROR 2006 (HY000): MySQL server has gone away
			No connection. Trying to reconnect...
			Connection id:    2817282
			Current database: *** NONE ***

			ERROR 1184 (08S01): Aborted connection 2817282 to db: 'unconnected' user: 'temp' host: 'localhost' (
			init_connect command failed)


		解决方案：对test.conn_log授予insert权限可以解决问题。
	*/

	for _, ip := range ips {
		wg.Add(1)
		tokenBucket <- 0 // 在这里操作 token 可以防止过多的协程启动但处于等待 token 的阻塞状态
		go func(ip string) {
			defer func() {
				<-tokenBucket
				wg.Done()
			}()
			defer func() {
				if r := recover(); r != nil {
					errorChan <- fmt.Errorf("inner panic,error:%v", r)
					return
				}
			}()

			var (
				identifiedByPassword string
				CreateUserVersion8   string
				sql                  string
				pswResp              PasswordResp
				err                  error
				sqlTemp              []string
			)

			identifiedByPassword = fmt.Sprintf("IDENTIFIED BY PASSWORD '%s'", multiPsw.Psw)
			CreateUserVersion8 = fmt.Sprintf(`CREATE USER IF NOT EXISTS '%s'@'%s' %s;`, account.User, ip,
				fmt.Sprintf("IDENTIFIED WITH mysql_native_password AS '%s'", multiPsw.Psw))
			// err 为空，没有此账号或者账号密码相同
			pswResp, err = GetPassword(account.User, multiPsw, mysqlVersion, ip, address, tendbhaMasterDomain, bkCloudId, clusterType)
			if err != nil {
				slog.Error("GetPassword", err)
				errorChan <- err
				return
			}

			// 存在此账号，新旧密码相同
			if pswResp.PwdType != "" {
				err = CheckDbCross(account.User, rule.Dbname, ip, address, tendbhaMasterDomain, bkCloudId)
				if err != nil {
					errorChan <- err
					return
				}
				identifiedByPassword = fmt.Sprintf("IDENTIFIED BY PASSWORD '%s'", pswResp.Psw)
				CreateUserVersion8 = fmt.Sprintf(`CREATE USER IF NOT EXISTS '%s'@'%s' %s;`,
					account.User, ip, fmt.Sprintf("IDENTIFIED WITH %s AS '%s'", pswResp.PwdType, pswResp.Psw))
			}
			if (clusterType == tendbha || clusterType == tendbsingle) && MySQLVersionParse(mysqlVersion, "") >=
				MySQLVersionParse("8.0.0", "") {
				sqlTemp = append(sqlTemp, CreateUserVersion8)
				identifiedByPassword = ""
			}
			// 备库域名只授予查询类权限
			if clusterType == tendbha && tendbhaMasterDomain == false {
				// 执行 show databases 可以查看授予 select 的 db。不授予全局 show databases 权限，因为看到所有 db。
				sql = fmt.Sprintf("GRANT SELECT, SHOW VIEW ON `%s`.* TO '%s'@'%s' %s;",
					rule.Dbname, account.User, ip, identifiedByPassword)
				sqlTemp = append(sqlTemp, sql)
				if containConnLogDBFlag {
					sql = fmt.Sprintf("%s '%s'@'%s' %s;", insertConnLogPriv, account.User, ip, identifiedByPassword)
					sqlTemp = append(sqlTemp, sql)
				}
				result.mu.Lock()
				result.backendSQL = append(result.backendSQL, sqlTemp...)
				result.mu.Unlock()
				return
			}

			if rule.DmlDdlPriv != "" {
				sql = fmt.Sprintf("GRANT %s ON `%s`.* TO '%s'@'%s' %s;",
					rule.DmlDdlPriv, rule.Dbname, account.User, ip, identifiedByPassword)
				sqlTemp = append(sqlTemp, sql)
				if needInsertConnLogFlag {
					sql = fmt.Sprintf("%s '%s'@'%s' %s;", insertConnLogPriv, account.User, ip, identifiedByPassword)
					sqlTemp = append(sqlTemp, sql)
				}
			}
			if rule.GlobalPriv != "" {
				sql = fmt.Sprintf(`GRANT %s ON *.* TO '%s'@'%s' %s;`,
					rule.GlobalPriv, account.User, ip, identifiedByPassword)
				// all privileges授予with grant option, 内部调用
				if strings.Contains(strings.ToLower(rule.GlobalPriv), "all privileges") {
					sql = fmt.Sprintf(`GRANT %s ON *.* TO '%s'@'%s' %s with grant option;`,
						rule.GlobalPriv, account.User, ip, identifiedByPassword)
				}
				sqlTemp = append(sqlTemp, sql)
			}

			result.mu.Lock()
			result.backendSQL = append(result.backendSQL, sqlTemp...)
			result.mu.Unlock()
			return
		}(ip)
	}

	/*
		wg.Wait在协程中执行，其被阻塞时，不影响主协程执行select。
		如果errorChan收到一个值，则主协程结束，所有子协程也会一并结束。
		直到所有的上面的子协程结束，errorChan没有值写入，wg.Wait完成并执行close(finishChan)，finishChan被关闭后，select读取finishChan将不被阻塞。
	*/
	go func() {
		wg.Wait()
		close(finishChan)
		close(tokenBucket)
	}()

	select {
	case <-finishChan:
	case err := <-errorChan:
		return nil, err
	}
	result.backendSQL = append(result.backendSQL, setBinlogOn, flushPriv)
	return result.backendSQL, nil
}

// GenerateProxyPrivilege 生成 proxy 新增白名单语句
func GenerateProxyPrivilege(user string, ips []string) []string {
	var (
		sql      string
		proxySQL []string
	)
	for _, ip := range ips {
		sql = fmt.Sprintf("refresh_users('%s@%s','+');", user, ip)
		proxySQL = append(proxySQL, sql)
	}
	return proxySQL
}

// ImportProxyPrivilege proxy 执行新增白名单语句
func ImportProxyPrivilege(proxy Proxy, proxySQL []string, bkCloudId int64) error {
	var errMsg []string
	address := fmt.Sprintf("%s:%d", proxy.IP, proxy.AdminPort)
	for _, grantSQL := range proxySQL {
		queryRequest := QueryRequest{[]string{address}, []string{grantSQL}, true, 30, bkCloudId}
		_, err := OneAddressExecuteProxySql(queryRequest)
		if err != nil {
			errMsg = append(errMsg, fmt.Sprintf("execute(%s) in bk_cloud_id(%d) mysqld(%s:%d) error:%s",
				grantSQL, bkCloudId, proxy.IP, proxy.Port, err.Error()))
		}
	}
	if len(errMsg) > 0 {
		return fmt.Errorf(strings.Join(errMsg, "\n"))
	}
	return nil
}

// GetPassword 实例是否已经存在 user@host,如果不存在，可以新增授权；如果存在并且新旧密码相同，可以新增授权；如果新旧密码不同，不可以新增授权。
func GetPassword(user string, multiPsw MultiPsw, mysqlVersion, ip string, address string,
	masterDomain bool, bkCloudId int64, clusterType string) (PasswordResp, error) {
	var pswResp PasswordResp
	var passwdColName = "password"
	var pswLen int
	var result oneAddressResult
	var err error
	var tipsForProxyIP string

	if (MySQLVersionParse(mysqlVersion, "") > MySQLVersionParse("5.7.5", "")) &&
		(clusterType == tendbha || clusterType == tendbsingle) {
		passwdColName = "authentication_string"
	}

	queryPwdSQL := fmt.Sprintf("SELECT %s AS psw,plugin AS pswType FROM mysql.user WHERE user='%s' AND host='%s'",
		passwdColName, user, ip)
	var queryRequest = QueryRequest{[]string{address}, []string{queryPwdSQL}, true, 60, bkCloudId}

	result, err = OneAddressExecuteSql(queryRequest)
	if err != nil {
		return pswResp, err
	}

	// 在实例上，不存在此账号
	if len(result.CmdResults[0].TableData) == 0 {
		return pswResp, nil
	}

	// 存在密码相同，获取密码类型
	pswResp.Psw = result.CmdResults[0].TableData[0]["psw"].(string)
	pswLen = len(pswResp.Psw)
	if masterDomain {
		tipsForProxyIP = fmt.Sprintf("%s是proxy的IP。", ip)
	}

	switch {
	case pswLen == 41:
		if pswResp.Psw == multiPsw.Psw {
			pswResp.PwdType = "mysql_native_password"
			return pswResp, nil
		}
	case pswLen == 16:
		if pswResp.Psw == multiPsw.OldPsw {
			pswResp.PwdType = "mysql_old_password"
			return pswResp, nil
		}
	case pswLen == 70:
		// caching_sha2_password 生成的密码是动态变化的
		return pswResp, fmt.Errorf("账号(%s@%s)在%s已存在，建议使用mysql_native_password代替caching_sha2_password。%s",
			user, ip, address, tipsForProxyIP)
	default:
		return pswResp, fmt.Errorf("账号(%s@%s)在%s已存在，但是新密码与旧密码不一致，需要保持一致。%s",
			user, ip, address, tipsForProxyIP)
	}
	return pswResp, fmt.Errorf("账号(%s@%s)在%s已存在，但是新密码与旧密码不一致，需要保持一致。%s",
		user, ip, address, tipsForProxyIP)
}

// CheckDbCross 如果 user@host 已存在，CheckDbCross 检查已授权的数据库和准备授权的数据库是否有包含关系。
// 如果有包含关系，不可以授权，因为鉴权去匹配到多条权限中的某一条，存在不确定性
func CheckDbCross(user string, dbname string, ip string, address string, masterDomain bool, bkCloudId int64) error {
	QueryGrantDbSQL := fmt.Sprintf("select db from mysql.db where user='%s' and host = '%s';", user, ip)
	var result oneAddressResult
	var errMsg []string
	var err error
	var queryRequest = QueryRequest{[]string{address}, []string{QueryGrantDbSQL}, true, 60, bkCloudId}
	var tipsForProxyIP string

	result, err = OneAddressExecuteSql(queryRequest)
	if err != nil {
		slog.Error("QueryGrantDbSQL", err)
		return err
	}

	if len(result.CmdResults[0].TableData) == 0 {
		slog.Info("if dbname cross, check ok")
		return nil
	}

	newDBRegexp := mysqlGrantDBToReg(dbname)
	percentrBegin := regexp.MustCompile("^%.*$")
	percentrEnd := regexp.MustCompile("^.*%$")

	for _, grantDb := range result.CmdResults[0].TableData {
		existDb := grantDb["db"].(string)
		if dbname == existDb {
			continue
		}
		existDbRegexp := mysqlGrantDBToReg(existDb)
		/*
			bug: （%d%、%h%）或者（d%、%h）存在交集，newDBRegexp.MatchString(existDb)、existDbRegexp.MatchString(dbname)无法判断出交集
			fix: 已存在的db与新db规则如果都包含%，并且，一个在开头有%，一个在结尾有%，存在交集情况
		*/
		if newDBRegexp.MatchString(existDb) || existDbRegexp.MatchString(dbname) ||
			(percentrBegin.MatchString(existDb) && percentrEnd.MatchString(dbname)) ||
			(percentrBegin.MatchString(dbname) && percentrEnd.MatchString(existDb)) {
			if masterDomain {
				tipsForProxyIP = fmt.Sprintf("%s是proxy的IP。", ip)
			}
			// 已授权的数据库和准备授权的数据库有包含关系
			// 单个的%转换为%%,避免 fmt.Sprintf 对于%输出%!`(MISSING)
			msg := fmt.Sprintf("账号(%s@%s)在%s已经对数据库[`%s`]授权，新增授权中的数据库[`%s`]与数据库[`%s`]存在交集，不可以授权。%s",
				user, ip, address, strings.Replace(existDb, "%", "%%", -1),
				strings.Replace(dbname, "%", "%%", -1),
				strings.Replace(existDb, "%", "%%", -1), tipsForProxyIP)
			errMsg = append(errMsg, msg)
			continue
		}
	}
	if len(errMsg) > 0 {
		return fmt.Errorf(strings.Join(errMsg, "\n"))
	}
	return nil
}

// mysqlGrantDBToReg 数据库名转换为正则表达式
func mysqlGrantDBToReg(dbName string) *regexp.Regexp {
	dbNameRegStr := strings.Replace(dbName, "%", ".*", -1)
	return regexp.MustCompile(fmt.Sprintf("^%s$", dbNameRegStr))
}

// GetMySQLVersion 获取实例的 mysql 版本
func GetMySQLVersion(address string, bkCloudId int64) (version string, err error) {
	var output oneAddressResult
	var queryRequest = QueryRequest{[]string{address}, []string{"select version() as version;"}, true, 30, bkCloudId}
	output, err = OneAddressExecuteSql(queryRequest)
	if err != nil {
		slog.Error("msg", err)
		return "", err
	}
	return output.CmdResults[0].TableData[0]["version"].(string), nil
}

// DeduplicationIP 检查授权对象 host 的格式，并且去重
func DeduplicationIP(sourceIPs []string) ([]string, []string) {
	var (
		errMsg  []string
		ips     []string
		UniqMap = make(map[string]struct{})
	)

	// 相同 ip 要去重，相同 user 的授权 ip 记录（包括1.1.1.1或者带%）
	reg := regexp.MustCompile(`(\d+\.)+\%`)
	for _, ip := range sourceIPs {
		ip = strings.TrimSpace(ip)
		// 检验访问来源 ip 格式，是否为 ip，或者 localhost 或者是否包含%
		if !(govalidator.IsIP(ip) || ip == "localhost" || ip == "%" || reg.MatchString(ip)) {
			errMsg = append(errMsg, fmt.Sprintf("%s is not an valid ip", ip))
			continue
		}
		if _, isExists := UniqMap[ip]; isExists == true {
			continue
		}
		UniqMap[ip] = struct{}{}
		ips = append(ips, ip)
	}
	if len(errMsg) > 0 {
		return nil, errMsg
	}

	return ips, nil
}

// DeduplicationTargetInstance 检查实例是否存在，是否使用与类型相匹配的单据，并且去重
func DeduplicationTargetInstance(instances []string, clusterType string) ([]string, []string) {
	var (
		errMsg  []string
		dnsList []string
		dns     Domain
		UniqMap = make(map[string]struct{})
		err     error
	)

	client := util.NewClientByHosts(viper.GetString("dbmeta"))
	for _, instance := range instances {
		instance = strings.Trim(strings.TrimSpace(instance), ".")
		if !govalidator.IsDNSName(instance) {
			err = fmt.Errorf("%s is not an valid domain name", instance)
			errMsg = append(errMsg, err.Error())
			continue
		}
		dns = Domain{EntryName: instance}
		_, err = GetCluster(client, clusterType, dns)
		if err != nil {
			errMsg = append(errMsg, err.Error())
			continue
		}
		if _, isExists := UniqMap[instance]; isExists == true {
			continue
		}
		UniqMap[instance] = struct{}{}
		dnsList = append(dnsList, instance)
	}
	if len(errMsg) > 0 {
		return nil, errMsg
	}
	return dnsList, nil
}

// MySQLVersionParse 解析 mysql 版本
func MySQLVersionParse(mysqlVersion, prefix string) uint64 {
	var matchExp = ""
	if prefix == "" {
		matchExp = "([\\d]+).?([\\d]+)?.?([\\d]+)?"
	} else {
		matchExp = fmt.Sprintf("%s-([\\d]+).?([\\d]+)?.?([\\d]+)?", prefix)
	}
	re := regexp.MustCompile(matchExp)
	result := re.FindStringSubmatch(mysqlVersion)
	// [tmysql-2.10.3 2 10 3]
	var (
		total    uint64
		billion  string
		thousand string
		single   string
		// 2.1.5  => 2 * 1000000 + 1 * 1000 + 5
	)
	if len(result) == 0 {
		return 0
	} else if len(result) == 4 {
		billion = result[1]
		thousand = result[2]
		single = result[3]
		if billion != "" {
			b, err := strconv.ParseUint(billion, 10, 64)
			if err != nil {
				slog.Error("msg", err)
				b = 0
			}
			total += b * 1000000
		}
		if thousand != "" {
			t, err := strconv.ParseUint(thousand, 10, 64)
			if err != nil {
				slog.Error("msg", err)
				t = 0
			}
			total += t * 1000
		}
		if single != "" {
			s, err := strconv.ParseUint(single, 10, 64)
			if err != nil {
				slog.Error("msg", err)
				s = 0
			}
			total += s
		}
	} else {
		// impossible condition,just for safe.
		return 0
	}
	return total
}

// ContainConnLogDB TODO
func ContainConnLogDB(dbname string) bool {
	DBRegexp := mysqlGrantDBToReg(dbname)
	if DBRegexp.MatchString(connLogDB) {
		return true
	}
	return false
}

// AddPrivResult 展示授权结果
func AddPrivResult(errMsg, successMsg Err) error {
	// 全部成功列表
	fail := errno.GrantPrivilegesFail.Add("\n" + strings.Join(errMsg.errs, "\n"))
	// 全部失败列表
	success := errno.GrantPrivilegesSuccess.Add("\n" + strings.Join(successMsg.errs, "\n"))
	// 部分失败
	subFail := errno.GrantPrivilegesFail.Add("\n" + strings.Join(errMsg.errs, "\n") + "\n\n\n\n" + success.Error())

	if len(errMsg.errs) > 0 {
		if len(successMsg.errs) > 0 {
			return subFail
		}
		return fail
	}
	return success
}

package service

import (
	"context"
	"fmt"
	"log/slog"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"

	"golang.org/x/time/rate"

	"dbm-services/mysql/priv-service/util"

	"github.com/pingcap/tidb/parser"
	"github.com/pingcap/tidb/parser/ast"
)

// Enter TODO
func (v *visitor) Enter(node ast.Node) (out ast.Node, skipChildren bool) {
	if grantstmt, ok := node.(*ast.GrantStmt); ok {
		v.secText = grantstmt.SecureText()
		v.username = grantstmt.Users[0].User.Username
		v.secPassword, v.legal = grantstmt.Users[0].EncodedPassword()
		v.withgrant = grantstmt.WithGrant
		v.hostname = grantstmt.Users[0].User.Hostname
	}
	return node, false
}

// Leave TODO
func (v *visitor) Leave(node ast.Node) (out ast.Node, ok bool) {
	return node, true
}

// GetRemotePrivilege 获取mysql上的授权语句
func GetRemotePrivilege(address string, host string, bkCloudId int64, instanceType string,
	user string, raw bool) ([]UserGrant, error) {
	var version string
	var errOuter error
	var repsOuter oneAddressResult
	// ResultTemp 授权语句集合
	type ResultTemp struct {
		mu         sync.RWMutex
		userGrants []UserGrant
	}
	var resultTemp ResultTemp
	needShowCreateUser := false
	wg := sync.WaitGroup{}
	finishChan := make(chan bool, 1)
	errorChan := make(chan error, 1)
	// 权限并行过高，引起实例Waiting for table metadata lock；并行过低，效率低
	limit := rate.Every(time.Millisecond * 50) // QPS：20
	burst := 20                                // 桶容量 20
	limiter := rate.NewLimiter(limit, burst)
	version, errOuter = GetMySQLVersion(address, bkCloudId)
	if errOuter != nil {
		return nil, errOuter
	}
	if MySQLVersionParse(version, "") > MySQLVersionParse("5.7.8", "") &&
		(instanceType == machineTypeBackend || instanceType == machineTypeSingle ||
			instanceType == machineTypeRemote) {
		needShowCreateUser = true
	}
	selectUser := `select user,host from mysql.user where 1=1 `
	if host != "" {
		selectUser += fmt.Sprintf(` and host in ('%s') `, host)
	}
	if user != "" {
		selectUser += fmt.Sprintf(` and user in ('%s') `, user)
	}
	// 根据目标ip模糊匹配查询或者客户端克隆，避免匹配到内部用户
	if raw {
		selectUser += " and user !='MONITOR' "
	}
	slog.Info("msg", "selectUser", selectUser)
	queryRequestOuter := QueryRequest{[]string{address}, []string{selectUser},
		true, 30, bkCloudId}
	repsOuter, errOuter = OneAddressExecuteSql(queryRequestOuter)
	if errOuter != nil {
		return nil, errOuter
	}
	slog.Info("users", "repsOuter.CmdResults[0].TableData", repsOuter.CmdResults[0].TableData)
	for _, row := range repsOuter.CmdResults[0].TableData {
		if row["user"] == "" || row["host"] == "" {
			return nil, fmt.Errorf("execute %s in %s ,user or host is null", selectUser, address)
		}
		userHost := fmt.Sprintf(`'%s'@'%s'`, row["user"].(string), row["host"].(string))
		wg.Add(1)
		errLimiter := limiter.Wait(context.Background())
		if errLimiter != nil {
			slog.Error("msg", "limiter.Wait", errLimiter)
			return nil, errLimiter
		}
		// tokenBucket <- 0 // 在这里操作 token 可以防止过多的协程启动但处于等待 token 的阻塞状态
		go func(userHost string, needShowCreateUser bool) {
			defer func() {
				wg.Done()
				// <-tokenBucket
			}()
			Grants, err := GetUserGantSql(needShowCreateUser, userHost, address, bkCloudId)
			if err != nil {
				errorChan <- err
				return
			}
			resultTemp.mu.Lock()
			resultTemp.userGrants = append(resultTemp.userGrants, UserGrant{userHost, Grants})
			resultTemp.mu.Unlock()
		}(userHost, needShowCreateUser)
	}
	go func() {
		wg.Wait()
		close(finishChan)
		// close(tokenBucket)
	}()

	select {
	case <-finishChan:
	case err := <-errorChan:
		return nil, err
	}
	if len(resultTemp.userGrants) == 0 {
		return nil, nil
	}
	return resultTemp.userGrants, nil
}

// GetUserGantSql 查询用户创建以及授权语句
func GetUserGantSql(needShowCreateUser bool, userHost, address string, bkCloudId int64) ([]string, error) {
	var (
		sql    string
		grants []string
	)
	var sqls []string
	if needShowCreateUser {
		sql = fmt.Sprintf("show create user %s;", userHost)
		sqls = append(sqls, sql)
	}
	sqls = append(sqls, fmt.Sprintf("show grants for %s ", userHost))
	queryRequest := QueryRequest{[]string{address}, sqls, true, 60, bkCloudId}
	reps, err := OneAddressExecuteSql(queryRequest)
	if err != nil {
		return grants, fmt.Errorf("execute (%s) fail, error:%s", sqls, err.Error())
	}
	for _, data := range reps.CmdResults {
		for _, item := range data.TableData {
			for _, grant := range item {
				if grant != nil {
					grants = append(grants, grant.(string))
				} else {
					return grants, fmt.Errorf("execute (%s), content of return is null", sqls)
				}
			}
		}
	}
	if len(grants) == 0 {
		return grants, fmt.Errorf("show grants in %s fail,query return nothing", userHost)
	}
	return grants, nil
}

// DealWithPrivileges 处理授权语句，做版本兼容
func (m *CloneInstancePrivPara) DealWithPrivileges(userGrants []UserGrant, instanceType string) ([]UserGrant, error) {
	newUserGrants := NewUserGrants{}
	m.Source.Address = strings.TrimSpace(m.Source.Address)
	m.Target.Address = strings.TrimSpace(m.Target.Address)
	sourceVersion, err := GetMySQLVersion(m.Source.Address, *m.BkCloudId)
	if err != nil {
		return newUserGrants.Data, err
	}
	targetVersion, err := GetMySQLVersion(m.Target.Address, *m.BkCloudId)
	if err != nil {
		return newUserGrants.Data, err
	}
	sourceIp := strings.Split(m.Source.Address, ":")[0]
	targetIp := strings.Split(m.Target.Address, ":")[0]
	var mysql5Tomysql8, mysql80Tomysql57, mysql57Tomysql56, mysql8 bool
	// mysql8.0克隆到mysql5.7。后面有新版本比如验证mysql8.1，就把8000改为8001

	if instanceType == machineTypeBackend || instanceType == machineTypeSingle ||
		instanceType == machineTypeRemote {
		if MySQLVersionParse(sourceVersion, "")/1000 == 8000 &&
			MySQLVersionParse(targetVersion, "")/1000 == 5007 {
			mysql80Tomysql57 = true
		} else if MySQLVersionParse(sourceVersion, "")/1000 == 5007 &&
			MySQLVersionParse(targetVersion, "")/1000 == 5006 {
			mysql57Tomysql56 = true
		} else if MySQLVersionParse(sourceVersion, "")/1000 < 8000 &&
			MySQLVersionParse(targetVersion, "")/1000 >= 8000 {
			mysql5Tomysql8 = true
		} else if MySQLVersionParse(sourceVersion, "")/1000 == 8000 {
			mysql8 = true
		}
	}

	wg := sync.WaitGroup{}
	errorChan := make(chan error, 1)
	finishChan := make(chan bool, 1)
	// Delete system user
	var userExcluded = []string{"ADMIN", "mysql.session", "mysql.sys", "mysql.infoschema", "spider"}
	for _, row := range userGrants {
		wg.Add(1)
		go func(row UserGrant, targetIp, sourceIp string) {
			defer wg.Done()
			defer func() {
				if r := recover(); r != nil {
					slog.Info("(Merge tree)panic error:%v", r)
					errorChan <- fmt.Errorf("(Merge tree)panic error:%v", r)
					return
				}
			}()
			for _, user := range userExcluded { // delete system user
				if regexp.MustCompile(fmt.Sprintf("['`]%s['`]", user)).MatchString(row.UserHost) {
					return
				}
			}
			reg := regexp.MustCompile(fmt.Sprintf("['`]%s['`]", targetIp)) // delete local ip user
			if reg.MatchString(row.UserHost) {
				return
			}
			reg = regexp.MustCompile(fmt.Sprintf("['`]%s['`]", sourceIp)) // change source ip user to local ip user
			if reg.MatchString(row.UserHost) {
				row.UserHost = reg.ReplaceAllString(row.UserHost, fmt.Sprintf(`%s`, targetIp))
				var tmp []string
				for _, str := range row.Grants {
					tmp = append(tmp, reg.ReplaceAllString(str, fmt.Sprintf(`%s`, targetIp)))
				}
				row.Grants = tmp
			}
			tmp, errInner := DiffVersionConvert(row.Grants, mysql80Tomysql57, mysql57Tomysql56, mysql5Tomysql8, mysql8)
			if errInner != nil {
				errorChan <- errInner
				return
			}
			row.Grants = tmp
			newUserGrants.mu.Lock()
			newUserGrants.Data = append(newUserGrants.Data, row)
			newUserGrants.mu.Unlock()
			return
		}(row, targetIp, sourceIp)
	}
	go func() {
		wg.Wait()
		close(finishChan)
	}()
	select {
	case <-finishChan:
	case err := <-errorChan:
		return nil, err
	}
	return newUserGrants.Data, nil
}

// DiffVersionConvert 跨版本克隆权限对授权语句变形，做兼容
func DiffVersionConvert(grants []string, mysql80Tomysql57, mysql57Tomysql56, mysql5Tomysql8, mysql8 bool) ([]string, error) {
	var err error
	var tmp []string
	regForCreateUser := regexp.MustCompile(`(?i)^\s*CREATE USER `) // CREATE USER变为CREATE USER IF NOT EXISTS
	regForPasswordExpired := regexp.MustCompile(
		`(?i)\s*REQUIRE NONE PASSWORD EXPIRE DEFAULT ACCOUNT UNLOCK`,
	) // 5.7->5.6去掉
	regForConnLog := regexp.MustCompile("`test`.`conn_log`") // `test`.`conn_log`变为 infodba_schema.conn_log

	switch {
	case mysql80Tomysql57:
		tmp, err = PrivMysql80ToMysql57(grants)
		if err != nil {
			return tmp, err
		}
	case mysql57Tomysql56:
		for _, str := range grants {
			if regForPasswordExpired.MatchString(str) {
				str = regForPasswordExpired.ReplaceAllString(str, ``)
			}
			if regForCreateUser.MatchString(str) {
				str = regForCreateUser.ReplaceAllString(str, `CREATE USER /*!50706 IF NOT EXISTS */ `)
			}
			if regForConnLog.MatchString(str) {
				str = regForConnLog.ReplaceAllString(str, `infodba_schema.conn_log`)
			}
			tmp = append(tmp, str)
		}
		return tmp, nil
	case mysql5Tomysql8:
		tmp, err = PrivMysql5ToMysql8(grants)
		if err != nil {
			return tmp, err
		}
	case mysql8:
		tmp = PrivMysql8(grants)
	default:
		for _, str := range grants {
			if regForCreateUser.MatchString(str) {
				str = regForCreateUser.ReplaceAllString(str, `CREATE USER /*!50706 IF NOT EXISTS */ `)
			}
			if regForConnLog.MatchString(str) {
				str = regForConnLog.ReplaceAllString(str, `infodba_schema.conn_log`)
			}
			tmp = append(tmp, str)
		}
	}
	return tmp, nil
}

// PrivMysql8 剔除txsql 8.0包含的动态权限
func PrivMysql8(grants []string) []string {
	var tmp []string
	regForCreateUser := regexp.MustCompile(`(?i)^\s*CREATE USER `) // CREATE USER变为CREATE USER IF NOT EXISTS
	regForConnLog := regexp.MustCompile("`test`.`conn_log`")       // `test`.`conn_log`变为 infodba_schema.conn_log
	// 8.0.30-txsql 包含的动态权限，但是开源版本不支持
	var onlyForTxsql = []string{"READ_MASK"}
	for _, item := range grants {
		dynamicGrantsFlag := false
		for _, priv := range onlyForTxsql {
			if regexp.MustCompile(priv).MatchString(item) {
				slog.Info("dynamicGrantExist", "sql", item)
				dynamicGrantsFlag = true
				break
			}
		}
		if dynamicGrantsFlag == true {
			continue
		}
		if regForCreateUser.MatchString(item) {
			item = regForCreateUser.ReplaceAllString(item, `CREATE USER /*!50706 IF NOT EXISTS */ `)
		}
		if regForConnLog.MatchString(item) {
			item = regForConnLog.ReplaceAllString(item, `infodba_schema.conn_log`)
		}
		tmp = append(tmp, item)
	}
	return tmp
}

// PrivMysql5ToMysql8 Mysql5授权语句向Mysql8兼容
func PrivMysql5ToMysql8(grants []string) ([]string, error) {
	var tmp []string
	regForCreateUser := regexp.MustCompile(`(?i)^\s*CREATE USER `) // CREATE USER变为CREATE USER IF NOT EXISTS
	regForConnLog := regexp.MustCompile("`test`.`conn_log`")       // `test`.`conn_log`变为 infodba_schema.conn_log
	regForPlainText := regexp.MustCompile(`(?i)\s+IDENTIFIED\s+BY\s+`)
	for _, item := range grants {
		if regForCreateUser.MatchString(item) {
			item = regForCreateUser.ReplaceAllString(item, `CREATE USER /*!50706 IF NOT EXISTS */ `)
		}
		if regForConnLog.MatchString(item) {
			item = regForConnLog.ReplaceAllString(item, `infodba_schema.conn_log`)
		}
		if regForPlainText.MatchString(item) {
			sqlParser := parser.New()
			stmtNodes, warns, err := sqlParser.Parse(item, "", "")
			if err != nil {
				return tmp, fmt.Errorf("parse sql failed, sql:%s, error:%s", item, err.Error())
			}
			if len(warns) > 0 {
				slog.Warn("some warnings happend", warns)
			}
			for _, stmtNode := range stmtNodes {
				v := visitor{}
				stmtNode.Accept(&v)
				if !v.legal {
					return tmp, fmt.Errorf("parse pass,but sql format error,sql:%s", item)
				}
				// statement which have password need to CREATE USER
				if v.legal && len(v.secPassword) > 0 {
					tmp = append(
						tmp, fmt.Sprintf(
							"CREATE USER IF NOT EXISTS '%s'@'%s' IDENTIFIED WITH mysql_native_password AS '%s';",
							v.username,
							v.hostname,
							v.secPassword,
						),
					)
				}

				if v.withgrant {
					v.secText += " WITH GRANT OPTION"
				}
				tmp = append(tmp, v.secText+";")
			}
		} else {
			tmp = append(tmp, item)
		}
	}
	return tmp, nil
}

// PrivMysql80ToMysql57 Mysql8.0授权语句向Mysql5.7兼容
func PrivMysql80ToMysql57(grants []string) ([]string, error) {
	var tmp []string
	var dynamicGrantsForMySQL8 = []string{
		"APPLICATION_PASSWORD_ADMIN",
		"AUDIT_ADMIN",
		"BACKUP_ADMIN",
		"BINLOG_ADMIN",
		"BINLOG_ENCRYPTION_ADMIN",
		"CLONE_ADMIN",
		"SERVICE_CONNECTION_ADMIN",
		"CONNECTION_ADMIN",
		"ENCRYPTION_KEY_ADMIN",
		"GROUP_REPLICATION_ADMIN",
		"INNODB_REDO_LOG_ARCHIVE",
		"PERSIST_RO_VARIABLES_ADMIN",
		"REPLICATION_APPLIER",
		"REPLICATION_SLAVE_ADMIN",
		"RESOURCE_GROUP_ADMIN",
		"RESOURCE_GROUP_USER",
		"ROLE_ADMIN",
		"SESSION_VARIABLES_ADMIN",
		"SET_USER_ID",
		"SYSTEM_USER",
		"SYSTEM_VARIABLES_ADMIN",
		"TABLE_ENCRYPTION_ADMIN",
		"XA_RECOVER_ADMIN",
	}
	var staticGrantsForMySQL8 = []string{"CREATE ROLE", "DROP ROLE"}

	regForPasswordOption := regexp.MustCompile(
		`(?i)\s*PASSWORD HISTORY DEFAULT PASSWORD REUSE INTERVAL DEFAULT PASSWORD REQUIRE CURRENT DEFAULT`,
	) // 5.8->5.7去掉
	regForCreateUser := regexp.MustCompile(`(?i)^\s*CREATE USER `) // CREATE USER变为CREATE USER IF NOT EXISTS
	regForPasswordPlugin := regexp.MustCompile(
		`'caching_sha2_password'`,
	) // 排除8.0使用caching_sha2_password作为密码验证方式
	regForConnLog := regexp.MustCompile("`test`.`conn_log`") // `test`.`conn_log`变为 infodba_schema.conn_log

	for _, item := range grants {
		if regForPasswordOption.MatchString(item) {
			item = regForPasswordOption.ReplaceAllString(item, ``)
		}

		dynamicGrantsFlag := false
		for _, dynamic := range dynamicGrantsForMySQL8 {
			/* 排除8.0的动态权限
			   在8.0 grant all privileges on *.* to xxx，show grants for xxx结果：
			   (1) GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, RELOAD, SHUTDOWN, PROCESS, FILE,
			   REFERENCES, INDEX, ALTER, SHOW DATABASES, SUPER, CREATE TEMPORARY TABLES, LOCK TABLES,
			   EXECUTE, REPLICATION SLAVE, REPLICATION CLIENT, CREATE VIEW, SHOW VIEW, CREATE ROUTINE,
			   ALTER ROUTINE, CREATE USER, EVENT, TRIGGER, CREATE TABLESPACE, CREATE ROLE,
			   DROP ROLE ON *.* TO xxx
			   (2) GRANT APPLICATION_PASSWORD_ADMIN,AUDIT_ADMIN,BACKUP_ADMIN,BINLOG_ADMIN,
			   BINLOG_ENCRYPTION_ADMIN,CLONE_ADMIN,CONNECTION_ADMIN,ENCRYPTION_KEY_ADMIN,
			   GROUP_REPLICATION_ADMIN,INNODB_REDO_LOG_ARCHIVE,PERSIST_RO_VARIABLES_ADMIN,
			   REPLICATION_APPLIER,REPLICATION_SLAVE_ADMIN,RESOURCE_GROUP_ADMIN,RESOURCE_GROUP_USER,
			   ROLE_ADMIN,SERVICE_CONNECTION_ADMIN,SESSION_VARIABLES_ADMIN,SET_USER_ID,SYSTEM_USER,
			   SYSTEM_VARIABLES_ADMIN,TABLE_ENCRYPTION_ADMIN,XA_RECOVER_ADMIN ON *.* TO xxx;
			   固定权限（1）8.0比5.7多了CREATE ROLE, DROP ROLE；8.0有动态权限，5.7没有
			*/
			if regexp.MustCompile(dynamic).MatchString(item) {
				slog.Info("dynamicGrantExist", "sql", item)
				dynamicGrantsFlag = true
				break
			}
		}
		if dynamicGrantsFlag == true {
			continue
		}

		for _, _static := range staticGrantsForMySQL8 {
			if regexp.MustCompile(_static).MatchString(item) {
				// 8.0 CREATE ROLE, DROP ROLE 替换为CREATE USER

				// 5.7 CREATE USER: Enables use of the ALTER USER, CREATE USER, DROP USER, RENAME USER,
				// and REVOKE ALL PRIVILEGES

				// 8.0 CREATE USER: Enables use of the ALTER USER, CREATE ROLE, CREATE USER, DROP ROLE,
				// DROP USER, RENAME USER, and REVOKE ALL PRIVILEGES statements.
				item = regexp.MustCompile(_static).ReplaceAllString(item, "CREATE USER")
			}
		}
		if regForPasswordPlugin.MatchString(item) {
			return tmp, fmt.Errorf("using caching_sha2_password, sql: %s", item)
		}
		if regForCreateUser.MatchString(item) {
			item = regForCreateUser.ReplaceAllString(item, `CREATE USER /*!50706 IF NOT EXISTS */ `)
		}
		if regForConnLog.MatchString(item) {
			item = regForConnLog.ReplaceAllString(item, `infodba_schema.conn_log`)
		}
		tmp = append(tmp, item)
	}
	return tmp, nil
}

// ValidateInstancePair 验证实例是否存在
func ValidateInstancePair(source, target InstancePara) (string, error) {
	var errMsg []string
	var instanceType string
	// 格式是否为ip:port
	if !util.IsIPPortFormat(source.Address) {
		errMsg = append(errMsg, fmt.Sprintf("sourceDBInstance(%s) is not a valid instance", source))
	}

	if !util.IsIPPortFormat(target.Address) {
		errMsg = append(errMsg, fmt.Sprintf("targetDBInstance(%s) is not a valid instance", target))
	}

	// 源实例和目标实例不能是同一个实例
	if source.Address == target.Address && source.Address != "" {
		errMsg = append(errMsg, "Source instance and target instance are the same one")
	}

	if len(errMsg) > 0 {
		return instanceType, fmt.Errorf(strings.Join(errMsg, "\n"))
	}

	// 类型是否相同
	instanceType = source.MachineType
	if source.MachineType != target.MachineType {
		if !((source.MachineType == machineTypeBackend || source.MachineType == machineTypeSingle) &&
			(target.MachineType == machineTypeBackend || target.MachineType == machineTypeSingle)) {
			errMsg = append(
				errMsg, fmt.Sprintf(
					"instance type not same, %s is %s,but %s is %s ", source.Address,
					source.MachineType, target.Address, target.MachineType,
				),
			)
		} else {
			instanceType = machineTypeBackend
		}
	}
	if len(errMsg) > 0 {
		return instanceType, fmt.Errorf(strings.Join(errMsg, "\n"))
	}
	return instanceType, nil
}

// CheckGrantInMySqlVersion 目标实例低于mysql 5，不能执行包含mysql_native_password加密方式的授权语句
func CheckGrantInMySqlVersion(userGrants []UserGrant, address string, bkCloudId int64) error {
	localBigVersion := ""
	if version, err := GetMySQLVersion(address, bkCloudId); err != nil {
		return err
	} else {
		reg := regexp.MustCompile(`\.+`)
		array := reg.Split(version, -1)
		if len(array) == 0 {
			return fmt.Errorf("获取%s的mysql大版本失败", address)
		}
		localBigVersion = array[0]
	}

	if localBigVersion >= "5" {
		return nil
	}

	for _, row := range userGrants {
		for _, str := range row.Grants {
			reg := regexp.MustCompile(`BY PASSWORD '\*`)
			if reg.MatchString(str) {
				return fmt.Errorf("目标实例%s的大版本是%s,低于5.0，不支持mysql_native_password加密方式", localBigVersion)
			}
		}
	}
	return nil
}

// ImportMysqlPrivileges 执行mysql权限
func ImportMysqlPrivileges(userGrants []UserGrant, address string, bkCloudId int64) error {
	var errMsg Err
	var grantRetry NewUserGrants
	wg := sync.WaitGroup{}
	limit := rate.Every(time.Millisecond * 50) // QPS：20
	burst := 20                                // 桶容量 20
	limiter := rate.NewLimiter(limit, burst)
	for _, row := range userGrants {
		errLimiter := limiter.Wait(context.Background())
		if errLimiter != nil {
			slog.Error("msg", "limiter.Wait", errLimiter)
			return errLimiter
		}
		wg.Add(1)
		go func(row UserGrant) {
			defer func() {
				wg.Done()
			}()
			queryRequest := QueryRequest{[]string{address}, row.Grants, true, 60, bkCloudId}
			_, err := OneAddressExecuteSql(queryRequest)
			if err != nil {
				if strings.Contains(err.Error(), "ERROR 1410") {
					/* mysql 8.0及以上的问题处理：
					show grants for testuser@1.1.1.1可以看到模糊匹配到的账号权限，
					比如'testuser'@'%'的grant语句GRANT SELECT, SHOW VIEW ON `db1`.* TO 'testuser'@'%'。
					show grants for testuser@1.1.1.1;
					+-------------------------------------------------------
					| Grants for testuser@1.1.1.1
					+-------------------------------------------------------
					| GRANT FILE ON *.* TO 'testuser'@'1.1.1.1'
					| GRANT SELECT, INSERT ON `db1`.* TO 'testuser'@'1.1.1.1'
					| GRANT SELECT, SHOW VIEW ON `db1`.* TO 'testuser'@'%'
					+--------------------------------------------------------

					但是并行创建用户，如果'testuser'@'%'还没有创建，在mysql 8.0版本执行这个grant语句，会报错。
					需要在create user之后再执行grant。
					GRANT SELECT, SHOW VIEW ON `db1`.* TO 'testuser'@'%';
					ERROR 1410 (42000): You are not allowed to create a user with GRANT

					实际上对于'testuser'@'%'用户的create和grant会在'testuser'@'%'用户的授权中完成，这里的报错是可以忽略的，稳妥起见重试。
					*/
					grantRetry.mu.Lock()
					grantRetry.Data = append(grantRetry.Data, row)
					grantRetry.mu.Unlock()
					return
				}
				errMsg.mu.Lock()
				errMsg.errs = append(errMsg.errs, err.Error())
				errMsg.mu.Unlock()
				return
			}
		}(row)
	}
	wg.Wait()
	slog.Info("msg", "retry for 8.0", grantRetry.Data)
	for _, row := range grantRetry.Data {
		errLimiter := limiter.Wait(context.Background())
		if errLimiter != nil {
			slog.Error("msg", "limiter.Wait", errLimiter)
			return errLimiter
		}
		wg.Add(1)
		go func(row UserGrant) {
			defer func() {
				wg.Done()
			}()
			queryRequest := QueryRequest{[]string{address}, row.Grants, true, 60, bkCloudId}
			_, err := OneAddressExecuteSql(queryRequest)
			if err != nil {
				errMsg.mu.Lock()
				errMsg.errs = append(errMsg.errs, err.Error())
				errMsg.mu.Unlock()
				return
			}
		}(row)
	}
	wg.Wait()
	queryRequest := QueryRequest{[]string{address}, []string{flushPriv}, true, 60, bkCloudId}
	_, err := OneAddressExecuteSql(queryRequest)
	if err != nil {
		errMsg.mu.Lock()
		errMsg.errs = append(errMsg.errs, err.Error())
		errMsg.mu.Unlock()
	}
	if len(errMsg.errs) > 0 {
		return fmt.Errorf(strings.Join(errMsg.errs, "\n"))
	}
	return nil
}

// changeToProxyAdminPort 获取proxy管理端口
func changeToProxyAdminPort(address string) (string, error) {
	tmp := strings.Split(address, ":")
	port, err := strconv.ParseInt(tmp[1], 10, 64)
	if err != nil {
		return "", err
	}
	return fmt.Sprintf("%s:%s", tmp[0], strconv.FormatInt(port+1000, 10)), nil
}

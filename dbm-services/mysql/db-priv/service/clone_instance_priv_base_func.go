package service

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"
	"sync"

	"dbm-services/mysql/priv-service/util"

	"github.com/pingcap/parser"
	"github.com/pingcap/parser/ast"
	_ "github.com/pingcap/tidb/types/parser_driver" // parser_driver TODO
	"golang.org/x/exp/slog"
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
func GetRemotePrivilege(address string, host string, bkCloudId int64, instanceType string) ([]UserGrant, error) {
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
	tokenBucket := make(chan int, 10)

	version, errOuter = GetMySQLVersion(address, bkCloudId)
	if errOuter != nil {
		return nil, errOuter
	}
	if MySQLVersionParse(version, "") > MySQLVersionParse("5.7.8", "") &&
		(instanceType == machineTypeBackend || instanceType == machineTypeSingle ||
			instanceType == machineTypeRemote) {
		needShowCreateUser = true
	}
	selectUser := `select user,host from mysql.user`
	if host != "" {
		selectUser += fmt.Sprintf(` where host='%s'`, host)
	}
	queryRequestOuter := QueryRequest{[]string{address}, []string{selectUser}, true, 30, bkCloudId}
	repsOuter, errOuter = OneAddressExecuteSql(queryRequestOuter)
	if errOuter != nil {
		return nil, errOuter
	}
	flush := UserGrant{"", []string{flushPriv}}
	resultTemp.userGrants = append([]UserGrant{flush}, resultTemp.userGrants...)

	for _, row := range repsOuter.CmdResults[0].TableData {
		if row["user"] == "" || row["host"] == "" {
			return nil, fmt.Errorf("execute %s in %s ,user or host is null", selectUser, address)
		}
		userHost := fmt.Sprintf(`'%s'@'%s'`, row["user"], row["host"])
		wg.Add(1)
		tokenBucket <- 0 // 在这里操作 token 可以防止过多的协程启动但处于等待 token 的阻塞状态
		go func(userHost string, needShowCreateUser bool) {
			defer func() {
				<-tokenBucket
				wg.Done()
			}()
			var Grants []string
			var err error
			err = GetUserGantSql(needShowCreateUser, userHost, address, &Grants, bkCloudId)
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
		close(tokenBucket)
	}()

	select {
	case <-finishChan:
	case err := <-errorChan:
		return nil, err
	}
	return append(resultTemp.userGrants, flush), nil
}

// GetUserGantSql 查询用户创建以及授权语句
func GetUserGantSql(needShowCreateUser bool, userHost, address string, grants *[]string, bkCloudId int64) error {
	var (
		sql      string
		err      error
		hasValue bool
	)
	if needShowCreateUser {
		sql = fmt.Sprintf("show create user %s;", userHost)
		err, hasValue = GetGrantResponse(sql, address, grants, bkCloudId)
		if err != nil {
			return err
		} else if !hasValue {
			return fmt.Errorf("execute (%s) return nothing", sql)
		}
	}
	sql = fmt.Sprintf("show grants for %s ", userHost)
	err, _ = GetGrantResponse(sql, address, grants, bkCloudId)
	if err != nil {
		return err
	}
	if len(*grants) == 0 {
		return fmt.Errorf("show grants in %s fail,query return nothing", userHost)
	}
	return nil
}

// GetGrantResponse 执行sql语句，获取结果
func GetGrantResponse(sql, address string, grants *[]string, bkCloudId int64) (error, bool) {
	hasValue := false
	queryRequest := QueryRequest{[]string{address}, []string{sql}, true, 60, bkCloudId}
	reps, err := OneAddressExecuteSql(queryRequest)
	if err != nil {
		return fmt.Errorf("execute (%s) fail, error:%s", sql, err.Error()), hasValue
	}

	if len(reps.CmdResults[0].TableData) > 0 {
		for _, item := range reps.CmdResults[0].TableData {
			for _, grant := range item {
				if grant != nil {
					*grants = append(*grants, grant.(string))
				} else {
					return fmt.Errorf("execute (%s), content of return is null", sql), hasValue
				}
			}
		}
	} else {
		return nil, hasValue
	}
	hasValue = true
	return nil, hasValue
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
	var mysql5Tomysql8, mysql80Tomysql57, mysql57Tomysql56 bool
	// mysql8.0克隆到mysql5.7。后面有新版本比如验证mysql8.1，就把8000改为8001

	if instanceType == machineTypeBackend || instanceType == machineTypeSingle ||
		instanceType == machineTypeRemote {
		if MySQLVersionParse(sourceVersion, "")/1000 == 8000 && MySQLVersionParse(targetVersion, "")/1000 == 5007 {
			mysql80Tomysql57 = true
		} else if MySQLVersionParse(sourceVersion, "")/1000 == 5007 && MySQLVersionParse(targetVersion, "")/1000 == 5006 {
			mysql57Tomysql56 = true
		} else if MySQLVersionParse(sourceVersion, "")/1000 < 8000 && MySQLVersionParse(targetVersion, "")/1000 >= 8000 {
			mysql5Tomysql8 = true
		}
	}

	wg := sync.WaitGroup{}
	errorChan := make(chan error, 1)
	finishChan := make(chan bool, 1)
	var userExcluded = []string{"ADMIN", "mysql.session", "mysql.sys", "mysql.infoschema"} // Delete system user
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
				if regexp.MustCompile(fmt.Sprintf(`'%s'`, user)).MatchString(row.UserHost) {
					return
				}
			}
			reg := regexp.MustCompile(fmt.Sprintf(`'%s'`, targetIp)) // delete local ip user
			if reg.MatchString(row.UserHost) {
				return
			}
			reg = regexp.MustCompile(fmt.Sprintf(`'%s'`, sourceIp)) // change source ip user to local ip user
			if reg.MatchString(row.UserHost) {
				row.UserHost = reg.ReplaceAllString(row.UserHost, fmt.Sprintf(`%s`, targetIp))
				var tmp []string
				for _, str := range row.Grants {
					tmp = append(tmp, reg.ReplaceAllString(str, fmt.Sprintf(`%s`, targetIp)))
				}
				row.Grants = tmp
			}
			errInner := DiffVersionConvert(&row.Grants, mysql80Tomysql57, mysql57Tomysql56, mysql5Tomysql8)
			if errInner != nil {
				errorChan <- errInner
				return
			}
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
func DiffVersionConvert(grants *[]string, mysql80Tomysql57, mysql57Tomysql56, mysql5Tomysql8 bool) error {
	var err error
	var tmp []string
	regForCreateUser := regexp.MustCompile(
		`(?i)^\s*CREATE USER `,
	) // CREATE USER变为CREATE USER IF NOT EXISTS
	regForPasswordExpired := regexp.MustCompile(
		`(?i)\s*REQUIRE NONE PASSWORD EXPIRE DEFAULT ACCOUNT UNLOCK`,
	) // 5.7->5.6去掉

	switch {
	case mysql80Tomysql57:
		err = PrivMysql80ToMysql57(grants)
		if err != nil {
			return err
		}
	case mysql57Tomysql56:
		for _, str := range *grants {
			if regForPasswordExpired.MatchString(str) {
				str = regForPasswordExpired.ReplaceAllString(str, ``)
			}
			tmp = append(tmp, str)
		}
		*grants = tmp
	case mysql5Tomysql8:
		err = PrivMysql5ToMysql8(grants)
		if err != nil {
			return err
		}
	default:
		for _, str := range *grants {
			if regForCreateUser.MatchString(str) {
				str = regForCreateUser.ReplaceAllString(str, `CREATE USER /*!50706 IF NOT EXISTS */ `)
			}
			tmp = append(tmp, str)
		}
		*grants = tmp
	}
	return nil
}

// PrivMysql5ToMysql8 Mysql5授权语句向Mysql8兼容
func PrivMysql5ToMysql8(grants *[]string) error {
	var tmp []string
	regForCreateUser := regexp.MustCompile(
		`(?i)^\s*CREATE USER `,
	) // CREATE USER变为CREATE USER IF NOT EXISTS
	regForPlainText := regexp.MustCompile(`(?i)\s+IDENTIFIED\s+BY\s+`)

	for _, item := range *grants {
		if regForCreateUser.MatchString(item) {
			item = regForCreateUser.ReplaceAllString(item, `CREATE USER /*!50706 IF NOT EXISTS */ `)
		}
		if regForPlainText.MatchString(item) {
			sqlParser := parser.New()
			stmtNodes, warns, err := sqlParser.Parse(item, "", "")
			if err != nil {
				return fmt.Errorf("parse sql failed, sql:%s, error:%s", item, err.Error())
			}
			if len(warns) > 0 {
				slog.Warn("some warnings happend", warns)
			}
			for _, stmtNode := range stmtNodes {
				v := visitor{}
				stmtNode.Accept(&v)
				if !v.legal {
					return fmt.Errorf("parse pass,but sql format error,sql:%s", item)
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
	*grants = tmp
	return nil
}

// PrivMysql80ToMysql57 Mysql8.0授权语句向Mysql5.7兼容
func PrivMysql80ToMysql57(grants *[]string) error {
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
	regForCreateUser := regexp.MustCompile(
		`(?i)^\s*CREATE USER `,
	) // CREATE USER变为CREATE USER IF NOT EXISTS
	regForPasswordPlugin := regexp.MustCompile(
		`'caching_sha2_password'`,
	) // 排除8.0使用caching_sha2_password作为密码验证方式

	for _, item := range *grants {
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
			break
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
			return fmt.Errorf("using caching_sha2_password, sql: %s", item)
		}
		if regForCreateUser.MatchString(item) {
			item = regForCreateUser.ReplaceAllString(item, `CREATE USER /*!50706 IF NOT EXISTS */ `)
		}
		tmp = append(tmp, item)
	}
	*grants = tmp
	return nil
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
	// Err 错误信息列表
	type Err struct {
		mu   sync.RWMutex
		errs []string
	}
	var errMsg Err
	wg := sync.WaitGroup{}
	tokenBucket := make(chan int, 10)

	for _, row := range userGrants {
		wg.Add(1)
		tokenBucket <- 0
		go func(row UserGrant) {
			defer func() {
				<-tokenBucket
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
	close(tokenBucket)

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

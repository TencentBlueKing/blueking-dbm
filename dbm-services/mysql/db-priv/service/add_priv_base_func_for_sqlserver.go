package service

import (
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	errors2 "errors"
	"fmt"
	"log/slog"
	"strings"

	"github.com/jinzhu/gorm"
)

// 获取DB名称, sqlserver专属
func GetDBSForSqlserver(address string, bkCloudId int64, dbInclude string) ([]string, error) {
	var realDBS []string
	var err error
	queryPwdSQL := fmt.Sprintf(
		`SELECT name FROM MASTER.SYS.DATABASES WHERE DATABASE_ID > 4 AND NAME <> '%s' AND NAME LIKE '%s' 
		AND IS_READ_ONLY = 0 
		AND IS_DISTRIBUTOR = 0 
		AND STATE = 0 
		`,
		sqlserverSysDB,
		dbInclude,
	)
	var queryRequest = QueryRequest{[]string{address}, []string{queryPwdSQL}, false, 60, bkCloudId}

	result, err := OneAddressExecuteSqlserverSql(queryRequest)
	if err != nil {
		return nil, err
	}
	for _, row := range result.CmdResults[0].TableData {
		realDBS = append(realDBS, row["name"].(string))
	}
	return realDBS, nil
}

// 判断login是否存在，sqlserver专属
func IsExistLogin(address string, bkCloudId int64, login string, sid string) (bool, error) {
	var err error

	queryPwdSQL := fmt.Sprintf(
		`SELECT CONVERT(NVARCHAR(MAX), sid, 1) as sid_hex, 
		name FROM master.sys.sql_logins where name = '%s';`,
		login,
	)
	var queryRequest = QueryRequest{[]string{address}, []string{queryPwdSQL}, false, 60, bkCloudId}

	result, err := OneAddressExecuteSqlserverSql(queryRequest)
	if err != nil {
		return false, err
	}
	if len(result.CmdResults[0].TableData) == 0 {
		// 表示账号不存在
		return false, nil
	}
	sidHex, ok := result.CmdResults[0].TableData[0]["sid_hex"].(string)
	if !ok {
		// handle the error
		return false, fmt.Errorf("sid_hex is not a string")
	}
	if !strings.EqualFold(sidHex, sid) {
		// 表示login存在, 但是sid对不上
		return false, fmt.Errorf(
			"the login [%s] exists but the sid is not enough:[%s]:[%s]",
			login, sid, sidHex,
		)
	}
	// 表示存在
	slog.Info(fmt.Sprintf("the login [%s] exist in instance [%s] ", login, address))
	return true, nil
}

// GenerateSqlserverSQL 生成sqlserver授权语句
func GenerateSqlserverSQL(account TbAccounts, rules []TbAccountRules, address string, bkCloudId int64, role string) ([]string, error) {
	// 授权语句
	// CREATE LOGIN xxx WITH PASSWORD=N'xxx', DEFAULT_DATABASE=[MASTER],SID='xxx',CHECK_POLICY=OFF;
	// use xxx
	// ALTER AUTHORIZATION ON SCHEMA::db_owner TO dbo
	// CREATE USER xxx FOR LOGIN xxx WITH DEFAULT_SCHEMA=[dbo]
	// EXEC SP_ADDROLEMEMBER N'xxx', N'xxx';
	var realDBS []string
	var sqls []string
	var err error
	var psw string
	var realPsw []byte
	pswMap := make(map[string]string)
	// 查询login账号是否存在
	check, err := IsExistLogin(address, bkCloudId, account.User, account.Sid)
	if err != nil {
		slog.Error("msg", "IsExistLogin error", err)
		return nil, fmt.Errorf("IsExistLogin error: %s", err.Error())
	}
	if !check {
		// 如果存在不用拼接create login
		// 密码解密
		err = json.Unmarshal([]byte(account.Psw), &pswMap)
		if err != nil {
			return nil, fmt.Errorf("trans json error: [%s]", err)
		}

		bytes, err := hex.DecodeString(pswMap["sm4"])
		if err != nil {
			slog.Error("msg", "get hex decode error", err)
			return nil, fmt.Errorf("get hex decode error: %s", err.Error())
		}
		psw, err = SM4Decrypt(string(bytes))
		if err != nil {
			slog.Error("SM4Decrypt", "error", err)
			return nil, fmt.Errorf("SM4Decrypt error: %s", err.Error())
		}
		// 解密后再用base64解开明文
		realPsw, err = base64.StdEncoding.DecodeString(psw)
		if err != nil {
			slog.Error("msg", "get base64 decode error", err)
			return nil, fmt.Errorf("get base64 decode error: %s", err.Error())
		}
		sqls = append(sqls,
			fmt.Sprintf("CREATE LOGIN %s WITH PASSWORD=N'%s', DEFAULT_DATABASE=[MASTER],SID=%s,CHECK_POLICY=OFF;",
				account.User,
				string(realPsw),
				account.Sid,
			),
		)
	}

	if role == backendMaster || role == orphan {
		// master/orphan角色生成create user 语句
		for _, rule := range rules {
			// 远程实例获取DB
			if realDBS, err = GetDBSForSqlserver(address, bkCloudId, rule.Dbname); err != nil {
				return nil, err
			}
			// 拼接db级别的授权语句
			for _, dbName := range realDBS {
				sqls = append(sqls, fmt.Sprintf(`USE [%s]
	ALTER AUTHORIZATION ON SCHEMA::db_owner TO dbo;
	IF EXISTS (SELECT 1 FROM [%s].sys.database_principals WHERE name = N'%s') 
	BEGIN 
		EXEC [%s].dbo.sp_change_users_login 'AUTO_FIX','%s'
	END
   	ELSE
   	BEGIN
   		CREATE USER [%s] FOR LOGIN [%s];
   	END
	`,
					dbName, dbName, account.User, dbName, account.User, account.User, account.User,
				))
				sqls = append(sqls, fmt.Sprintf("USE [%s]", dbName))
				for _, p := range strings.Split(rule.Priv, ",") {
					sqls = append(sqls, fmt.Sprintf("EXEC SP_ADDROLEMEMBER N'%s', N'%s';", p, account.User))
				}

			}
		}
	}

	return sqls, nil
}

// ImportSqlserverPrivilege 生成 sqlserver 授权语句，并执行授权语句
func ImportSqlserverPrivilege(account TbAccounts, rules []TbAccountRules, bkCloudId int64, storage []Storage) error {
	var backendSQL []string
	var err error
	for _, s := range storage {
		var address string = fmt.Sprintf("%s:%d", s.IP, s.Port)
		if backendSQL, err = GenerateSqlserverSQL(account, rules, address, bkCloudId, s.InstanceRole); err != nil {
			return err
		}
		if len(backendSQL) == 0 && s.InstanceRole == backendSlave {
			// slave节点有可能不需要执行授权SQL，所以返回正常
			slog.Info(
				fmt.Sprintf("[%s] no grant sql execute in slave instance [%s]", account.User, address),
			)
			return nil
		}
		var queryRequest = QueryRequest{[]string{address}, backendSQL, false, 60, bkCloudId}
		_, err = OneAddressExecuteSqlserverSql(queryRequest)
		if err != nil {
			// 屏蔽报错出现的密码
			newStr := RemovePasswordPrintForSqlserver(err.Error())
			slog.Error("ImportSqlserverPrivilege failed", slog.String("err", newStr))
			return err
		}
	}

	return nil
}

// SaveAutoGRant 保存授权配置到实例
func SaveAutoGRant(account TbAccounts, rules []TbAccountRules, bkCloudId int64, storage []Storage) error {
	tableName := "[Monitor].[dbo].[AUTO_GRANT]"
	var sqls []string
	var addresses []string
	for _, rule := range rules {
		for _, p := range strings.Split(rule.Priv, ",") {
			sqls = append(
				sqls,
				fmt.Sprintf("use Monitor; delete from %s where [ACCOUNT] = '%s' and [GRANT_DB] = '%s' and [GRANT_TYPE] = '%s';",
					tableName, account.User, rule.Dbname, p),
				fmt.Sprintf("use Monitor; insert into %s values('%s','%s','%s',getdate());",
					tableName, account.User, rule.Dbname, p),
			)
		}
	}
	for _, s := range storage {
		addresses = append(addresses, fmt.Sprintf("%s:%d", s.IP, s.Port))
	}
	var queryRequest = QueryRequest{addresses, sqls, false, 60, bkCloudId}
	_, err := OneAddressExecuteSqlserverSql(queryRequest)
	if err != nil {
		slog.Error("SaveAutoGRant failed", slog.String("err", err.Error()))
		return err
	}
	return nil
}

// 获取sqlserver账号对象
func GetAccount(bkBizId int64, user string) (TbAccounts, error) {
	var account TbAccounts
	err := DB.Self.Table("tb_accounts").Where(&TbAccounts{BkBizId: bkBizId, ClusterType: "sqlserver", User: user}).
		Take(&account).Error
	if errors2.Is(err, gorm.ErrRecordNotFound) {
		return account, fmt.Errorf("账号%s不存在", user)
	} else if err != nil {
		return account, err
	} else if account.Sid == "" {
		return account, fmt.Errorf("账号%s的Sid为空,练习系统管理员", user)
	}
	return account, nil
}

// 获取sqlserver的master/orphan 节点
// 如果节点的状态非running,则报错
func GetInstance(cluster Instance) (Storage, []Storage, error) {
	var master Storage
	var slaves []Storage
	for _, s := range cluster.Storages {
		if s.Status != running {
			return master, nil,
				fmt.Errorf(
					"[%s]master-instance-status is not running, check[%s]",
					cluster.ImmuteDomain,
					s.Status,
				)
		}

		if s.InstanceRole == backendMaster || s.InstanceRole == orphan {
			// 传入到master
			master = s
		} else {
			// 传入到slaves
			slaves = append(slaves, s)
		}
	}
	return master, slaves, nil
}

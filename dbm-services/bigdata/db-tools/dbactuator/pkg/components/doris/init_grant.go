package doris

import (
	"database/sql"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/dorisutil"
	"dbm-services/common/go-pubpkg/logger"
	"fmt"
)

// InitGrantParams TODO
type InitGrantParams struct {
	Host          string `json:"host" validate:"required,ip" ` // 本机IP
	QueryPort     int    `json:"query_port" validate:"required"`
	UserName      string `json:"username" `
	Password      string `json:"password" `
	RootPassword  string `json:"root_password" `
	AdminPassword string `json:"admin_password" `
}

// InitGrantService TODO
type InitGrantService struct {
	GeneralParam    *components.GeneralParam
	Params          *InitGrantParams
	RollBackContext rollback.RollBackObjects
}

// InitGrant TODO
func (i *InitGrantService) InitGrant() (err error) {
	return i.InitGrantTxn()
}

// AlterRootPassword 修改root用户 的密码
func (i *InitGrantService) AlterRootPassword() (err error) {

	// mysql客户端实现
	db, err := sql.Open("mysql", fmt.Sprintf("%s:%s@tcp(%s:%d)/%s",
		RootUser, "", i.Params.Host, i.Params.QueryPort, ""))

	if err != nil {
		logger.Error("connect doris database failed, %v", err)
		return err
	}
	defer func(db *sql.DB) {
		err := db.Close()
		if err != nil {
			return
		}
	}(db)
	pwd := dorisutil.DefaultString(i.Params.RootPassword, i.Params.Password)
	// Doris 不支持 prepared statement 传参 ALTER USER，对密码做单引号/反斜杠转义防注入
	alterSql := fmt.Sprintf("ALTER USER root@'%%' IDENTIFIED BY '%s';", dorisutil.EscapeSQLString(pwd))
	// 执行SQL
	if _, err = db.Exec(alterSql); err != nil {
		return err
	}
	return
}

// AlterAdminPassword 修改admin用户的密码
func (i *InitGrantService) AlterAdminPassword() (err error) {
	// 兼容 dbm-ui未发版
	rootPwd := dorisutil.DefaultString(i.Params.RootPassword, i.Params.Password)

	// mysql客户端实现
	db, err := sql.Open("mysql", fmt.Sprintf("%s:%s@tcp(%s:%d)/%s",
		RootUser, rootPwd, i.Params.Host, i.Params.QueryPort, ""))

	if err != nil {
		logger.Error("connect doris database failed, %v", err)
		return err
	}
	defer func(db *sql.DB) {
		err := db.Close()
		if err != nil {
			return
		}
	}(db)
	pwd := dorisutil.DefaultString(i.Params.AdminPassword, i.Params.Password)
	// Doris 不支持 prepared statement 传参 ALTER USER，对密码做单引号/反斜杠转义防注入
	alterSql := fmt.Sprintf("ALTER USER `admin`@'%%' IDENTIFIED BY '%s';", dorisutil.EscapeSQLString(pwd))
	// 执行SQL
	if _, err = db.Exec(alterSql); err != nil {
		return err
	}
	return
}

// CreateCustomUser 创建自定义 用户
func (i *InitGrantService) CreateCustomUser() (err error) {
	// 兼容 dbm-ui未发版
	pwd := dorisutil.DefaultString(i.Params.RootPassword, i.Params.Password)
	// mysql客户端实现
	db, err := sql.Open("mysql", fmt.Sprintf("%s:%s@tcp(%s:%d)/%s",
		RootUser, pwd, i.Params.Host, i.Params.QueryPort, ""))

	if err != nil {
		logger.Error("connect doris database failed, %v", err)
		return err
	}
	defer func(db *sql.DB) {
		err := db.Close()
		if err != nil {
			return
		}
	}(db)

	// Doris 不支持 prepared statement 传参 CREATE USER/GRANT，且用户名会以裸标识符出现在 SQL 中，
	// 必须先做标识符合法性校验（防注入 + 防语法破坏），密码走字符串字面值转义。
	if err = dorisutil.ValidateSQLIdentifier(i.Params.UserName); err != nil {
		logger.Error("invalid custom username, %v", err)
		return err
	}
	// 自定义用户仅需 admin 角色：NODE_PRIV 非必要，用户属性（resource_tags.location 等）由运行时配置管理下发
	alterSql := fmt.Sprintf("CREATE USER %s@'%%' IDENTIFIED BY '%s'; grant 'admin' to '%s'@'%%' ;",
		i.Params.UserName, dorisutil.EscapeSQLString(i.Params.Password), i.Params.UserName)
	// 执行SQL
	if _, err = db.Exec(alterSql); err != nil {
		return err
	}
	return
}

// InitGrantTxn Doris集群账号初始化
//
// TODO: 函数名保留了 "Txn" 后缀，但 Doris 当前并不支持账号/DDL 类语句的多语句事务：
//
//	ALTER USER / CREATE USER / GRANT 在 Doris 侧执行时即已原子提交，此处的 tx.Begin/Commit
//	仅在 MySQL 协议层建立会话状态，Rollback 实际无法回滚前置步骤已产生的账号变更。
//	因此本函数并不能保证跨步骤的原子性，任一步失败时前面已执行的账号操作不会被撤销。
//	另外，本函数首步会修改 root 密码，后续步骤若失败，简单重试未必能自动收敛；
//	如需真正支持重试/补偿，需要显式记录阶段状态，或调整执行顺序与重连凭据策略。
//	等 Doris 支持 DDL 事务，或这里补齐显式补偿后，再回来去掉这条 TODO。
func (i *InitGrantService) InitGrantTxn() (err error) {
	// Doris 不支持 prepared statement 传参 DDL，用户名会以裸标识符落到 SQL，必须先校验；
	// 密码通过 EscapeSQLString 做字面值转义，避免包含 ' 或 \ 时破坏 SQL。
	if err = dorisutil.ValidateSQLIdentifier(i.Params.UserName); err != nil {
		logger.Error("invalid custom username, %v", err)
		return err
	}

	// mysql客户端实现
	db, err := sql.Open("mysql", fmt.Sprintf("%s:%s@tcp(%s:%d)/%s",
		RootUser, "", i.Params.Host, i.Params.QueryPort, ""))

	if err != nil {
		logger.Error("connect doris database failed, %v", err)
		return err
	}
	defer func(db *sql.DB) {
		err := db.Close()
		if err != nil {
			return
		}
	}(db)
	// 开启事务（见函数注释 TODO：实际不具备跨步骤原子性，仅走 MySQL 协议层）
	tx, err := db.Begin()
	if err != nil {
		logger.Error("begin transaction failed, %v", err)
		return err
	}
	rootPwd := dorisutil.DefaultString(i.Params.RootPassword, i.Params.Password)
	alterRootSql := fmt.Sprintf("ALTER USER root@'%%' IDENTIFIED BY '%s';",
		dorisutil.EscapeSQLString(rootPwd))
	// 1. 修改root用户密码
	if _, err = tx.Exec(alterRootSql); err != nil {
		if rbErr := tx.Rollback(); rbErr != nil {
			logger.Warn("rollback failed after altering root password, %v", rbErr)
		}
		logger.Error("alter root password failed, %v", err)
		return err
	}
	adminPwd := dorisutil.DefaultString(i.Params.AdminPassword, i.Params.Password)

	alterAdminSql := fmt.Sprintf("ALTER USER `admin`@'%%' IDENTIFIED BY '%s';",
		dorisutil.EscapeSQLString(adminPwd))
	// 2. 修改admin用户密码
	if _, err = tx.Exec(alterAdminSql); err != nil {
		if rbErr := tx.Rollback(); rbErr != nil {
			logger.Warn("rollback failed after altering admin password, %v", rbErr)
		}
		logger.Error("alter admin password failed, %v", err)
		return err
	}
	// 3. 创建自定义用户
	createUserSql := fmt.Sprintf("CREATE USER %s@'%%' IDENTIFIED BY '%s'",
		i.Params.UserName, dorisutil.EscapeSQLString(i.Params.Password))
	if _, err = tx.Exec(createUserSql); err != nil {
		if rbErr := tx.Rollback(); rbErr != nil {
			logger.Warn("rollback failed after creating custom user, %v", rbErr)
		}
		logger.Error("create custom user failed, %v", err)
		return err
	}
	// 4. 给自定义用户授予 admin 角色
	grantAdminSql := fmt.Sprintf("GRANT 'admin' TO '%s'@'%%';", i.Params.UserName)
	if _, err = tx.Exec(grantAdminSql); err != nil {
		if rbErr := tx.Rollback(); rbErr != nil {
			logger.Warn("rollback failed after granting admin role, %v", rbErr)
		}
		logger.Error("grant admin role to custom user failed, %v", err)
		return err
	}
	// 提交事务
	if err = tx.Commit(); err != nil {
		logger.Error("commit transaction failed, %v", err)
		return err
	}
	return nil
}

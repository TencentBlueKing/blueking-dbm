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
		"root", "", i.Params.Host, i.Params.QueryPort, ""))

	if err != nil {
		logger.Error("连接Doris数据库失败，%v", err)
		return err
	}
	defer func(db *sql.DB) {
		err := db.Close()
		if err != nil {
			return
		}
	}(db)
	pwd := dorisutil.DefaultString(i.Params.RootPassword, i.Params.Password)
	alterSql := fmt.Sprintf("ALTER USER root@'%%' IDENTIFIED BY '%s';", pwd)
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
		"root", rootPwd, i.Params.Host, i.Params.QueryPort, ""))

	if err != nil {
		logger.Error("连接Doris数据库失败，%v", err)
		return err
	}
	defer func(db *sql.DB) {
		err := db.Close()
		if err != nil {
			return
		}
	}(db)
	pwd := dorisutil.DefaultString(i.Params.AdminPassword, i.Params.Password)
	alterSql := fmt.Sprintf("ALTER USER `admin`@'%%' IDENTIFIED BY '%s';", pwd)
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
		"root", pwd, i.Params.Host, i.Params.QueryPort, ""))

	if err != nil {
		logger.Error("连接Doris数据库失败，%v", err)
		return err
	}
	defer func(db *sql.DB) {
		err := db.Close()
		if err != nil {
			return
		}
	}(db)

	alterSql := fmt.Sprintf("CREATE USER %s@'%%' IDENTIFIED BY '%s'; grant 'admin' to '%s'@'%%' ;",
		i.Params.UserName, i.Params.Password, i.Params.UserName)
	// 执行SQL
	if _, err = db.Exec(alterSql); err != nil {
		return err
	}
	alterSql = fmt.Sprintf("grant NODE_PRIV on *.*.* to '%s'@'%%' ;", i.Params.UserName)
	// 执行SQL
	if _, err = db.Exec(alterSql); err != nil {
		return err
	}
	// 用户变量 UserProperty调整
	// 不管是否存在温/冷 节点，均对自定义用户配置
	setPropSql := fmt.Sprintf("set property for '%s' 'resource_tags.location' = 'cold,default';", i.Params.UserName)
	if _, err = db.Exec(setPropSql); err != nil {
		return err
	}
	return
}

// InitGrantTxn Doris集群账号初始化事务，保证原子性
func (i *InitGrantService) InitGrantTxn() (err error) {
	// mysql客户端实现
	db, err := sql.Open("mysql", fmt.Sprintf("%s:%s@tcp(%s:%d)/%s",
		"root", "", i.Params.Host, i.Params.QueryPort, ""))

	if err != nil {
		logger.Error("连接Doris数据库失败，%v", err)
		return err
	}
	defer func(db *sql.DB) {
		err := db.Close()
		if err != nil {
			return
		}
	}(db)
	// 开启事务
	tx, err := db.Begin()
	if err != nil {
		logger.Fatal("开启事务失败: %v", err)
	}
	rootPwd := dorisutil.DefaultString(i.Params.RootPassword, i.Params.Password)
	alterRootSql := fmt.Sprintf("ALTER USER root@'%%' IDENTIFIED BY '%s';", rootPwd)
	// 1. 修改root用户密码
	_, err = tx.Exec(alterRootSql)
	if err != nil {
		tx.Rollback()
		logger.Fatal("修改root用户密码失败: %v", err)
	}
	adminPwd := dorisutil.DefaultString(i.Params.AdminPassword, i.Params.Password)

	alterAdminSql := fmt.Sprintf("ALTER USER `admin`@'%%' IDENTIFIED BY '%s';", adminPwd)
	// 2. 修改admin用户密码
	_, err = tx.Exec(alterAdminSql)
	if err != nil {
		tx.Rollback()
		logger.Fatal("修改admin用户密码失败: %v", err)
	}
	// 3. 创建自定义用户
	createUserSql := fmt.Sprintf("CREATE USER %s@'%%' IDENTIFIED BY '%s'",
		i.Params.UserName, i.Params.Password)
	_, err = tx.Exec(createUserSql)
	if err != nil {
		tx.Rollback()
		logger.Fatal("创建自定义用户失败: %v", err)
	}
	// 提交事务
	if err := tx.Commit(); err != nil {
		logger.Fatal("提交事务失败: %v", err)
	}
	return nil
}

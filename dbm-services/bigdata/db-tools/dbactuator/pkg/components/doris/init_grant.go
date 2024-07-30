package doris

import (
	"database/sql"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/rollback"
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
	// TODO  change root and admin password
	if err := i.AlterRootPassword(); err != nil {
		logger.Error("修改root用户密码失败:%s", err.Error())
		return err
	}
	if err = i.AlterAdminPassword(); err != nil {
		logger.Error("修改admin用户密码失败:%s", err.Error())

		return err
	}
	if err = i.CreateCustomUser(); err != nil {
		logger.Error("创建业务用户失败:%s", err.Error())
		return err
	}
	return nil
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

	alterSql := fmt.Sprintf("ALTER USER root@'%%' IDENTIFIED BY '%s';", i.Params.Password)
	// 执行SQL
	if _, err = db.Exec(alterSql); err != nil {
		return err
	}
	return
}

// AlterAdminPassword 修改admin用户的密码
func (i *InitGrantService) AlterAdminPassword() (err error) {

	// mysql客户端实现
	db, err := sql.Open("mysql", fmt.Sprintf("%s:%s@tcp(%s:%d)/%s",
		"root", i.Params.Password, i.Params.Host, i.Params.QueryPort, ""))

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

	alterSql := fmt.Sprintf("ALTER USER `admin`@'%%' IDENTIFIED BY '%s';", i.Params.Password)
	// 执行SQL
	if _, err = db.Exec(alterSql); err != nil {
		return err
	}
	return
}

// CreateCustomUser 创建自定义 用户
func (i *InitGrantService) CreateCustomUser() (err error) {

	// mysql客户端实现
	db, err := sql.Open("mysql", fmt.Sprintf("%s:%s@tcp(%s:%d)/%s",
		"root", i.Params.Password, i.Params.Host, i.Params.QueryPort, ""))

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
	return
}

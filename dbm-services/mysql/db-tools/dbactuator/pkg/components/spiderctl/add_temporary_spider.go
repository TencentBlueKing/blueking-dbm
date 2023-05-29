// Package spiderctl TODO
package spiderctl

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"fmt"
)

// AddTmpSpiderComp 分为通用参数和行为专用参数
type AddTmpSpiderComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       *AddTmpSpiderParam       `json:"extend"`
	InitCtx
}

// AddTmpSpiderParam 具体执行时所需要的参数
type AddTmpSpiderParam struct {
	Host            string     `json:"host" validate:"required,ip"`
	Port            int        `json:"port" validate:"required,lt=65536,gte=3306"`
	SpiderInstances []Instance `json:"spider_instance" validate:"required"`
}

// Example TODO
func (a *AddTmpSpiderComp) Example() interface{} {
	comp := AddTmpSpiderComp{}
	return comp
}

// Init 初始化数据库连接，之后用于客户端登录执行添加新的路由信息
func (a *AddTmpSpiderComp) Init() (err error) {
	a.dbConn, err = native.InsObject{
		Host: a.Params.Host,
		Port: a.Params.Port,
		User: a.GeneralParam.RuntimeAccountParam.AdminUser,
		Pwd:  a.GeneralParam.RuntimeAccountParam.AdminPwd,
	}.Conn()
	if err != nil {
		logger.Error("Connect %d failed:%s", a.Params.Port, err.Error())
		return err
	}
	return nil
}

// AddTmpSpider TODO
func (a *AddTmpSpiderComp) AddTmpSpider() (err error) {
	var execSQLs []string
	tdbctlUser := a.GeneralParam.RuntimeAccountParam.TdbctlUser
	tdbctlPwd := a.GeneralParam.RuntimeAccountParam.TdbctlPwd
	for _, inst := range a.Params.SpiderInstances {
		execSQLs = append(execSQLs, fmt.Sprintf(
			"tdbctl create node wrapper 'SPIDER' options(user '%s', password '%s', host '%s', port %d) with database;",
			tdbctlUser, tdbctlPwd, inst.Host, inst.Port,
		),
		)
	}
	execSQLs = append(execSQLs, "tdbctl flush routing;")
	_, err = a.dbConn.ExecMore(execSQLs)
	if err != nil {
		logger.Error("tdbctl create node failed:[%s]", err.Error())
		return err
	}
	return nil
}

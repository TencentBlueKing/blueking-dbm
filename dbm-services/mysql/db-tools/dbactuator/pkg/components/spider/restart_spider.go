// Package spider TODO
package spider

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/computil"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
)

// RestartSpiderComp restart spider comp
type RestartSpiderComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       *RestartSpiderParam      `json:"extend"`
}

// RestartSpiderParam  restart spider param
type RestartSpiderParam struct {
	Host    string `json:"host"  validate:"required,ip"`
	Port    int    `json:"port"  validate:"required,gte=3306"`
	myCnf   *util.CnfFile
	instObj *native.InsObject
}

// Example subcommand example input
func (d *RestartSpiderComp) Example() interface{} {
	comp := RestartSpiderComp{
		Params: &RestartSpiderParam{
			Host: "1.1.1.1",
			Port: 0,
		},
	}
	return comp
}

// Init prepare run env
func (u *RestartSpiderComp) Init() (err error) {
	f := util.GetMyCnfFileName(u.Params.Port)
	u.Params.myCnf = &util.CnfFile{
		FileName: f,
	}
	if err := u.Params.myCnf.Load(); err != nil {
		return err
	}
	dbSocket, err := u.Params.myCnf.GetMySQLSocket()
	if err != nil {
		return err
	}
	u.Params.instObj = &native.InsObject{
		Host:   u.Params.Host,
		Port:   u.Params.Port,
		User:   u.GeneralParam.RuntimeAccountParam.AdminUser,
		Pwd:    u.GeneralParam.RuntimeAccountParam.AdminPwd,
		Socket: dbSocket,
	}
	return
}

// PreCheck pre check
func (u *RestartSpiderComp) PreCheck() (err error) {
	_, err = u.Params.instObj.ConnSpiderAdmin()
	if err != nil {
		logger.Error(fmt.Sprintf("连接Admin失败。%s", err.Error()))
		return err
	}
	return
}

// RestartSpider restart
func (u *RestartSpiderComp) RestartSpider() (err error) {
	err = computil.RestartMysqlInstanceNormal(*u.Params.instObj)
	if err != nil {
		return err
	}
	return nil
}

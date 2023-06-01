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

// RestartSpiderComp TODO
type RestartSpiderComp struct {
	GeneralParam *components.GeneralParam `json:"general"`
	Params       *RestartSpiderParam      `json:"extend"`
}

// RestartSpiderParam TODO
type RestartSpiderParam struct {
	Host    string `json:"host"  validate:"required,ip"`
	Port    int    `json:"port"  validate:"required,gte=3306"`
	myCnf   *util.CnfFile
	instObj *native.InsObject
}

// Example TODO
func (d *RestartSpiderComp) Example() interface{} {
	comp := RestartSpiderComp{
		Params: &RestartSpiderParam{
			Host: "1.1.1.1",
			Port: 0,
		},
	}
	return comp
}

// Init TODO
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

// PreCheck TODO
func (u *RestartSpiderComp) PreCheck() (err error) {
	_, err = u.Params.instObj.ConnSpiderAdmin()
	if err != nil {
		logger.Error(fmt.Sprintf("连接Admin失败。%s", err.Error()))
		return err
	}
	return
}

// RestartSpider TODO
func (u *RestartSpiderComp) RestartSpider() (err error) {
	err = computil.RestartMysqlInstanceNormal(*u.Params.instObj)
	if err != nil {
		return err
	}
	return nil
}

// Package mysql_proxy TODO
/*
 * @Description: 克隆proxy的user权限
 */
package mysql_proxy

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
)

// CloneProxyUserComp TODO
type CloneProxyUserComp struct {
	GeneralParam         *components.GeneralParam
	Params               *CloneProxyUserParam
	SoueceProxyAdminConn *native.ProxyAdminDbWork
	TargetProxyAdminConn *native.ProxyAdminDbWork
}

// CloneProxyUserParam TODO
// payload param
type CloneProxyUserParam struct {
	SourceProxyHost string `json:"source_proxy_host"  validate:"required,ip"`
	SourceProxyPort int    `json:"source_proxy_port" validate:"required,gte=3306"`
	TargetProxyHost string `json:"target_proxy_host"  validate:"required,ip"`
	TargetProxyPort int    `json:"target_proxy_port" validate:"required,gte=3306"`
}

// Init TODO
func (p *CloneProxyUserComp) Init() (err error) {
	p.SoueceProxyAdminConn, err = native.InsObject{
		Host: p.Params.SourceProxyHost,
		Port: p.Params.SourceProxyPort,
		User: p.GeneralParam.RuntimeAccountParam.ProxyAdminUser,
		Pwd:  p.GeneralParam.RuntimeAccountParam.ProxyAdminPwd,
	}.ConnProxyAdmin()
	if err != nil {
		logger.Error("connect source proxy admin port(ori:%s) failed,%s", p.Params.SourceProxyPort, err.Error())
		return err
	}
	p.TargetProxyAdminConn, err = native.InsObject{
		Host: p.Params.TargetProxyHost,
		Port: p.Params.TargetProxyPort,
		User: p.GeneralParam.RuntimeAccountParam.ProxyAdminUser,
		Pwd:  p.GeneralParam.RuntimeAccountParam.ProxyAdminPwd,
	}.ConnProxyAdmin()
	if err != nil {
		logger.Error("connect target proxy admin port(ori:%s) failed,%s", p.Params.TargetProxyPort, err.Error())
		return err
	}
	return
}

// CloneProxyUser 在源proxy克隆user白名单给目标proxy
func (p *CloneProxyUserComp) CloneProxyUser() (err error) {
	err = p.SoueceProxyAdminConn.CloneProxyUser(p.TargetProxyAdminConn)
	if err != nil {
		logger.Error(
			"clone proxy users to instance(%s#%s) failed,%s", p.Params.TargetProxyHost, p.Params.TargetProxyPort,
			err.Error(),
		)
		return err
	}
	return
}

// Example TODO
func (p *CloneProxyUserComp) Example() interface{} {
	comp := CloneProxyUserComp{
		Params: &CloneProxyUserParam{
			SourceProxyHost: "1.1.1.1",
			SourceProxyPort: 10000,
			TargetProxyHost: "2.2.2.2",
			TargetProxyPort: 10000,
		},
	}
	return comp
}

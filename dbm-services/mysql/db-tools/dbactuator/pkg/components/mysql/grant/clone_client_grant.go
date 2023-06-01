// Package grant TODO
/*
 * @Description:
 */
package grant

import (
	"fmt"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/mysqlutil"
)

// CloneClentGRantComp TODO
type CloneClentGRantComp struct {
	GeneralParam  *components.GeneralParam
	Params        *CloneClentGRantParam
	db            *native.DbWorker // 本地db链接
	masterVersion string           // 主库的数据库版本
}

// CloneClentGRantParam 给mysql 克隆客户端的权限
type CloneClentGRantParam struct {
	// 当前实例的主机地址
	Host string `json:"host" validate:"required,ip"`
	// 当前实例的端口
	Port int `json:"port" validate:"required,lt=65536,gte=3306"`
	// 作为模板权限的客户端ip
	TemplateClientHost string `json:"template_client_host" validate:"required,ip"`
	// 目标的客户端ip
	TargetClientHost string `json:"target_client_host" validate:"required,ip"`
	//	是否回收旧客户端账号
	IsDrop bool `json:"is_drop"`
	//	当is_drop为true才读取该变量，默认传1.1.1.1即可，表示需要删除对应权限的客户端host
	OriginClientHost string `json:"origin_client_host" validate:"required,ip"`
}

// Init TODO
func (g *CloneClentGRantComp) Init() (err error) {
	dbwork, err := native.InsObject{
		Host: g.Params.Host,
		Port: g.Params.Port,
		User: g.GeneralParam.RuntimeAccountParam.AdminUser,
		Pwd:  g.GeneralParam.RuntimeAccountParam.AdminPwd,
	}.Conn()
	if err != nil {
		logger.Error("connect %s:%d failed,err:%s", g.Params.Host, g.Params.Port, err.Error())
		return
	}

	g.db = dbwork
	if g.masterVersion, err = g.db.SelectVersion(); err != nil {
		logger.Error("select Version error:%s", err)
	}
	logger.Info("Version is %s", g.masterVersion)
	return
}

// ReadTemplateClientPriv TODO
func (g *CloneClentGRantComp) ReadTemplateClientPriv() (grantSql []string, err error) {
	var rows []string

	selectSql := fmt.Sprintf(
		"select concat( user,'@',host) as userhost from mysql.user where host = '%s'",
		g.Params.TemplateClientHost,
	)
	created := false

	if mysqlutil.MySQLVersionParse(g.masterVersion) > 5007000 {
		created = true
	}

	// 先查询TemplateClientHost 对应在mysql实例上的user，host
	err = g.db.Queryx(&rows, selectSql)
	if err != nil {
		logger.Error("select error:%s", err)
		return
	}

	// 读取模板的授权
	for _, row := range rows {
		var grants []string
		if grants, err = g.db.ShowPrivForUser(created, row); err != nil {
			logger.Error("show priv sql for user error :%s", err)
			return
		}
		grantSql = append(grantSql, grants...)
	}
	return
}

// SpliceDropUserSQL TODO
func (g *CloneClentGRantComp) SpliceDropUserSQL(clientHost string) (dropUserSqls []string, err error) {
	var rows []string

	selectSql := fmt.Sprintf("select concat( user,'@',host) as userhost from mysql.user where host = '%s'", clientHost)

	// 先查询clientHost对应在mysql实例上的user，host
	err = g.db.Queryx(&rows, selectSql)
	if err != nil {
		logger.Error("select error:%s", err)
		return
	}

	// 拼接drop user SQL 模板
	for _, row := range rows {
		sql := fmt.Sprintf("drop user %s", row)
		dropUserSqls = append(dropUserSqls, sql)
	}
	return
}

// CloneTargetClientPriv 读取模板客户端的权限内容，生成对应目标客户端授权语句执行
func (g *CloneClentGRantComp) CloneTargetClientPriv() (err error) {
	var targetGrantSqls []string
	var templateGrantSqls []string
	if templateGrantSqls, err = g.ReadTemplateClientPriv(); err != nil {
		return
	}

	if len(templateGrantSqls) == 0 {
		logger.Info("related priv is empty.")
		return nil
	}

	for _, grant := range templateGrantSqls {
		tmpGrant := strings.Replace(grant, g.Params.TemplateClientHost, g.Params.TargetClientHost, -1)
		targetGrantSqls = append(targetGrantSqls, tmpGrant)
	}

	if _, err = g.db.ExecMore(targetGrantSqls); err != nil {
		logger.Error("Clone permission failed: %s", err)
		return
	}

	return
}

// DropOriginClientPriv 回收旧客户端用户和权限
func (g *CloneClentGRantComp) DropOriginClientPriv() (err error) {
	var dropUserSqls []string
	if !g.Params.IsDrop {
		// 传入参数不执行删除用户的步骤，则提前退出
		logger.Info("IsDrop is %s, skip", g.Params.IsDrop)
		return nil
	}

	if dropUserSqls, err = g.SpliceDropUserSQL(g.Params.OriginClientHost); err != nil {
		return
	}

	if len(dropUserSqls) == 0 {
		logger.Info("drop priv is empty.")
		return nil
	}

	if _, err = g.db.ExecMore(dropUserSqls); err != nil {
		logger.Error("drop user failed: %s", err)
		return
	}
	return
}

// ClearTargetClientPriv 清理目标客户端残留的用户和权限
func (g *CloneClentGRantComp) ClearTargetClientPriv() (err error) {
	var dropUserSqls []string
	if dropUserSqls, err = g.SpliceDropUserSQL(g.Params.TargetClientHost); err != nil {
		return
	}

	if len(dropUserSqls) == 0 {
		logger.Info("clear priv is empty.")
		return nil
	}

	if _, err = g.db.ExecMore(dropUserSqls); err != nil {
		logger.Error("clear user failed: %s", err)
		return
	}
	return
}

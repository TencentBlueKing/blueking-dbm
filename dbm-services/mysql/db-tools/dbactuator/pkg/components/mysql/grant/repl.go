// Package grant TODO
/*
 * @Description:
 */
package grant

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"encoding/json"
	"fmt"
)

// GrantReplComp TODO
type GrantReplComp struct {
	GeneralParam  *components.GeneralParam `json:"general"`
	Params        *GrantReplParam          `json:"extend"`
	Db            *native.DbWorker         // 本地db链接
	masterVersion string                   // 主库的数据库版本
}

// GrantReplParam 对Master 增加repl 账户
type GrantReplParam struct {
	Host      string   `json:"host"`       // 当前实例的主机地址
	Port      int      `json:"port"`       // 当前实例的端口
	ReplHosts []string `json:"repl_hosts"` // slave host
}

// Example TODO
func (g *GrantReplComp) Example() interface{} {
	comp := GrantReplComp{
		Params: &GrantReplParam{
			Host:      "1.1.1.1",
			Port:      3306,
			ReplHosts: []string{"2.2.2.2", "3.3.3.3"},
		},
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: common.MySQLAdminReplExample,
			},
		},
	}
	return comp
}

// Init TODO
func (g *GrantReplComp) Init() (err error) {
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
	g.Db = dbwork
	ver, err := g.Db.SelectVersion()
	if err != nil {
		return
	}
	g.masterVersion = ver
	logger.Info("Version is %s", g.masterVersion)
	return
}

// GrantRepl TODO
func (g *GrantReplComp) GrantRepl() (err error) {
	repl_user := g.GeneralParam.RuntimeAccountParam.ReplUser
	repl_pwd := g.GeneralParam.RuntimeAccountParam.ReplPwd
	var execSQLs []string
	for _, replHost := range g.Params.ReplHosts {
		execSQLs = append(
			execSQLs,
			fmt.Sprintf(
				"CREATE USER /*!50706 IF NOT EXISTS */ `%s`@`%s` IDENTIFIED BY '%s';",
				repl_user, replHost, repl_pwd,
			),
		)
		execSQLs = append(
			execSQLs,
			fmt.Sprintf("GRANT REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO `%s`@`%s`;", repl_user, replHost),
		)
	}
	if _, err := g.Db.ExecMore(execSQLs); err != nil {
		logger.Error("create repl user failed:[%s]", err.Error())
		return err
	}

	// sqls := []string{
	// 	fmt.Sprintf("CREATE USER /*!50706 IF NOT EXISTS */ `%s`@`%s` IDENTIFIED BY '%s';",
	// 		repl_user, g.Params.ReplHost, repl_pwd),
	// 	fmt.Sprintf("GRANT REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO `%s`@`%s`;", repl_user, g.Params.ReplHost)}
	// for _, lqs := range sqls {
	// 	if _, err := g.Db.Exec(lqs); err != nil {
	// 		return err
	// 	}
	// }
	return nil
}

// GetBinPosition TODO
func (g *GrantReplComp) GetBinPosition() (binPosition string, err error) {
	resp, err := g.Db.ShowMasterStatus()
	if err != nil {
		return "", err
	}
	b, err := json.Marshal(resp)
	if err != nil {
		return "", err
	}
	// fmt.Printf("<ctx>%s</ctx>", string(b))
	return string(b), nil
}

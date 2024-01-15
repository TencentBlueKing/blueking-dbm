// Package grant TODO
/*
 * @Description:
 */
package grant

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/common"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
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
			ReplHosts: []string{"2.2.2.2", "127.0.0.3"},
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

// GrantRepl grant user if not exists
// 幂等
func (g *GrantReplComp) GrantRepl() (err error) {
	replUser := g.GeneralParam.RuntimeAccountParam.ReplUser
	replPass := g.GeneralParam.RuntimeAccountParam.ReplPwd

	// 因为可能需要 set session 会话，需要使用独立的connection
	ctx := context.Background()
	conn, err := g.Db.Db.Conn(ctx)
	if err != nil {
		return errors.WithMessage(err, "get connection")
	}
	// 增加对tdbctl授权的判断，初始化session设置tc_admin=0
	if strings.Contains(g.masterVersion, "tdbctl") {
		if _, err = conn.ExecContext(ctx, "set tc_admin = 0;"); err != nil {
			return err
		}
	}

	for _, replHost := range g.Params.ReplHosts {
		if err = native.DropUserIfExists(replUser, replHost, conn); err != nil {
			return err
		}
		if err = native.CreateUserIfNotExists(replUser, replHost, replPass, conn); err != nil {
			return err
		}
		grantSQL := fmt.Sprintf("GRANT REPLICATION SLAVE, REPLICATION CLIENT ON *.* TO `%s`@`%s`;", replUser, replHost)
		if _, err = conn.ExecContext(ctx, grantSQL); err != nil {
			return err
		}
	}
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

package native

import (
	"fmt"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/core/cst"
)

const (
	// ProxyMinVersion TODO
	ProxyMinVersion = "mysql-proxy 0.8.2.4"
)

// ProxyAdminDbWork TODO
type ProxyAdminDbWork struct {
	DbWorker
}

// ConnProxyAdmin TODO
// Connect Proxy Admin Port By Tcp/Ip
func (o InsObject) ConnProxyAdmin() (*ProxyAdminDbWork, error) {
	dbwork, err := NewDbWorkerNoPing(o.proxyAdminTcpDsn(), o.User, o.Pwd)
	return &ProxyAdminDbWork{DbWorker: *dbwork}, err
}

// SelectBackend 查询ProxyBackends
func (h *ProxyAdminDbWork) SelectBackend() (backends ProxyAdminBackend, err error) {
	err = h.Queryxs(&backends, "SELECT * FROM backends;")
	return
}

// SelectProxyVersion  查询Proxy Version
//
//	@receiver h
//	@return backends
//	@return err
func (h *ProxyAdminDbWork) SelectProxyVersion() (version string, err error) {
	err = h.Queryxs(&version, "select version();")
	return
}

// AddUser TODO
// refresh_users('user@host','flag')
// Add Proxy Users
func (h *ProxyAdminDbWork) AddUser(userDsn string) (err error) {
	_, err = h.Exec(fmt.Sprintf("refresh_users('%s','+')", userDsn))
	return
}

// RefreshBackends TODO
// refresh_backends('host:port',flag)
// Add Proxy Users
func (h *ProxyAdminDbWork) RefreshBackends(host string, port int) (err error) {
	refreshSQL := fmt.Sprintf("refresh_backends('%s:%d',1)", host, port)
	logger.Info(refreshSQL)
	_, err = h.Exec(refreshSQL)
	return
}

// CheckProxyInUse 检查Proxy backend 是否等于 1.1.1.1:3306 还有是否存在连接的Client
//
//	@receiver h
//	@return inuse
//	@return err
func (h *ProxyAdminDbWork) CheckProxyInUse() (inuse bool, err error) {
	backend, err := h.SelectBackend()
	if err != nil {
		return false, err
	}
	if strings.Compare(backend.Address, cst.DefaultBackend) != 0 && backend.ConnectedClients > 0 {
		return true, nil
	}
	return false, nil
}

// CloneProxyUser 定义proxy克隆白名单的功能
func (h *ProxyAdminDbWork) CloneProxyUser(target_db *ProxyAdminDbWork) (err error) {
	// refresh_users('a@b,c@d,e@f','+');
	users, err := h.GetAllProxyUsers()
	if err != nil {
		return err
	}

	userStr := strings.Join(users, ",")
	refreshSQL := fmt.Sprintf("refresh_users('%s','+');", userStr)

	_, err = target_db.Exec(refreshSQL)
	if err != nil {
		return err
	}
	return nil
}

// GetAllProxyUsers 定义查询proxy 所有user 功能
func (h *ProxyAdminDbWork) GetAllProxyUsers() (users []string, err error) {
	var sql = "select * from users;"

	rows, err := h.Query(sql)
	if err != nil {
		return nil, err
	}
	for _, row := range rows {
		users = append(users, row["user@ip"].(string))
	}
	return
}

// CheckBackend TODO
func (h *ProxyAdminDbWork) CheckBackend(host string, port int) (err error) {
	c, err := h.SelectBackend()
	if err != nil {
		return err
	}
	if strings.Compare(c.Address, fmt.Sprintf("%s:%d", host, port)) != 0 {
		return fmt.Errorf(
			"change backend get an error, expected %s but is %s",
			fmt.Sprintf("%s:%d", host, port),
			c.Address,
		)
	}
	return err
}

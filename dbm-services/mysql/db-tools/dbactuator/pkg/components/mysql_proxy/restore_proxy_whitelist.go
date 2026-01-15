// Package mysql_proxy TODO
/*
 * @Description: 从 Master 恢复 Proxy 白名单
 * 用于 Proxy 救援流程，优先从 Master 的 infodba_schema.proxy_user_list 表获取白名单；
 * 若备份为空，则回退到 mysql.user 推算 user@host 作为白名单，并应用到新 Proxy。
 */
package mysql_proxy

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
)

// RestoreProxyWhitelistComp 从 Master 恢复 Proxy 白名单组件
type RestoreProxyWhitelistComp struct {
	GeneralParam         *components.GeneralParam
	Params               *RestoreProxyWhitelistParam
	MasterConn           *native.DbWorker
	TargetProxyAdminConn *native.ProxyAdminDbWork
}

// RestoreProxyWhitelistParam 从 Master 恢复白名单的参数
type RestoreProxyWhitelistParam struct {
	MasterHost      string `json:"master_host" validate:"required,ip"`
	MasterPort      int    `json:"master_port" validate:"required,gte=3306"`
	TargetProxyHost string `json:"target_proxy_host" validate:"required,ip"`
	TargetProxyPort int    `json:"target_proxy_port" validate:"required,gte=3306"`
}

// ProxyWhitelistRecord 白名单记录结构（与 infodba_schema.proxy_user_list 一致）
type ProxyWhitelistRecord struct {
	ProxyIP  string `db:"proxy_ip"`
	Username string `db:"username"`
	Host     string `db:"host"`
}

// Init 初始化连接
func (r *RestoreProxyWhitelistComp) Init() (err error) {
	// 连接 Master 实例
	r.MasterConn, err = native.InsObject{
		Host: r.Params.MasterHost,
		Port: r.Params.MasterPort,
		User: r.GeneralParam.RuntimeAccountParam.AdminUser,
		Pwd:  r.GeneralParam.RuntimeAccountParam.AdminPwd,
	}.Conn()
	if err != nil {
		logger.Error("connect master instance(%s:%d) failed: %s", r.Params.MasterHost, r.Params.MasterPort, err.Error())
		return err
	}
	logger.Info("successfully connected to master instance(%s:%d)", r.Params.MasterHost, r.Params.MasterPort)

	// 连接目标 Proxy 的 admin 端口
	r.TargetProxyAdminConn, err = native.InsObject{
		Host: r.Params.TargetProxyHost,
		Port: r.Params.TargetProxyPort,
		User: r.GeneralParam.RuntimeAccountParam.ProxyAdminUser,
		Pwd:  r.GeneralParam.RuntimeAccountParam.ProxyAdminPwd,
	}.ConnProxyAdmin()
	if err != nil {
		logger.Error("connect target proxy admin port(%s:%d) failed: %s",
			r.Params.TargetProxyHost, r.Params.TargetProxyPort, err.Error())
		return err
	}
	logger.Info("successfully connected to target proxy admin port(%s:%d)",
		r.Params.TargetProxyHost, r.Params.TargetProxyPort)

	return nil
}

// RestoreWhitelistFromMaster 从 Master 恢复白名单到目标 Proxy
// 优先使用 infodba_schema.proxy_user_list 备份；当备份为空时，自动回退到 mysql.user 推算
func (r *RestoreProxyWhitelistComp) RestoreWhitelistFromMaster() (err error) {
	logger.Info("start to restore proxy whitelist from master to target proxy")

	source := "proxy_user_list"
	whitelistRecords, err := r.fetchWhitelistFromProxyUserList()
	if err != nil {
		logger.Error("failed to fetch whitelist from proxy_user_list: %s", err.Error())
		return err
	}

	if len(whitelistRecords) == 0 {
		logger.Warn("proxy_user_list empty on master(%s:%d), fallback to mysql.user",
			r.Params.MasterHost, r.Params.MasterPort)

		whitelistRecords, err = r.fetchWhitelistFromMysqlUser()
		if err != nil {
			logger.Error("failed to fetch whitelist from mysql.user: %s", err.Error())
			return err
		}

		if len(whitelistRecords) == 0 {
			return fmt.Errorf("no whitelist records found in proxy_user_list nor mysql.user")
		}

		source = "mysql.user"
		logger.Warn("proxy_user_list empty, fallback to mysql.user from master(%s:%d), found %d records",
			r.Params.MasterHost, r.Params.MasterPort, len(whitelistRecords))
	} else {
		logger.Info("found %d whitelist records from master proxy_user_list", len(whitelistRecords))
	}

	err = r.applyWhitelistToProxy(whitelistRecords)
	if err != nil {
		logger.Error("failed to apply whitelist to proxy: %s", err.Error())
		return err
	}

	logger.Info("successfully restored whitelist to proxy(%s:%d) from source [%s], total %d records",
		r.Params.TargetProxyHost, r.Params.TargetProxyPort, source, len(whitelistRecords))

	return nil
}

// fetchWhitelistFromProxyUserList 从 Master 的 infodba_schema.proxy_user_list 表获取白名单（主数据源）
func (r *RestoreProxyWhitelistComp) fetchWhitelistFromProxyUserList() (records []ProxyWhitelistRecord, err error) {
	sql := "SELECT proxy_ip, username, host FROM infodba_schema.proxy_user_list WHERE proxy_ip = ?"
	logger.Info("query whitelist from master proxy_user_list: %s, proxy_ip=%s", sql, r.Params.TargetProxyHost)

	err = r.MasterConn.Queryx(&records, sql, r.Params.TargetProxyHost)
	if err != nil {
		logger.Error("query whitelist from proxy_user_list failed: %s", err.Error())
		return nil, err
	}

	return records, nil
}

// fetchWhitelistFromMysqlUser 当 proxy_user_list 备份为空时的回退：基于 mysql.user 推算白名单
// 排除策略：
//   - 排除 MySQL 系统账号：mysql.session / mysql.sys / mysql.infoschema / mysql
//   - 排除本机类 host：localhost / 127.0.0.1
//
// 注意：由于 mysql.user 的 host 在 TenDBHA 架构下通常是 Proxy 的 IP，并非客户端视角的真实来源，
// 因此这里将白名单 host 统一改写为 '%'，即按用户粒度放通（user@%），并通过 DISTINCT 对用户去重。
func (r *RestoreProxyWhitelistComp) fetchWhitelistFromMysqlUser() (records []ProxyWhitelistRecord, err error) {
	sql := `SELECT DISTINCT user AS username FROM mysql.user ` +
		`WHERE user NOT IN ('mysql.session','mysql.sys','mysql.infoschema','mysql') ` +
		`AND host NOT IN ('localhost','127.0.0.1')`
	logger.Info("query whitelist from master mysql.user: %s", sql)

	type userRow struct {
		Username string `db:"username"`
	}
	var rows []userRow
	err = r.MasterConn.Queryx(&rows, sql)
	if err != nil {
		logger.Error("query whitelist from mysql.user failed: %s", err.Error())
		return nil, err
	}

	records = make([]ProxyWhitelistRecord, 0, len(rows))
	for _, row := range rows {
		records = append(records, ProxyWhitelistRecord{
			ProxyIP:  r.Params.TargetProxyHost,
			Username: row.Username,
			Host:     "%",
		})
	}
	return records, nil
}

// applyWhitelistToProxy 将白名单应用到目标 Proxy
func (r *RestoreProxyWhitelistComp) applyWhitelistToProxy(records []ProxyWhitelistRecord) (err error) {
	// 构建白名单用户列表
	var users []string
	for _, record := range records {
		// 与 mysql-monitor proxyuserlist 备份一致：username@host（host 为客户端来源）
		userAtHost := fmt.Sprintf("%s@%s", record.Username, record.Host)
		users = append(users, userAtHost)
	}

	if len(users) == 0 {
		return fmt.Errorf("no valid users to restore")
	}

	logger.Info("restoring %d users to proxy: %v", len(users), users)

	// 使用 refresh_users 命令添加白名单
	// refresh_users('user1@ip1,user2@ip2,...','+')
	for i := 0; i < len(users); i += 100 {
		// 分批处理，每次最多 100 个用户
		end := i + 100
		if end > len(users) {
			end = len(users)
		}

		batch := users[i:end]
		userList := ""
		for idx, user := range batch {
			if idx > 0 {
				userList += ","
			}
			userList += user
		}

		refreshSQL := fmt.Sprintf("refresh_users('%s','+');", userList)
		logger.Info("executing refresh_users command (batch %d/%d): users count=%d",
			i/100+1, (len(users)+99)/100, len(batch))

		_, err = r.TargetProxyAdminConn.Exec(refreshSQL)
		if err != nil {
			logger.Error("refresh_users failed for batch %d: %s", i/100+1, err.Error())
			return err
		}

		logger.Info("successfully restored batch %d/%d", i/100+1, (len(users)+99)/100)
	}

	return nil
}

// Example 示例
func (r *RestoreProxyWhitelistComp) Example() interface{} {
	comp := RestoreProxyWhitelistComp{
		Params: &RestoreProxyWhitelistParam{
			MasterHost:      "127.0.0.1",
			MasterPort:      20000,
			TargetProxyHost: "127.0.0.2",
			TargetProxyPort: 10000,
		},
	}
	return comp
}

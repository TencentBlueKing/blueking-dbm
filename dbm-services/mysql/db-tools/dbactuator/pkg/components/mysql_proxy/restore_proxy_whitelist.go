// Package mysql_proxy TODO
/*
 * @Description: 从 Master 恢复 Proxy 白名单
 * 用于 Proxy 救援流程，优先从 Master 的 infodba_schema.proxy_user_list 表获取白名单；
 * 若备份为空，则回退到 mysql.user 推算 user@% 作为白名单。
 * 支持在单次任务中同时恢复多个目标 Proxy 实例。
 */
package mysql_proxy

import (
	"fmt"
	"strings"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
)

// TargetProxyInstance 单个目标 Proxy 实例
type TargetProxyInstance struct {
	Host string `json:"host" validate:"required,ip"`
	Port int    `json:"port" validate:"required,gte=3306"`
}

// RestoreProxyWhitelistComp 从 Master 恢复 Proxy 白名单组件
type RestoreProxyWhitelistComp struct {
	GeneralParam *components.GeneralParam
	Params       *RestoreProxyWhitelistParam
	MasterConn   *native.DbWorker
}

// RestoreProxyWhitelistParam 从 Master 恢复白名单的参数
type RestoreProxyWhitelistParam struct {
	MasterHost    string                `json:"master_host" validate:"required,ip"`
	MasterPort    int                   `json:"master_port" validate:"required,gte=3306"`
	TargetProxies []TargetProxyInstance `json:"target_proxies" validate:"required,min=1,dive"`
}

// ProxyWhitelistRecord 白名单记录结构（与 infodba_schema.proxy_user_list 一致）
type ProxyWhitelistRecord struct {
	ProxyIP  string `db:"proxy_ip"`
	Username string `db:"username"`
	Host     string `db:"host"`
}

// Init 初始化 Master 连接（Proxy admin 连接在 apply 阶段按需建立/释放）
func (r *RestoreProxyWhitelistComp) Init() (err error) {
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
	return nil
}

// RestoreWhitelistFromMaster 从 Master 批量恢复白名单到所有目标 Proxy
// 主源一次性按 proxy_ip IN (...) 拉取 infodba_schema.proxy_user_list；
// 对主源为空的 Proxy 自动回退到 mysql.user 推算的 user@%（回退结果懒加载、多 proxy 共享）。
func (r *RestoreProxyWhitelistComp) RestoreWhitelistFromMaster() (err error) {
	logger.Info("start to restore proxy whitelist from master(%s:%d) to %d target proxies",
		r.Params.MasterHost, r.Params.MasterPort, len(r.Params.TargetProxies))

	proxyIPs := make([]string, 0, len(r.Params.TargetProxies))
	for _, p := range r.Params.TargetProxies {
		proxyIPs = append(proxyIPs, p.Host)
	}

	primaryByProxy, err := r.fetchWhitelistFromProxyUserList(proxyIPs)
	if err != nil {
		logger.Error("failed to fetch whitelist from proxy_user_list: %s", err.Error())
		return err
	}

	var fallbackTemplate []ProxyWhitelistRecord
	fallbackFetched := false

	for _, proxy := range r.Params.TargetProxies {
		records := primaryByProxy[proxy.Host]
		source := "proxy_user_list"

		if len(records) == 0 {
			if !fallbackFetched {
				logger.Warn("proxy_user_list empty for proxy %s, fallback to mysql.user from master(%s:%d)",
					proxy.Host, r.Params.MasterHost, r.Params.MasterPort)
				fallbackTemplate, err = r.fetchWhitelistFromMysqlUser()
				if err != nil {
					logger.Error("failed to fetch whitelist from mysql.user: %s", err.Error())
					return err
				}
				fallbackFetched = true
			}

			if len(fallbackTemplate) == 0 {
				return fmt.Errorf("no whitelist records for proxy(%s:%d) in proxy_user_list nor mysql.user",
					proxy.Host, proxy.Port)
			}

			records = make([]ProxyWhitelistRecord, 0, len(fallbackTemplate))
			for _, rec := range fallbackTemplate {
				rec.ProxyIP = proxy.Host
				records = append(records, rec)
			}
			source = "mysql.user"
		}

		if err = r.applyWhitelistToOneProxy(proxy, records); err != nil {
			logger.Error("failed to apply whitelist to proxy(%s:%d): %s", proxy.Host, proxy.Port, err.Error())
			return err
		}
		logger.Info("successfully restored whitelist to proxy(%s:%d) from source [%s], total %d records",
			proxy.Host, proxy.Port, source, len(records))
	}

	logger.Info("all %d target proxies restored successfully", len(r.Params.TargetProxies))
	return nil
}

// fetchWhitelistFromProxyUserList 主数据源：一次性查询所有目标 proxy_ip 的白名单，按 proxy_ip 分组返回
func (r *RestoreProxyWhitelistComp) fetchWhitelistFromProxyUserList(
	proxyIPs []string,
) (map[string][]ProxyWhitelistRecord, error) {
	placeholders := make([]string, len(proxyIPs))
	args := make([]interface{}, len(proxyIPs))
	for i, ip := range proxyIPs {
		placeholders[i] = "?"
		args[i] = ip
	}
	sql := fmt.Sprintf(
		"SELECT proxy_ip, username, host FROM infodba_schema.proxy_user_list WHERE proxy_ip IN (%s)",
		strings.Join(placeholders, ","),
	)
	logger.Info("query whitelist from master proxy_user_list: %s, proxy_ips=%v", sql, proxyIPs)

	var records []ProxyWhitelistRecord
	if err := r.MasterConn.Queryx(&records, sql, args...); err != nil {
		logger.Error("query whitelist from proxy_user_list failed: %s", err.Error())
		return nil, err
	}

	result := make(map[string][]ProxyWhitelistRecord, len(proxyIPs))
	for _, rec := range records {
		result[rec.ProxyIP] = append(result[rec.ProxyIP], rec)
	}
	return result, nil
}

// fetchWhitelistFromMysqlUser 回退源：基于 mysql.user 推算白名单
// 排除策略：
//   - 排除 MySQL 系统账号：mysql.session / mysql.sys / mysql.infoschema / mysql
//   - 排除本机类 host：localhost / 127.0.0.1
//
// 注意：由于 mysql.user 的 host 在 TenDBHA 架构下通常是 Proxy 的 IP，并非客户端视角的真实来源，
// 因此这里将白名单 host 统一改写为 '%'，即按用户粒度放通（user@%），并通过 DISTINCT 对用户去重。
// 返回的模板记录 ProxyIP 为空，由调用方按目标 Proxy 补齐。
func (r *RestoreProxyWhitelistComp) fetchWhitelistFromMysqlUser() ([]ProxyWhitelistRecord, error) {
	sql := `SELECT DISTINCT user AS username FROM mysql.user ` +
		`WHERE user NOT IN ('mysql.session','mysql.sys','mysql.infoschema','mysql') ` +
		`AND host NOT IN ('localhost','127.0.0.1')`
	logger.Info("query whitelist from master mysql.user: %s", sql)

	type userRow struct {
		Username string `db:"username"`
	}
	var rows []userRow
	if err := r.MasterConn.Queryx(&rows, sql); err != nil {
		logger.Error("query whitelist from mysql.user failed: %s", err.Error())
		return nil, err
	}

	records := make([]ProxyWhitelistRecord, 0, len(rows))
	for _, row := range rows {
		records = append(records, ProxyWhitelistRecord{
			Username: row.Username,
			Host:     "%",
		})
	}
	return records, nil
}

// applyWhitelistToOneProxy 对单个目标 Proxy 建立 admin 连接、应用白名单、释放连接
func (r *RestoreProxyWhitelistComp) applyWhitelistToOneProxy(
	proxy TargetProxyInstance,
	records []ProxyWhitelistRecord,
) error {
	adminConn, err := native.InsObject{
		Host: proxy.Host,
		Port: proxy.Port,
		User: r.GeneralParam.RuntimeAccountParam.ProxyAdminUser,
		Pwd:  r.GeneralParam.RuntimeAccountParam.ProxyAdminPwd,
	}.ConnProxyAdmin()
	if err != nil {
		logger.Error("connect target proxy admin port(%s:%d) failed: %s", proxy.Host, proxy.Port, err.Error())
		return err
	}
	defer adminConn.Stop()
	logger.Info("successfully connected to target proxy admin port(%s:%d)", proxy.Host, proxy.Port)

	users := make([]string, 0, len(records))
	for _, record := range records {
		// 与 mysql-monitor proxyuserlist 备份一致：username@host（host 为客户端来源）
		users = append(users, fmt.Sprintf("%s@%s", record.Username, record.Host))
	}
	if len(users) == 0 {
		return fmt.Errorf("no valid users to restore for proxy(%s:%d)", proxy.Host, proxy.Port)
	}

	logger.Info("restoring %d users to proxy(%s:%d): %v", len(users), proxy.Host, proxy.Port, users)

	// 使用 refresh_users 命令添加白名单：refresh_users('user1@ip1,user2@ip2,...','+')
	// 分批处理，每次最多 100 个用户
	totalBatch := (len(users) + 99) / 100
	for i := 0; i < len(users); i += 100 {
		end := i + 100
		if end > len(users) {
			end = len(users)
		}
		batch := users[i:end]
		userList := strings.Join(batch, ",")

		refreshSQL := fmt.Sprintf("refresh_users('%s','+');", userList)
		batchNo := i/100 + 1
		logger.Info("executing refresh_users on proxy(%s:%d) batch %d/%d: users count=%d",
			proxy.Host, proxy.Port, batchNo, totalBatch, len(batch))

		if _, err = adminConn.Exec(refreshSQL); err != nil {
			logger.Error("refresh_users failed on proxy(%s:%d) batch %d: %s",
				proxy.Host, proxy.Port, batchNo, err.Error())
			return err
		}
		logger.Info("successfully restored batch %d/%d on proxy(%s:%d)",
			batchNo, totalBatch, proxy.Host, proxy.Port)
	}
	return nil
}

// Example 示例
func (r *RestoreProxyWhitelistComp) Example() interface{} {
	comp := RestoreProxyWhitelistComp{
		Params: &RestoreProxyWhitelistParam{
			MasterHost: "127.0.0.1",
			MasterPort: 20000,
			TargetProxies: []TargetProxyInstance{
				{Host: "127.0.0.2", Port: 10000},
				{Host: "127.0.0.3", Port: 10000},
			},
		},
	}
	return comp
}

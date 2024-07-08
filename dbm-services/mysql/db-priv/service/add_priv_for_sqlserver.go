package service

import (
	"fmt"
	"log/slog"
	"strings"
	"time"

	"dbm-services/mysql/priv-service/util"

	"github.com/spf13/viper"
)

// AddPriv 使用账号规则，新增权限
func (m *PrivTaskPara) AddPrivForSqlserver(jsonPara string) error {
	slog.Info(fmt.Sprintf("PrivTaskPara:%v", m))
	var account TbAccounts
	var rules []TbAccountRules
	var err error

	// 为了避免通过api未调用AddPrivDryRun，直接调用AddPriv，未做检查参数，所以AddPriv先调用AddPrivDryRun
	if _, outerErr := m.AddPrivDryRun(); outerErr != nil {
		return outerErr
	}
	AddPrivLog(PrivLog{BkBizId: m.BkBizId, Operator: m.Operator, Para: jsonPara, Time: time.Now()})

	// 获取添加账号信息
	if account, err = GetAccount(m.BkBizId, m.User); err != nil {
		return err
	}
	// 获取账号对应的规则信息
	for _, rule := range m.AccoutRules {
		_, accountRule, err := GetAccountRuleInfo(m.BkBizId, m.ClusterType, m.User, rule.Dbname)
		if err != nil {
			return err
		}
		rules = append(rules, accountRule)
	}

	client := util.NewClientByHosts(viper.GetString("dbmeta"))
	for _, dns := range m.TargetInstances {
		// 获取集群相关信息
		dns = strings.Trim(strings.TrimSpace(dns), ".")
		cluster, err := GetCluster(client, m.ClusterType, Domain{EntryName: dns})
		if err != nil {
			return err
		}
		// 执行授权sql
		if err := ImportSqlserverPrivilege(
			account,
			rules,
			cluster.BkCloudId,
			cluster.Storages,
		); err != nil {
			return err
		}
		// 导入授权配置到实例
		if err := SaveAutoGRant(
			account,
			rules,
			cluster.BkCloudId,
			cluster.Storages,
		); err != nil {
			return err
		}

	}
	return nil
}

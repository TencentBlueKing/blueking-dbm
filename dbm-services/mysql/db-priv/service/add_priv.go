package service

import (
	"fmt"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/errno"
)

// AddPrivDryRun 使用账号规则，新增权限预检查
func (m *PrivTaskPara) AddPrivDryRun() (PrivTaskPara, error) {
	var taskPara PrivTaskPara
	var errMsg []string
	var errMsgTemp []string

	if m.BkBizId == 0 {
		return taskPara, errno.BkBizIdIsEmpty
	}
	if m.ClusterType == "" {
		return taskPara, errno.ClusterTypeIsEmpty
	}

	taskPara.SourceIPs, errMsgTemp = DeduplicationIP(m.SourceIPs)
	if len(errMsgTemp) > 0 {
		errMsg = append(errMsg, errMsgTemp...)
	}

	taskPara.TargetInstances, errMsgTemp = DeduplicationTargetInstance(m.TargetInstances, m.ClusterType)
	if len(errMsgTemp) > 0 {
		errMsg = append(errMsg, errMsgTemp...)
	}

	for _, rule := range m.AccoutRules {
		_, _, err := GetAccountRuleInfo(m.BkBizId, m.ClusterType, m.User, rule.Dbname)
		if err != nil {
			errMsg = append(errMsg, err.Error())
		}
	}

	if len(errMsg) > 0 {
		return taskPara, errno.GrantPrivilegesParameterCheckFail.Add("\n" + strings.Join(errMsg, "\n"))
	}

	taskPara.BkBizId = m.BkBizId
	taskPara.Operator = m.Operator
	taskPara.AccoutRules = m.AccoutRules
	taskPara.ClusterType = m.ClusterType
	taskPara.User = m.User

	return taskPara, nil
}

// AddPriv 使用账号规则，新增权限
func (m *PrivTaskPara) AddPriv(jsonPara string, ticket string) error {
	if m.ClusterType == sqlserverHA || m.ClusterType == sqlserverSingle || m.ClusterType == sqlserver {
		// 走sqlserver授权逻辑
		return m.AddPrivForSqlserver(jsonPara)
	}

	return fmt.Errorf("use add priv v2 on mysql")
}

// AddPrivWithoutAccountRule 不使用账号规则模版，在mysql实例授权。此接口不被页面前端调用，为后台服务设计。不建议通过此接口授权。
func (m *AddPrivWithoutAccountRule) AddPrivWithoutAccountRule(jsonPara string, ticket string) error {
	var clusterType string
	psw, err := EncryptPswInDb(m.Psw)
	if err != nil {
		return err
	}
	ts := time.Now()
	tmpAccount := TbAccounts{0, 0, "", m.User, psw, "",
		ts, "", ts, ""}
	tmpAccountRule := TbAccountRules{0, 0, "", 0, m.Dbname, m.Priv,
		m.DmlDdlPriv, m.GlobalPriv, "", ts, "", ts}
	if m.BkCloudId == nil {
		return errno.CloudIdRequired
	}

	if m.Role == machineTypeSpider {
		clusterType = tendbcluster
	} else if m.Role == tdbctl {
		clusterType = tdbctl
	} else {
		clusterType = tendbsingle
	}
	err = ImportBackendPrivilege(tmpAccount, tmpAccountRule, m.Address, nil, m.Hosts,
		clusterType, false, *m.BkCloudId, true, false)
	if err != nil {
		return errno.GrantPrivilegesFail.Add(err.Error())
	}
	AddPrivLog(PrivLog{BkBizId: m.BkBizId, Ticket: ticket, Operator: m.Operator, Para: jsonPara, Time: time.Now()})
	return nil
}

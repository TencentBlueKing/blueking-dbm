package service

import (
	"errors"
	"fmt"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/errno"
)

// CloneInstancePrivDryRun 克隆实例权限预检查
func (m *CloneInstancePrivParaList) CloneInstancePrivDryRun() error {

	var errMsg []string
	var UniqMap = make(map[string]struct{})

	if m.BkBizId == 0 {
		return errno.BkBizIdIsEmpty
	}
	for index, slaveRecord := range m.CloneInstancePrivRecords {
		_, err := ValidateInstancePair(slaveRecord.Source, slaveRecord.Target)
		if err != nil {
			msg := fmt.Sprintf("line %d: input is invalid, reason: %s", index+1, err)
			errMsg = append(errMsg, msg)
		}
		tempStr := slaveRecord.String()
		if _, isExists := UniqMap[tempStr]; isExists == true {
			msg := fmt.Sprintf("line %d: line duplicate", index+1)
			errMsg = append(errMsg, msg)
			continue
		}
		UniqMap[tempStr] = struct{}{}
	}

	if len(errMsg) > 0 {
		return errno.ClonePrivilegesCheckFail.Add("\n" + strings.Join(errMsg, "\n"))
	}

	return nil
}

// CloneInstancePriv 克隆实例权限
func (m *CloneInstancePrivPara) CloneInstancePriv(jsonPara string, ticket string) error {

	AddPrivLog(PrivLog{BkBizId: m.BkBizId, Ticket: ticket, Operator: m.Operator, Para: jsonPara, Time: time.Now()})

	if m.BkBizId == 0 {
		return errno.BkBizIdIsEmpty
	}
	if m.BkCloudId == nil {
		return errno.CloudIdRequired
	}
	m.Source.Address = strings.TrimSpace(m.Source.Address)
	m.Target.Address = strings.TrimSpace(m.Target.Address)

	instanceType, errOuter := ValidateInstancePair(m.Source, m.Target)
	if errOuter != nil {
		return errno.ClonePrivilegesFail.Add("\n" + errOuter.Error())
	}

	// 此处单集群instanceType是single
	if instanceType == machineTypeSingle || instanceType == machineTypeBackend ||
		instanceType == machineTypeRemote || instanceType == machineTypeSpider {
		userGrants, err := GetRemotePrivilege(m.Source.Address, "", *m.BkCloudId, instanceType, "", false)
		if err != nil {
			return err
		} else if len(userGrants) == 0 {
			return errno.NoPrivilegesNothingToDo
		}
		userGrants, err = m.DealWithPrivileges(userGrants, instanceType)
		if err != nil {
			return err
		} else if len(userGrants) == 0 {
			return errno.NoPrivilegesNothingToDo
		}
		if instanceType != machineTypeSpider {
			err = CheckGrantInMySqlVersion(userGrants, m.Target.Address, *m.BkCloudId)
			if err != nil {
				return err
			}
		}
		err = ImportMysqlPrivileges(userGrants, m.Target.Address, *m.BkCloudId)
		if err != nil {
			return err
		}
	} else if instanceType == machineTypeProxy {
		var err error
		m.Source.Address, err = changeToProxyAdminPort(m.Source.Address)
		if err != nil {
			return errno.ClonePrivilegesFail.Add(err.Error())
		}
		m.Target.Address, err = changeToProxyAdminPort(m.Target.Address)
		if err != nil {
			return errno.ClonePrivilegesFail.Add(err.Error())
		}
		proxyUsers, err := GetProxyPrivilege(m.Source.Address, nil, *m.BkCloudId, "")
		if err != nil {
			return err
		} else if len(proxyUsers) == 0 {
			return errno.NoPrivilegesNothingToDo
		}

		var oneBuckUsers []string
		var errCollect error
		for _, u := range proxyUsers {
			oneBuckUsers = append(oneBuckUsers, u)
			if len(oneBuckUsers) >= 1000 {
				refreshSql := fmt.Sprintf(
					"refresh_users('%s', '+')",
					strings.Join(oneBuckUsers, ","),
				)

				err = ImportProxyPrivileges(
					[]string{refreshSql},
					m.Target.Address, *m.BkCloudId)
				if err != nil {
					errCollect = errors.Join(errCollect, err)
				}
				oneBuckUsers = []string{}
			}
		}
		refreshSql := fmt.Sprintf(
			"refresh_users('%s', '+')",
			strings.Join(oneBuckUsers, ","),
		)

		err = ImportProxyPrivileges([]string{refreshSql}, m.Target.Address, *m.BkCloudId)
		if err != nil {
			errCollect = errors.Join(errCollect, err)
		}

		if errCollect != nil {
			return errCollect
		}
	}
	return nil
}

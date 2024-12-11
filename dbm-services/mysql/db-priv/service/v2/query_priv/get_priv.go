// Package query_priv TODO
package query_priv

import (
	"fmt"
	"slices"
	"strings"

	"dbm-services/mysql/priv-service/service"
	v2 "dbm-services/mysql/priv-service/service/v2/internal"
)

// GetPriv TODO
// func (m *GetPrivPara) GetPriv() error {
// 	err := m.validate()
// 	if err != nil {
// 		return err
// 	}

// 	if len(m.Users) == 0 {
// 		return errno.ErrUserIsEmpty
// 	}
// 	userStr := strings.Join(m.Users, `','`)

// 	var errChan = make(chan error)
// 	var retChan = make(chan []string)

// 	go func() {
// 		wg := sync.WaitGroup{}

// 		for _, item := range m.ImmuteDomains {
// 			wg.Add(1)

// 			err := m.limiter.Wait(context.Background())
// 			if err != nil {
// 				errChan <- err
// 				wg.Done()
// 				return
// 			}

// 			go func(item string) {
// 				defer func() {
// 					wg.Done()
// 				}()

// 				domainInfo, err := service.GetCluster(*m.ClusterType, service.Domain{EntryName: item})
// 				if err != nil {
// 					errChan <- err
// 					return
// 				}

// 				switch domainInfo.ClusterType {
// 				case v2.ClusterTypeTenDBSingle:
// 					privsFromTenDBSingle(&domainInfo, m.Users, m.Ips, m.Dbs)
// 				case v2.ClusterTypeTenDBHA:
// 					privsFromTenDBHA(&domainInfo, m.Users, m.Ips, m.Dbs)
// 				case v2.ClusterTypeTenDBCluster:
// 				default:
// 					errChan <- fmt.Errorf("unknown cluster type: %s", domainInfo.ClusterType)
// 					return
// 				}
// 			}(item)
// 		}
// 	}()
// }

func privsFromTenDBSingle(domainInfo *service.Instance, users, clientIps, dbs []string) ([]service.GrantInfo, error) {
	backendAddr := fmt.Sprintf("%s:%d", domainInfo.Storages[0].IP, domainInfo.Storages[0].Port)

	userList, _, matchHosts, err := service.MysqlUserList(
		backendAddr,
		domainInfo.BkCloudId,
		clientIps,
		users,
		domainInfo.ImmuteDomain,
	)
	if err != nil {
		return nil, err
	}
	if len(matchHosts) == 0 {
		return nil, nil
	}

	userGrants, err := service.GetRemotePrivilege(
		backendAddr,
		matchHosts,
		domainInfo.BkCloudId,
		v2.MachineTypeBackend,
		strings.Join(users, `','`),
		true,
	)
	if err != nil {
		return nil, err
	}
	if len(userGrants) == 0 {
		return nil, nil
	}

	splitUserGrants := service.SplitGrantSql(userGrants, dbs, false)
	return service.CombineUserWithGrant(userList, splitUserGrants, false), nil
}

func privsFromTenDBHA(domainInfo *service.Instance, users, clientIps, dbs []string) ([]service.GrantInfo, error) {
	if domainInfo.EntryRole == v2.EntryRoleMasterEntry && !domainInfo.PaddingProxy {
		return privsFromTenDBHAMaster(domainInfo, users, clientIps, dbs)
	} else {
		return privsFromTenDBHASlave(domainInfo, users, clientIps, dbs)
	}
}

func privsFromTenDBHAMaster(domainInfo *service.Instance, users, clientIps, dbs []string) ([]service.GrantInfo, error) {
	idx := slices.IndexFunc(domainInfo.Storages, func(s service.Storage) bool {
		return s.InstanceRole == v2.InstanceRoleBackendMaster
	})
	backendAddr := fmt.Sprintf("%s:%d", domainInfo.Storages[idx].IP, domainInfo.Storages[idx].Port)

	userGrants, err := service.GetRemotePrivilege(
		backendAddr,
		domainInfo.Proxies[0].IP,
		domainInfo.BkCloudId,
		v2.MachineTypeBackend,
		strings.Join(users, `','`),
		true,
	)
	if err != nil {
		return nil, err
	}

	splitUserGrants := service.SplitGrantSql(userGrants, dbs, true)

	proxyAddr := fmt.Sprintf("%s:%d", domainInfo.Proxies[0].IP, domainInfo.Proxies[0].Port)
	whiteList, _, _, err := service.ProxyWhiteList(
		proxyAddr,
		domainInfo.BkCloudId,
		clientIps,
		users,
		domainInfo.ImmuteDomain,
	)
	if err != nil {
		return nil, err
	}

	return service.CombineUserWithGrant(whiteList, splitUserGrants, true), nil
}

func privsFromTenDBHASlave(domainInfo *service.Instance, users []string, clientIps []string,
	dbs []string) ([]service.GrantInfo, error) {
	idx := slices.IndexFunc(domainInfo.Storages, func(s service.Storage) bool {
		// ToDo 这里其实有点问题, 如果有多个 slave, 应该返回哪一个?
		return s.InstanceRole == v2.InstanceRoleBackendSlave
	})
	backendAddr := fmt.Sprintf("%s:%d", domainInfo.Storages[idx].IP, domainInfo.Storages[idx].Port)

	userList, _, matchHosts, err := service.MysqlUserList(
		backendAddr,
		domainInfo.BkCloudId,
		clientIps,
		users,
		domainInfo.ImmuteDomain,
	)
	if err != nil {
		return nil, err
	}

	if len(matchHosts) == 0 {
		return nil, nil
	}

	userGrants, err := service.GetRemotePrivilege(
		backendAddr,
		matchHosts,
		domainInfo.BkCloudId,
		v2.MachineTypeBackend,
		strings.Join(users, `','`),
		true,
	)
	if err != nil {
		return nil, err
	}
	if len(userGrants) == 0 {
		return nil, nil
	}

	splitUserGrants := service.SplitGrantSql(userGrants, dbs, false)
	return service.CombineUserWithGrant(userList, splitUserGrants, false), nil
}

func privsFromTenDBCluster() {

}

// func privsFromMySQL(addr string, isMasterDomain bool, domainInfo *service.Instance, users, clientIps,
// 	dbs []string) ([]service.GrantInfo, error) {

// }

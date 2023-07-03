package service

import (
	"fmt"
	"strings"
	"sync"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/priv-service/util"

	"github.com/spf13/viper"
)

// CloneClientPrivDryRun 克隆客户端权限预检查
func (m *CloneClientPrivParaList) CloneClientPrivDryRun() error {

	var errMsg []string
	var errMsgTemp []string
	if m.BkBizId == 0 {
		return errno.BkBizIdIsEmpty
	}

	var UniqMap = make(map[string]struct{})
	for index, slaveRecord := range m.CloneClientPrivRecords {
		errMsgTemp = validateIP(slaveRecord.SourceIp, slaveRecord.TargetIp, slaveRecord.BkCloudId)
		if len(errMsgTemp) > 0 {
			msg := fmt.Sprintf("line %d: input is invalid, reason: %s", index+1, strings.Join(errMsgTemp, ", "))
			errMsg = append(errMsg, msg)
		}

		tempStr := slaveRecord.String()
		if _, isExists := UniqMap[tempStr]; isExists == true {
			msg := fmt.Sprintf("line %d: record is duplicate", index+1)
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

// CloneClientPriv 克隆客户端权限
func (m *CloneClientPrivPara) CloneClientPriv(jsonPara string) error {
	var errMsg Err
	wg := sync.WaitGroup{}
	tokenBucket := make(chan int, 10)

	if m.BkBizId == 0 {
		return errno.BkBizIdIsEmpty
	}
	if m.BkCloudId == nil {
		return errno.CloudIdRequired
	}
	if m.ClusterType == nil {
		ct := mysql
		m.ClusterType = &ct
		// return errno.ClusterTypeIsEmpty
	}

	AddPrivLog(PrivLog{BkBizId: m.BkBizId, Operator: m.Operator, Para: jsonPara, Time: util.NowTimeFormat()})

	client := util.NewClientByHosts(viper.GetString("dbmeta"))
	resp, errOuter := GetAllClustersInfo(client, BkBizIdPara{m.BkBizId})
	if errOuter != nil {
		return errOuter
	}
	var clusters []Cluster
	for _, item := range resp {
		if item.BkCloudId == *m.BkCloudId {
			// mysql客户权限克隆，会克隆tendbha、tendbsingle集群内的权限
			// spider客户权限克隆，会克隆tendbcluster集群内的权限
			if *m.ClusterType == tendbcluster && item.ClusterType == tendbcluster {
				clusters = append(clusters, item)
			} else if *m.ClusterType == mysql && (item.ClusterType == tendbha ||
				item.ClusterType == tendbsingle) {
				clusters = append(clusters, item)
			}
		}
	}
	errMsg.errs = validateIP(m.SourceIp, m.TargetIp, m.BkCloudId)
	if len(errMsg.errs) > 0 {
		return errno.ClonePrivilegesFail.Add("\n" + strings.Join(errMsg.errs, "\n"))
	}
	// 获取业务下所有的集群，并行获取对旧的client授权的语句，替换旧client的ip为新client，执行导入
	// 一个协程失败，其报错信息添加到errMsg.errs。主协程wg.Wait()，等待所有协程执行完成才会返回。

	// 每个集群一个协程
	for _, item := range clusters {
		wg.Add(1)
		tokenBucket <- 0
		go func(item Cluster) {
			defer func() {
				<-tokenBucket
				wg.Done()
			}()

			if item.ClusterType == tendbha || item.ClusterType == tendbsingle {
				for _, storage := range item.Storages {
					address := fmt.Sprintf("%s:%d", storage.IP, storage.Port)
					userGrants, err := GetRemotePrivilege(address, m.SourceIp, item.BkCloudId, machineTypeBackend)
					if err != nil {
						AddError(&errMsg, address, err)
						return
					}
					userGrants = ReplaceHostInMysqlGrants(userGrants, m.SourceIp, m.TargetIp)
					err = ImportMysqlPrivileges(userGrants, address, item.BkCloudId)
					if err != nil {
						AddError(&errMsg, address, err)
						return
					}
				}
			} else {
				spiders := append(append(item.SpiderMaster, item.SpiderSlave...), item.SpiderMnt...)
				for _, spider := range spiders {
					address := fmt.Sprintf("%s:%d", spider.IP, spider.Port)
					userGrants, err := GetRemotePrivilege(address, m.SourceIp, item.BkCloudId, machineTypeSpider)
					if err != nil {
						AddError(&errMsg, address, err)
						return
					}
					userGrants = ReplaceHostInMysqlGrants(userGrants, m.SourceIp, m.TargetIp)
					err = ImportMysqlPrivileges(userGrants, address, item.BkCloudId)
					if err != nil {
						AddError(&errMsg, address, err)
						return
					}
				}
			}
			if item.ClusterType == tendbha {
				for _, proxy := range item.Proxies {
					address := fmt.Sprintf("%s:%d", proxy.IP, proxy.AdminPort)
					proxyGrants, err := GetProxyPrivilege(address, m.SourceIp, item.BkCloudId)
					if err != nil {
						AddError(&errMsg, address, err)
					}
					proxyGrants = ReplaceHostInProxyGrants(proxyGrants, m.SourceIp, m.TargetIp)
					err = ImportProxyPrivileges(proxyGrants, address, item.BkCloudId)
					if err != nil {
						AddError(&errMsg, address, err)
					}
				}
			}
		}(item)
	}
	wg.Wait()
	close(tokenBucket)
	if len(errMsg.errs) > 0 {
		return errno.ClonePrivilegesFail.Add("\n" + strings.Join(errMsg.errs, "\n"))
	}
	return nil
}

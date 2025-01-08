package service

import (
	"context"
	"dbm-services/common/go-pubpkg/mysqlcomm"
	"fmt"
	"log/slog"
	"strings"
	"sync"
	"time"

	"golang.org/x/time/rate"

	"dbm-services/common/go-pubpkg/errno"
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
func (m *CloneClientPrivPara) CloneClientPriv(jsonPara string, ticket string) ([]ClusterGrantSql, error) {
	var errMsg Err
	var sqls ClusterGrants
	wg := sync.WaitGroup{}
	limit := rate.Every(time.Millisecond * 100) // QPS：10
	burst := 10                                 // 桶容量 10
	limiter := rate.NewLimiter(limit, burst)
	tokenBucket := make(chan int, 10) // 最大并行度

	if m.BkBizId == 0 {
		return nil, errno.BkBizIdIsEmpty
	}
	if m.BkCloudId == nil {
		return nil, errno.CloudIdRequired
	}
	if m.ClusterType == nil {
		ct := mysql
		m.ClusterType = &ct
	}

	AddPrivLog(PrivLog{BkBizId: m.BkBizId, Ticket: ticket, Operator: m.Operator, Para: jsonPara, Time: time.Now()})
	resp, errOuter := GetAllClustersInfo(BkBizIdPara{m.BkBizId})
	if errOuter != nil {
		return nil, errOuter
	}
	var tempClusters []Cluster
	var clusters []Cluster
	var notExists []string
	for _, item := range resp {
		if item.BkCloudId == *m.BkCloudId {
			// mysql客户权限克隆，会克隆tendbha、tendbsingle集群内的权限
			// spider客户权限克隆，会克隆tendbcluster集群内的权限
			if (*m.ClusterType == tendbcluster && item.ClusterType == tendbcluster) ||
				(*m.ClusterType == mysql && (item.ClusterType == tendbha ||
					item.ClusterType == tendbsingle)) {
				tempClusters = append(tempClusters, item)
			}
		}
	}

	// 内部调用，标准运维的指定用户的客户端克隆功能
	if len(m.TargetInstances) > 0 {
		for _, target := range m.TargetInstances {
			exist := false
			for _, temp := range tempClusters {
				if target == temp.ImmuteDomain {
					clusters = append(clusters, temp)
					exist = true
					break
				}
			}
			if exist == false {
				notExists = append(notExists, target)
			}
		}
		if len(notExists) > 0 {
			return nil, errno.DomainNotExists.AddBefore(strings.Join(notExists, ","))
		}
	} else {
		clusters = make([]Cluster, len(tempClusters))
		clusters = tempClusters
	}

	errMsg.errs = validateIP(m.SourceIp, m.TargetIp, m.BkCloudId)
	if len(errMsg.errs) > 0 {
		return nil, errno.ClonePrivilegesFail.Add("\n" + strings.Join(errMsg.errs, "\n"))
	}
	// 获取业务下所有的集群，并行获取对旧的client授权的语句，替换旧client的ip为新client，执行导入
	// 一个协程失败，其报错信息添加到errMsg.errs。主协程wg.Wait()，等待所有协程执行完成才会返回。

	// 每个集群一个协程
	slog.Info("msg", "clusters", clusters)
	for _, item := range clusters {
		errOuter = limiter.Wait(context.Background())
		if errOuter != nil {
			slog.Error("limiter.Wait", "error", errOuter)
			AddError(&errMsg, item.ImmuteDomain, errOuter)
			continue
		}
		wg.Add(1)
		tokenBucket <- 0
		slog.Info("msg", "item.ImmuteDomain", item.ImmuteDomain)
		go func(item Cluster) {
			defer func() {
				<-tokenBucket
				wg.Done()
			}()
			clusterGrant := ClusterGrantSql{ImmuteDomain: item.ImmuteDomain}
			if item.ClusterType == tendbha || item.ClusterType == tendbsingle {
				for _, storage := range item.Storages {
					address := fmt.Sprintf("%s:%d", storage.IP, storage.Port)
					// 在后端mysql中获取匹配的user@host列表
					_, _, matchHosts, err := MysqlUserList(address, item.BkCloudId, []string{m.SourceIp}, nil, "")
					if err != nil {
						AddError(&errMsg, address, err)
						continue
					}
					if len(matchHosts) == 0 {
						slog.Info("no match user@host", "instance", address,
							"source ip", m.SourceIp)
						continue
					}
					slog.Info("msg", "matchHosts", matchHosts)
					userGrants, err := GetRemotePrivilege(address, matchHosts, item.BkCloudId,
						machineTypeBackend, m.User, true)
					if err != nil {
						AddError(&errMsg, address, err)
						continue
					}
					if len(userGrants) == 0 {
						slog.Info("no match user@host", "instance", address,
							"source ip", m.SourceIp, "user", m.User)
						continue
					}
					userGrants = ReplaceHostInMysqlGrants(userGrants, m.TargetIp)
					var grants []string
					for _, sql := range userGrants {
						grants = append(grants, sql.Grants...)
					}
					clusterGrant.Sqls = append(clusterGrant.Sqls, InstanceGrantSql{address,
						mysqlcomm.ClearIdentifyByInSQLs(grants)})
					err = ImportMysqlPrivileges(userGrants, address, item.BkCloudId)
					if err != nil {
						AddError(&errMsg, address, err)
					}
				}
			} else {
				for _, spider := range item.Proxies {
					address := fmt.Sprintf("%s:%d", spider.IP, spider.Port)
					_, _, matchHosts, err := MysqlUserList(address, item.BkCloudId, []string{m.SourceIp}, nil, "")
					if err != nil {
						AddError(&errMsg, address, err)
						continue
					}
					if len(matchHosts) == 0 {
						slog.Info("no match user@host", "instance", address,
							"source ip", m.SourceIp)
						continue
					}
					userGrants, err := GetRemotePrivilege(address, matchHosts, item.BkCloudId,
						machineTypeSpider, m.User, true)
					if err != nil {
						AddError(&errMsg, address, err)
						continue
					}
					if len(userGrants) == 0 {
						slog.Info("no match user@host", "instance", address,
							"source ip", m.SourceIp, "user", m.User)
						continue
					}
					userGrants = ReplaceHostInMysqlGrants(userGrants, m.TargetIp)
					var grants []string
					for _, sql := range userGrants {
						grants = append(grants, sql.Grants...)
					}
					clusterGrant.Sqls = append(clusterGrant.Sqls, InstanceGrantSql{address,
						mysqlcomm.ClearIdentifyByInSQLs(grants)})
					err = ImportMysqlPrivileges(userGrants, address, item.BkCloudId)
					if err != nil {
						AddError(&errMsg, address, err)
					}
				}
			}
			if item.ClusterType == tendbha {
				for _, proxy := range item.Proxies {
					address := fmt.Sprintf("%s:%d", proxy.IP, proxy.AdminPort)
					_, _, matchHosts, err := ProxyWhiteList(address, item.BkCloudId, []string{m.SourceIp}, nil, "")
					if err != nil {
						slog.Error("msg", "ProxyWhiteList", err)
						AddError(&errMsg, address, err)
					}
					slog.Info("msg", "matchHosts", matchHosts)
					if len(matchHosts) == 0 {
						slog.Info("no match user@host", "instance", address,
							"source ip", m.SourceIp)
						continue
					}
					proxyUsers, err := GetProxyPrivilege(address, matchHosts, item.BkCloudId, m.User)
					if err != nil {
						slog.Error("msg", "GetProxyPrivilege", err)
						AddError(&errMsg, address, err)
					}
					if len(proxyUsers) == 0 {
						slog.Info("no match user@host", "instance", address, "user", m.User)
						continue
					}
					proxyUsers = ReplaceHostInProxyGrants(proxyUsers, m.TargetIp)

					var oneBuckUsers []string
					for _, u := range proxyUsers {
						oneBuckUsers = append(oneBuckUsers, u)
						if len(oneBuckUsers) >= 1000 {
							refreshSql := fmt.Sprintf(
								"refresh_users('%s', '+')",
								strings.Join(oneBuckUsers, ","),
							)
							clusterGrant.Sqls = append(clusterGrant.Sqls,
								InstanceGrantSql{address, []string{refreshSql}},
							)
							err = ImportProxyPrivileges(
								[]string{refreshSql},
								address, item.BkCloudId)
							if err != nil {
								AddError(&errMsg, address, err)
							}
							oneBuckUsers = []string{}
						}
					}
					refreshSql := fmt.Sprintf(
						"refresh_users('%s', '+')",
						strings.Join(oneBuckUsers, ","),
					)
					clusterGrant.Sqls = append(clusterGrant.Sqls,
						InstanceGrantSql{address, []string{refreshSql}},
					)
					err = ImportProxyPrivileges([]string{refreshSql}, address, item.BkCloudId)
					if err != nil {
						AddError(&errMsg, address, err)
					}
				}
			}
			if len(clusterGrant.Sqls) > 0 {
				sqls.mu.Lock()
				sqls.resources = append(sqls.resources, clusterGrant)
				sqls.mu.Unlock()
			}
		}(item)
	}
	wg.Wait()
	slog.Info("msg", "clusterGrant", sqls.resources)
	if len(errMsg.errs) > 0 {
		return nil, errno.ClonePrivilegesFail.Add("\n" + strings.Join(errMsg.errs, "\n"))
	}
	return sqls.resources, nil
}

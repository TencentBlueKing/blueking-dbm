package service

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"regexp"
	"strings"
	"sync"
	"time"

	"golang.org/x/time/rate"

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
	slog.Info(fmt.Sprintf("PrivTaskPara:%v", m))
	var errMsg, successMsg Err
	var wg sync.WaitGroup
	// 为了避免通过api未调用AddPrivDryRun，直接调用AddPriv，未做检查参数，所以AddPriv先调用AddPrivDryRun
	if _, outerErr := m.AddPrivDryRun(); outerErr != nil {
		return outerErr
	}
	if m.BkBizId == 0 {
		return errno.BkBizIdIsEmpty
	}
	if m.ClusterType == "" {
		return errno.ClusterTypeIsEmpty
	}
	AddPrivLog(PrivLog{BkBizId: m.BkBizId, Ticket: ticket, Operator: m.Operator, Para: jsonPara, Time: time.Now()})
	limit := rate.Every(time.Millisecond * 100) // QPS：10
	burst := 10                                 // 桶容量 10
	limiter := rate.NewLimiter(limit, burst)
	for _, rule := range m.AccoutRules { // 添加权限,for accountRuleList;for instanceList; do create a routine
		account, accountRule, outerErr := GetAccountRuleInfo(m.BkBizId, m.ClusterType, m.User, rule.Dbname)
		if outerErr != nil {
			AddErrorOnly(&errMsg, outerErr)
			continue
		}
		repl := accountRule
		var replFlag bool
		// replication slave、replication client 权限在tendbha集群下，单独处理，授权方式与其他权限不同
		for _, priv := range []string{"replication slave", "replication client"} {
			if strings.Contains(accountRule.GlobalPriv, priv) {
				replFlag = true
				accountRule.GlobalPriv = strings.Replace(accountRule.GlobalPriv, priv, "", -1)
				repl.GlobalPriv = fmt.Sprintf("%s,%s", repl.GlobalPriv, priv)
			}
		}
		if replFlag {
			repl.GlobalPriv = strings.Trim(repl.GlobalPriv, ",")
			accountRule.GlobalPriv = strings.Trim(accountRule.GlobalPriv, ",")
			accountRule.GlobalPriv = regexp.MustCompile(`,+`).ReplaceAllString(accountRule.GlobalPriv, ",")
		}
		for _, dns := range m.TargetInstances {
			errLimiter := limiter.Wait(context.Background())
			if errLimiter != nil {
				slog.Error("limiter.Wait", "error", errLimiter, "dns", dns)
				AddErrorOnly(&errMsg, errors.New(errLimiter.Error()))
				continue
			}
			wg.Add(1)
			go func(dns string) {
				defer func() {
					wg.Done()
				}()
				var (
					instance                                      Instance
					proxySQL, proxyIPs, errMsgInner               []string
					err                                           error
					tendbhaMasterDomain                           bool // 是否为集群的主域名
					tendbhaPaddingProxy                           bool //集群伪造了proxy，但是不使用proxy
					successInfo, failInfo, baseInfo, ips, address string
				)
				dns = strings.Trim(strings.TrimSpace(dns), ".")
				ips = strings.Join(m.SourceIPs, " ")
				baseInfo = fmt.Sprintf(`账号规则："%s-%s", 授权来源ip："%s"，使用账号："%s"，访问目标集群："%s"的数据库："%s"`,
					account.User, accountRule.Dbname, ips, account.User, dns, accountRule.Dbname)
				successInfo = fmt.Sprintf(`%s，授权成功。`, baseInfo)
				failInfo = fmt.Sprintf(`%s，授权失败：`, baseInfo)

				instance, err = GetCluster(m.ClusterType, Domain{EntryName: dns})
				if err != nil {
					AddErrorOnly(&errMsg, errors.New(failInfo+sep+err.Error()))
					return
				}
				if m.ClusterType == tendbha || m.ClusterType == tendbsingle {
					// 当"cluster_type": "tendbha", "bind_to": "proxy" tendbha的主域名, "bind_to": "storage" tendbha的备域名
					if instance.ClusterType == tendbha && instance.BindTo == machineTypeProxy {
						tendbhaMasterDomain = true
						tendbhaPaddingProxy = instance.PaddingProxy
						for _, proxy := range instance.Proxies {
							proxyIPs = append(proxyIPs, proxy.IP)
						}
					}
					for _, storage := range instance.Storages {
						if tendbhaMasterDomain && storage.InstanceRole == backendSlave && storage.Status != running {
							slog.Warn(baseInfo, "slave instance not running state, skipped",
								fmt.Sprintf("%s:%d", storage.IP, storage.Port))
							continue
						}
						address = fmt.Sprintf("%s:%d", storage.IP, storage.Port)
						err = ImportBackendPrivilege(account, accountRule, address, proxyIPs, m.SourceIPs,
							instance.ClusterType, tendbhaMasterDomain, instance.BkCloudId, false,
							tendbhaPaddingProxy)
						if err != nil {
							errMsgInner = append(errMsgInner, err.Error())
						}
						if replFlag {
							// 在mysql实例上授权
							err = ImportBackendPrivilege(account, repl, address, proxyIPs, m.SourceIPs,
								instance.ClusterType, tendbhaMasterDomain, instance.BkCloudId, false,
								true)
							if err != nil {
								errMsgInner = append(errMsgInner, err.Error())
							}
						}
					}
					if len(errMsgInner) > 0 {
						AddErrorOnly(&errMsg, errors.New(failInfo+sep+strings.Join(errMsgInner, sep)))
						return
					}
					if tendbhaMasterDomain && !tendbhaPaddingProxy { // proxy授权放到mysql授权执行之后，mysql授权成功，才在proxy执行
						proxySQL = GenerateProxyPrivilege(account.User, m.SourceIPs)
						var runningNum int
						for _, proxy := range instance.Proxies {
							if proxy.Status == running {
								runningNum = runningNum + 1
							}
						}
						if runningNum == 0 {
							errMsgInner = append(errMsgInner, "no running state proxy")
						} else {
							for _, proxy := range instance.Proxies {
								if proxy.Status != running {
									slog.Warn(baseInfo, "proxy instance not running state, skipped", fmt.Sprintf("%s:%d", proxy.IP, proxy.Port))
									continue
								}
								err = ImportProxyPrivilege(proxy, proxySQL, instance.BkCloudId)
								if err != nil {
									errMsgInner = append(errMsgInner, err.Error())
								}
							}
						}
					}
					if len(errMsgInner) > 0 {
						AddErrorOnly(&errMsg, errors.New(failInfo+sep+strings.Join(errMsgInner, sep)))
						return
					}
				} else if m.ClusterType == tendbcluster {
					var spiders []Proxy
					// spider在spider-master和spider-slave节点添加权限的行为是一致的，
					// 通过部署时spider-slave实例只读控制实际能执行的操作
					if instance.EntryRole == masterEntry {
						spiders = append(spiders, instance.SpiderMaster...)
					} else if instance.EntryRole == slaveEntry {
						spiders = append(spiders, instance.SpiderSlave...)
					} else {
						errMsgInner = append(errMsgInner, fmt.Sprintf("wrong entry role %s", instance.EntryRole))
					}
					var runningNum int
					for _, spider := range spiders {
						if spider.Status == running {
							runningNum = runningNum + 1
						}
					}
					if runningNum == 0 {
						errMsgInner = append(errMsgInner, "no running state spider")
					} else {
						for _, spider := range spiders {
							address = fmt.Sprintf("%s:%d", spider.IP, spider.Port)
							if spider.Status != running {
								slog.Warn(baseInfo, "spider instance not running state, skipped", address)
								continue
							}
							err = ImportBackendPrivilege(account, accountRule, address, proxyIPs, m.SourceIPs,
								instance.ClusterType, tendbhaMasterDomain, instance.BkCloudId, false,
								tendbhaPaddingProxy)
							if err != nil {
								errMsgInner = append(errMsgInner, err.Error())
							}
						}
					}
					if len(errMsgInner) > 0 {
						AddErrorOnly(&errMsg, errors.New(failInfo+sep+strings.Join(errMsgInner, sep)))
						return
					}
				} else {
					AddErrorOnly(&errMsg, errors.New(fmt.Sprintf("%s%scluster type is %s, wrong type", failInfo, sep,
						instance.ClusterType)))
					return
				}
				AddErrorOnly(&successMsg, errors.New(successInfo))
			}(dns)
		}
	}
	wg.Wait() // 一个协程失败，其报错信息添加到errMsg.errs。主协程wg.Wait()，等待所有协程执行完成才会返回。
	return AddPrivResult(errMsg, successMsg)
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

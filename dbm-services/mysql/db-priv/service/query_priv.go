package service

import (
	"context"
	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/priv-service/util"
	"fmt"
	"log/slog"
	"regexp"
	"strings"
	"sync"
	"time"

	"golang.org/x/time/rate"
)

// GetUserList 根据域名、ip获取账号列表
func (m *GetPrivPara) GetUserList() ([]string, int, error) {
	var count int
	var errMsg Err
	var userList StringList
	errCheck := m.CheckPara()
	if errCheck != nil {
		return userList.l, count, errCheck
	}
	wg := sync.WaitGroup{}
	limit := rate.Every(time.Millisecond * 50) // QPS：20
	burst := 20                                // 桶容量 20
	limiter := rate.NewLimiter(limit, burst)
	for _, item := range m.ImmuteDomains {
		errLimiter := limiter.Wait(context.Background())
		if errLimiter != nil {
			AddError(&errMsg, item, errLimiter)
			continue
		}
		wg.Add(1)
		go func(item string) {
			defer func() {
				wg.Done()
			}()
			var users []string
			instance, err := GetCluster(*m.ClusterType, Domain{EntryName: item})
			if err != nil {
				AddError(&errMsg, item, err)
				return
			}
			var tendbhaMasterDomain bool // 是否为集群的主域名
			if instance.ClusterType == tendbha && instance.BindTo == machineTypeProxy && !instance.PaddingProxy {
				tendbhaMasterDomain = true
			}
			// tendbha的主域名，从proxy中查询账号
			if tendbhaMasterDomain {
				if len(instance.Proxies) == 0 {
					AddError(&errMsg, item, fmt.Errorf("no proxy found"))
					return
				} else {
					proxy := instance.Proxies[0]
					address := fmt.Sprintf("%s:%d", proxy.IP, proxy.AdminPort)
					// 获取proxy中的账号
					_, users, _, err = ProxyWhiteList(address, instance.BkCloudId, m.Ips, nil, "")
					if err != nil {
						AddError(&errMsg, address, err)
						return
					}
				}
			} else {
				var address string
				// tendbha的从域名，或者单点，从后端mysql查询账号
				if instance.ClusterType == tendbha || instance.ClusterType == tendbsingle {
					for _, storage := range instance.Storages {
						if storage.InstanceRole == backendSlave || storage.InstanceRole == orphan {
							address = fmt.Sprintf("%s:%d", storage.IP, storage.Port)
							break
						}
					}
				} else if instance.ClusterType == tendbcluster {
					// tendbcluster，从spider节点查询账号
					if instance.EntryRole == masterEntry {
						for _, spider := range instance.SpiderMaster {
							address = fmt.Sprintf("%s:%d", spider.IP, spider.Port)
							break
						}
					} else if instance.EntryRole == slaveEntry {
						for _, spider := range instance.SpiderSlave {
							address = fmt.Sprintf("%s:%d", spider.IP, spider.Port)
							break
						}
					} else {
						AddError(&errMsg, item, fmt.Errorf("wrong entry role %s", instance.EntryRole))
					}
				} else {
					AddError(&errMsg, item, fmt.Errorf("wrong cluster type %s", instance.ClusterType))
				}
				if address == "" {
					AddError(&errMsg, item, fmt.Errorf("no instance found"))
				}
				// 获取mysql实例中的账号
				_, users, _, err = MysqlUserList(address, instance.BkCloudId, m.Ips, nil, "")
				if err != nil {
					AddError(&errMsg, address, err)
					return
				}
			}
			AddString(&userList, users)
		}(item)
	}
	wg.Wait()
	if len(errMsg.errs) > 0 {
		return userList.l, count, errno.QueryPrivilegesFail.Add("\n" + strings.Join(errMsg.errs, "\n"))
	}
	var uniqUser = make(map[string]struct{})
	var users []string
	for _, user := range userList.l {
		if _, isExists := uniqUser[user]; isExists == false {
			uniqUser[user] = struct{}{}
			users = append(users, user)
		}
	}
	return users, len(users), nil
}

// GetPriv 获取权限
func (m *GetPrivPara) GetPriv() ([]RelatedIp, []RelatedDomain2, int, []GrantInfo, []string, []string, error) {
	type PrivMu struct {
		mu        sync.RWMutex
		resources []GrantInfo
	}

	var (
		all    PrivMu
		count  int
		errMsg Err
	)
	errCheck := m.CheckPara()
	if errCheck != nil {
		return nil, nil, count, nil, nil, nil, errCheck
	}
	if len(m.Users) == 0 {
		return nil, nil, count, nil, nil, nil, errno.ErrUserIsEmpty
	}
	users := strings.Join(m.Users, "','")
	wg := sync.WaitGroup{}
	limit := rate.Every(time.Millisecond * 200) // 并发查询集群数量 QPS 5
	burst := 5                                  // 桶容量 5
	limiter := rate.NewLimiter(limit, burst)
	for _, item := range m.ImmuteDomains {
		errLimiter := limiter.Wait(context.Background())
		if errLimiter != nil {
			AddError(&errMsg, item, errLimiter)
			continue
		}
		wg.Add(1)
		go func(item string) {
			defer func() {
				wg.Done()
			}()
			instance, err := GetCluster(*m.ClusterType, Domain{EntryName: item})
			if err != nil {
				AddError(&errMsg, item, err)
				return
			}
			var tendbhaMasterDomain bool // 是否为集群的主域名
			var userGrants []UserGrant
			var result []GrantInfo
			var matchHosts string
			dbpriv := make(map[string][]DbPriv)
			if instance.ClusterType == tendbha && instance.BindTo == machineTypeProxy && !instance.PaddingProxy {
				tendbhaMasterDomain = true
			}
			// tendbha的主域名，从后端查询权限信息，从proxy中查询user
			if tendbhaMasterDomain {
				if len(instance.Proxies) == 0 {
					AddError(&errMsg, item, fmt.Errorf("no proxy found"))
					return
				} else {
					proxy := instance.Proxies[0]
					// 在后端mysql查询权限信息
					for _, storage := range instance.Storages {
						if storage.InstanceRole == backendMaster {
							address := fmt.Sprintf("%s:%d", storage.IP, storage.Port)
							slog.Info("msg", "backend", address)
							userGrants, err = GetRemotePrivilege(address, proxy.IP, instance.BkCloudId,
								machineTypeBackend, users, true)
							if err != nil {
								AddError(&errMsg, address, err)
								return
							}
							// 对权限语句做正则匹配，模糊匹配，过滤出匹配输入db的权限信息
							dbpriv = SplitGrantSql(userGrants, m.Dbs, tendbhaMasterDomain)
							break
						}
					}
					address := fmt.Sprintf("%s:%d", proxy.IP, proxy.AdminPort)
					slog.Info("msg", "proxy", address)
					// 在proxy查询查询user@ip
					result, _, _, err = ProxyWhiteList(address, instance.BkCloudId, m.Ips, m.Users, item)
					if err != nil {
						AddError(&errMsg, address, err)
						return
					}
					// 将proxy的user@ip与mysql查询到的user@proxy_ip相结合
					result = CombineUserWithGrant(result, dbpriv, tendbhaMasterDomain)
				}
			} else {
				var address string
				var machineType string
				if instance.ClusterType == tendbha || instance.ClusterType == tendbsingle {
					for _, storage := range instance.Storages {
						if storage.InstanceRole == backendSlave || storage.InstanceRole == orphan {
							address = fmt.Sprintf("%s:%d", storage.IP, storage.Port)
							machineType = machineTypeBackend
							break
						}
					}
				} else if instance.ClusterType == tendbcluster {
					// tendbcluster，从spider节点查询账号
					if instance.EntryRole == masterEntry {
						for _, spider := range instance.SpiderMaster {
							address = fmt.Sprintf("%s:%d", spider.IP, spider.Port)
							break
						}
					} else if instance.EntryRole == slaveEntry {
						for _, spider := range instance.SpiderSlave {
							address = fmt.Sprintf("%s:%d", spider.IP, spider.Port)
							break
						}
					} else {
						AddError(&errMsg, item, fmt.Errorf("wrong entry role %s", instance.EntryRole))
					}
				} else {
					AddError(&errMsg, item, fmt.Errorf("wrong cluster type %s", instance.ClusterType))
					return
				}
				if address == "" {
					AddError(&errMsg, item, fmt.Errorf("no instance found"))
					return
				}
				// 在后端mysql中获取匹配的user@host列表
				result, _, matchHosts, err = MysqlUserList(address, instance.BkCloudId, m.Ips, m.Users, item)
				if err != nil {
					AddError(&errMsg, address, err)
					return
				}
				if len(matchHosts) == 0 {
					slog.Info("no match user@host", "instance", address,
						"source ip", m.Ips, "users", m.Users)
					return
				}
				// 获取user@host的权限信息
				userGrants, err = GetRemotePrivilege(address, matchHosts, instance.BkCloudId,
					machineType, users, true)
				if err != nil {
					AddError(&errMsg, address, err)
					return
				}
				if len(userGrants) == 0 {
					slog.Info("no match user@host", "instance", address,
						"source ip", matchHosts, "users", users)
					return
				}
				// 对权限语句做正则匹配，模糊匹配，过滤出匹配输入db的权限信息
				dbpriv = SplitGrantSql(userGrants, m.Dbs, tendbhaMasterDomain)
				// mysql中的账号与权限相结合
				result = CombineUserWithGrant(result, dbpriv, tendbhaMasterDomain)
			}
			slog.Info("msg", "SplitGrantSql", dbpriv)
			slog.Info("msg", "CombineUserWithGrant", result)
			all.mu.Lock()
			all.resources = append(all.resources, result...)
			all.mu.Unlock()
		}(item)
	}
	wg.Wait()
	if len(errMsg.errs) > 0 {
		return nil, nil, count, nil, nil, nil, errno.QueryPrivilegesFail.Add("\n" + strings.Join(errMsg.errs, "\n"))
	}
	slog.Info("msg", "all.resources", all.resources)
	// 以访问源的ip等维度聚合展示
	if m.Format == "ip" {
		formatted, hasPriv, noPriv := FormatRelatedIp(all.resources, m.Ips)
		return formatted, nil, len(formatted), all.resources, hasPriv, noPriv, nil
	} else if m.Format == "cluster" {
		formatted, hasPriv, noPriv := FormatRelatedCluster(all.resources, m.Ips, m.ImmuteDomains)
		return nil, formatted, len(formatted), all.resources, hasPriv, noPriv, nil
	} else {
		return nil, nil, 0, nil, nil, nil, fmt.Errorf("not supported display format")
	}
}

// CombineUserWithGrant 将账号与权限信息关联
func CombineUserWithGrant(user []GrantInfo, dbPriv map[string][]DbPriv, tendbhaMasterDomain bool) []GrantInfo {
	var result []GrantInfo
	if tendbhaMasterDomain {
		for _, userIp := range user {
			v, isExists := dbPriv[userIp.User]
			if isExists == false {
				continue
			}
			userIp.Privs = v
			result = append(result, userIp)
		}
	} else {
		for _, userIp := range user {
			k := fmt.Sprintf(`'%s'@'%s'`, userIp.User, userIp.MatchIp)
			v, isExists := dbPriv[k]
			if isExists == false {
				continue
			}
			userIp.Privs = v
			result = append(result, userIp)
		}
	}
	return result
}

// SplitGrantSql 对权限语句做正则匹配，过滤出匹配输入db的权限信息，包括全局权限
func SplitGrantSql(grants []UserGrant, dbs []string, tendbhaMasterDomain bool) map[string][]DbPriv {
	userPriv := make(map[string][]DbPriv)
	// 正则匹配授权语句，过滤出权限、db
	re := regexp.MustCompile("GRANT (.*) ON ['`](.*)['`]\\.\\*")
	var filterDb bool
	if len(dbs) > 0 {
		filterDb = true
	}
	var userHost string
	for _, grant := range grants {
		if tendbhaMasterDomain {
			userHost = strings.Split(strings.Replace(grant.UserHost, "'", "", -1), "@")[0]
		} else {
			userHost = grant.UserHost
		}
		for _, sql := range grant.Grants {
			split := re.FindStringSubmatch(sql)
			if len(split) != 3 {
				slog.Warn("msg", "not format grants", sql, "wrong regexp", split)
				continue
			}
			db := split[2]
			priv := split[1]
			// 全局权限
			if split[2] == "*" {
				if priv == "USAGE" {
					continue
				}
				// 全局权限可以匹配任何目标db
				if filterDb {
					for _, targetDb := range dbs {
						userPriv[userHost] = append(userPriv[userHost],
							DbPriv{Db: targetDb, MatchDb: "*", Priv: priv})
					}
				} else {
					userPriv[userHost] = append(userPriv[userHost],
						DbPriv{MatchDb: "*", Priv: priv})
				}
			} else {
				// db权限
				if filterDb {
					// db模糊匹配，比如db%可以匹配db
					reStr := strings.Replace(db, "%", ".*", -1)
					reDb := regexp.MustCompile(reStr)
					for _, targetDb := range dbs {
						if reDb.MatchString(targetDb) {
							userPriv[userHost] = append(userPriv[userHost], DbPriv{Db: targetDb,
								MatchDb: db, Priv: split[1]})
						}
					}
				} else {
					userPriv[userHost] = append(userPriv[userHost],
						DbPriv{MatchDb: db, Priv: priv})
				}
			}
		}
	}
	return userPriv
}

// ProxyWhiteList 查询出proxy上与指定账号、指定ip所匹配的账号
func ProxyWhiteList(address string, bkCloudId int64, hosts []string, usersInput []string,
	immuteDomain string) ([]GrantInfo, []string, []string, error) {
	var UniqMap = make(map[string]struct{})
	var UniqMapHost = make(map[string]struct{})
	var users []string
	var matchHosts []string
	sql := "select * from user;"
	var infos []GrantInfo
	var queryRequest = QueryRequest{[]string{address}, []string{sql}, true, 30, bkCloudId}
	output, err := OneAddressExecuteProxySql(queryRequest)
	if err != nil {
		return infos, users, matchHosts, fmt.Errorf(
			"execute (%s) in bk_cloud_id (%d) instance (%s) get an error:%s", sql, bkCloudId, address,
			err.Error())
	}
	usersResult := output.CmdResults[0].TableData
	for _, res := range usersResult {
		tmpUser := res["user@ip"].(string)
		l := strings.Split(tmpUser, "@")
		if len(l) != 2 {
			slog.Error("msg", "address", address, "wrong user@ip format", tmpUser)
			continue
		}
		user := l[0]
		host := l[1]
		if user == "MONITOR" {
			continue
		}
		if user == "" || host == "" {
			slog.Warn("msg", "user or host is null", "sql", sql, "address", address)
			continue
		}
		// ip模糊匹配，比如1.1.%可以匹配1.1.1.1
		reStr := fmt.Sprintf("@%s$", strings.Replace(strings.ReplaceAll(host, ".", "\\."), "%", ".*", -1))
		re := regexp.MustCompile(reStr)
		if len(usersInput) > 0 {
			for _, u := range usersInput {
				if u == user {
					for _, h := range hosts {
						if re.MatchString(fmt.Sprintf("@%s", h)) {
							infos = append(infos, GrantInfo{Ip: h, MatchIp: host, User: user, ImmuteDomain: immuteDomain})
						}
					}
					break
				}
			}
		} else {
			for _, h := range hosts {
				if re.MatchString(fmt.Sprintf("@%s", h)) {
					if _, isExists := UniqMap[user]; isExists == false {
						UniqMap[user] = struct{}{}
						users = append(users, user)
					}
					if _, isExists := UniqMapHost[host]; isExists == false {
						UniqMapHost[host] = struct{}{}
						matchHosts = append(matchHosts, host)
					}
				}
			}
		}
	}
	return infos, users, matchHosts, nil
}

// MysqlUserList 在mysql中查询与输入用户名、以及ip相配的账号信息，查询到user@host列表
func MysqlUserList(address string, bkCloudId int64, hosts []string, usersInput []string,
	immuteDomain string) ([]GrantInfo, []string, string, error) {
	var UniqMap = make(map[string]struct{})
	var UniqMapHost = make(map[string]struct{})
	var users []string
	var infos []GrantInfo
	var matchHosts []string
	vsql := `select user,host from mysql.user where 1=1`
	if len(usersInput) > 0 {
		vsql = fmt.Sprintf(`%s and user in ("%s") `, vsql, strings.Join(usersInput, "','"))
	}
	var queryRequest = QueryRequest{[]string{address}, []string{vsql}, true, 30, bkCloudId}
	output, err := OneAddressExecuteSql(queryRequest)
	if err != nil {
		return infos, nil, "", fmt.Errorf(
			"execute (%s) in bk_cloud_id (%d) instance (%s) get an error:%s", vsql, bkCloudId, address,
			err.Error())
	}
	usersResult := output.CmdResults[0].TableData
	for _, res := range usersResult {
		user := res["user"].(string)
		host := res["host"].(string)
		if user == "MONITOR" {
			continue
		}
		if user == "" || host == "" {
			slog.Warn("msg", "user or host is null", "sql", vsql, "address", address)
			continue
		}
		// ip模糊匹配，比如1.1.%可以匹配1.1.1.1
		reStr := strings.Replace(strings.ReplaceAll(host, ".", "\\."), "%", ".*", -1)
		re := regexp.MustCompile(reStr)
		if len(usersInput) > 0 {
			for _, u := range usersInput {
				if u == user {
					for _, h := range hosts {
						if re.MatchString(h) {
							infos = append(infos, GrantInfo{Ip: h, MatchIp: host, User: u, ImmuteDomain: immuteDomain})
							matchHosts = append(matchHosts, host)
						}
					}
					break
				}
			}
		} else {
			for _, h := range hosts {
				if re.MatchString(h) {
					if _, isExists := UniqMap[user]; isExists == false {
						UniqMap[user] = struct{}{}
						users = append(users, user)
					}
					if _, isExists := UniqMapHost[host]; isExists == false {
						UniqMapHost[host] = struct{}{}
						matchHosts = append(matchHosts, host)
					}
				}
			}
		}
	}
	return infos, users, strings.Join(matchHosts, "','"), nil
}

// CheckPara 查询权限入参检查
func (m *GetPrivPara) CheckPara() error {
	if m.ClusterType == nil {
		return errno.ClusterTypeIsEmpty
	}
	if len(m.Ips) == 0 {
		return errno.IpRequired
	}
	if len(m.ImmuteDomains) == 0 {
		return errno.DomainRequired
	}
	return nil
}

// FormatRelatedIp 权限结果格式化，以ip、访问DB、域名、用户等维度依次聚合展示
func FormatRelatedIp(source []GrantInfo, ips []string) ([]RelatedIp, []string, []string) {
	var result []RelatedIp
	var hasPriv, noPriv []string
	var UniqIp = make(map[string][]RelatedDb)
	var UniqIpDb = make(map[string][]RelatedDomain)
	var UniqIpDbDomain = make(map[string][]RelatedUser)
	var UniqIpDbDomainUser = make(map[string][]RelatedMatchIp)
	var UniqIpDbDomainUserMatchIp = make(map[string][]RelatedMatchDb)
	for _, grant := range source {
		// 对所有的权限归类，记录每个权限细则的信息：查询ip、查询db、域名、用户、命中ip
		for _, priv := range grant.Privs {
			IpDbDomainUserMatchIp := fmt.Sprintf("|%s|%s|%s|%s|%s|", grant.Ip, priv.Db,
				grant.ImmuteDomain, grant.User, grant.MatchIp)
			IpDbDomainUser := fmt.Sprintf("|%s|%s|%s|%s|", grant.Ip, priv.Db,
				grant.ImmuteDomain, grant.User)
			IpDbDomain := fmt.Sprintf("|%s|%s|%s|", grant.Ip, priv.Db, grant.ImmuteDomain)
			IpDb := fmt.Sprintf("|%s|%s|", grant.Ip, priv.Db)
			Ip := grant.Ip
			UniqIpDbDomainUserMatchIp[IpDbDomainUserMatchIp] = append(UniqIpDbDomainUserMatchIp[IpDbDomainUserMatchIp],
				RelatedMatchDb{priv.MatchDb, priv.Priv})
			UniqIpDbDomainUser[IpDbDomainUser] = nil
			UniqIpDbDomain[IpDbDomain] = nil
			UniqIpDb[IpDb] = nil
			UniqIp[Ip] = nil
		}
	}

	for user := range UniqIpDbDomainUser {
		for k, v := range UniqIpDbDomainUserMatchIp {
			if strings.Contains(k, user) {
				matchIp := strings.Split(k, "|")[5]
				UniqIpDbDomainUser[user] = append(UniqIpDbDomainUser[user], RelatedMatchIp{matchIp, v})
			}
		}
	}
	for domain := range UniqIpDbDomain {
		for k, v := range UniqIpDbDomainUser {
			if strings.Contains(k, domain) {
				user := strings.Split(k, "|")[4]
				UniqIpDbDomain[domain] = append(UniqIpDbDomain[domain], RelatedUser{user, v})
			}
		}
	}
	for db := range UniqIpDb {
		for k, v := range UniqIpDbDomain {
			if strings.Contains(k, db) {
				domain := strings.Split(k, "|")[3]
				UniqIpDb[db] = append(UniqIpDb[db], RelatedDomain{domain, v})
			}
		}
	}
	for ip := range UniqIp {
		for k, v := range UniqIpDb {
			if strings.Contains(k, fmt.Sprintf("|%s|", ip)) {
				db := strings.Split(k, "|")[2]
				UniqIp[ip] = append(UniqIp[ip], RelatedDb{db, v})
			}
		}
	}
	// 以ip的维度展示
	for _, ip := range ips {
		if v, isExists := UniqIp[ip]; isExists == false {
			noPriv = append(noPriv, ip)
		} else {
			hasPriv = append(hasPriv, ip)
			result = append(result, RelatedIp{ip, v})
		}
	}
	return result, hasPriv, noPriv
}

// FormatRelatedCluster 权限结果格式化，以域名、用户、匹配的访问源、匹配的DB等维度依次聚合展示
func FormatRelatedCluster(source []GrantInfo, ips []string, domains []string) ([]RelatedDomain2, []string, []string) {
	var hasPriv, noPriv []string
	var result []RelatedDomain2
	var UniqDomain = make(map[string][]RelatedUser2)
	var UniqDomainUser = make(map[string][]RelatedMatchIp2)
	var UniqDomainUserMatchIp = make(map[string][]RelatedMatchDb2)
	var UniqDomainUserMatchIpMatchDbPriv = make(map[string][]RelatedIpDb)
	var UniqDomainUserMatchIpMatchDbPrivTemp = make(map[string][]RelatedIpDb)
	var uniqIp = make(map[string]struct{})
	for _, grant := range source {
		// 对所有的权限归类，记录每个权限细则的信息：域名、用户、命中ip、命中的db、权限细则
		for _, priv := range grant.Privs {
			DomainUserMatchIpMatchDbPriv := fmt.Sprintf("|%s|%s|%s|%s|%s|", grant.ImmuteDomain,
				grant.User, grant.MatchIp, priv.MatchDb, priv.Priv)
			DomainUserMatchIp := fmt.Sprintf("|%s|%s|%s|", grant.ImmuteDomain, grant.User, grant.MatchIp)
			DomainUser := fmt.Sprintf("|%s|%s|", grant.ImmuteDomain, grant.User)
			vDomain := grant.ImmuteDomain
			UniqDomainUserMatchIpMatchDbPrivTemp[DomainUserMatchIpMatchDbPriv] =
				append(UniqDomainUserMatchIpMatchDbPrivTemp[DomainUserMatchIpMatchDbPriv],
					RelatedIpDb{grant.Ip, priv.Db})
			UniqDomainUserMatchIp[DomainUserMatchIp] = nil
			UniqDomainUser[DomainUser] = nil
			UniqDomain[vDomain] = nil
		}
	}
	// 同一个权限规则，对应的ip与db整合展示、去重
	for k, v := range UniqDomainUserMatchIpMatchDbPrivTemp {
		var uniqIpForUserHost = make(map[string]struct{})
		var uniqDbForUserHost = make(map[string]struct{})
		var ipsTmp, dbsTmp []string
		for _, ipDb := range v {
			if _, isExists := uniqIp[ipDb.Ip]; isExists == false {
				uniqIp[ipDb.Ip] = struct{}{}
				hasPriv = append(hasPriv, ipDb.Ip)
			}
			if _, isExists := uniqIpForUserHost[ipDb.Ip]; isExists == false {
				uniqIpForUserHost[ipDb.Ip] = struct{}{}
				ipsTmp = append(ipsTmp, ipDb.Ip)
			}
			if _, isExists := uniqDbForUserHost[ipDb.Db]; isExists == false {
				uniqDbForUserHost[ipDb.Db] = struct{}{}
				dbsTmp = append(dbsTmp, ipDb.Db)
			}
		}
		UniqDomainUserMatchIpMatchDbPriv[k] = []RelatedIpDb{{strings.Join(ipsTmp, ","),
			strings.Join(dbsTmp, ",")}}
	}
	// 找到未匹配到权限的ip
	for _, v := range ips {
		if !util.HasElem(v, hasPriv) {
			noPriv = append(noPriv, v)
		}
	}
	for matchip := range UniqDomainUserMatchIp {
		for k, v := range UniqDomainUserMatchIpMatchDbPriv {
			if strings.Contains(k, matchip) {
				splits := strings.Split(k, "|")
				matchDB := splits[4]
				priv := splits[5]
				UniqDomainUserMatchIp[matchip] = append(UniqDomainUserMatchIp[matchip],
					RelatedMatchDb2{matchDB, priv, v})
			}
		}
	}
	for user := range UniqDomainUser {
		for k, v := range UniqDomainUserMatchIp {
			if strings.Contains(k, user) {
				matchip := strings.Split(k, "|")[3]
				UniqDomainUser[user] = append(UniqDomainUser[user],
					RelatedMatchIp2{matchip, v})
			}
		}
	}
	for domain := range UniqDomain {
		for k, v := range UniqDomainUser {
			if strings.Contains(k, fmt.Sprintf("|%s|", domain)) {
				user := strings.Split(k, "|")[2]
				UniqDomain[domain] = append(UniqDomain[domain],
					RelatedUser2{user, v})
			}
		}
	}
	// 以集群维度展示
	for _, domain := range domains {
		if v, isExists := UniqDomain[domain]; isExists == true {
			result = append(result, RelatedDomain2{domain, v})
		}
	}
	return result, hasPriv, noPriv
}

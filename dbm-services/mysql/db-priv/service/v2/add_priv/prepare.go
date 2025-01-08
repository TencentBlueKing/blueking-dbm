package add_priv

import (
	"dbm-services/mysql/priv-service/service"
	"dbm-services/mysql/priv-service/service/v2/internal"
	"fmt"
	"log/slog"
	"strings"
)

func (c *PrivTaskPara) prepareMySQLPayload(targetMetaInfos ...*service.Instance) (
	clientIps []string,
	workingMySQLInstances map[int64][]string) {
	slog.Info(
		"prepare mysql payload",
		slog.String("cluster type", c.ClusterType),
	)
	switch c.ClusterType {
	case internal.ClusterTypeTenDBSingle:
		return c.prepareTenDBSingle(targetMetaInfos)
	case internal.ClusterTypeTenDBHA:
		return c.prepareTenDBHA(targetMetaInfos)
	default:
		return c.prepareTenDBCluster(targetMetaInfos)
	}
}

func (c *PrivTaskPara) prepareTenDBSingle(targetMetaInfos []*service.Instance) (
	clientIps []string,
	workingMySQLInstances map[int64][]string) {
	clientIps = c.SourceIPs
	workingMySQLInstances = make(map[int64][]string)

	for _, ele := range targetMetaInfos {
		for _, s := range ele.Storages {
			if _, ok := workingMySQLInstances[ele.BkCloudId]; !ok {
				workingMySQLInstances[ele.BkCloudId] = make([]string, 0)
			}
			workingMySQLInstances[ele.BkCloudId] = append(
				workingMySQLInstances[ele.BkCloudId],
				fmt.Sprintf(`%s:%d`, s.IP, s.Port))
		}
	}

	return
}

func (c *PrivTaskPara) prepareTenDBHA(targetMetaInfos []*service.Instance) (
	clientIps []string,
	workingMySQLInstances map[int64][]string) {
	clientIps = make([]string, 0)
	workingMySQLInstances = make(map[int64][]string)

	for _, ele := range targetMetaInfos {
		var proxyIps []string
		for _, p := range ele.Proxies {
			proxyIps = append(proxyIps, p.IP)
		}

		// 申请主域名权限要把来源替换为 proxy ip
		// 如果集群有 padding proxy 属性, 则是把 proxy ip 追加到 client ip 里
		slog.Info(
			"prepare tendbha",
			slog.String("bind to", ele.BindTo),
			slog.Bool("padding proxy", ele.PaddingProxy),
		)
		if ele.BindTo == internal.MachineTypeProxy {
			if ele.PaddingProxy {
				clientIps = append(c.SourceIPs, proxyIps...)
			} else {
				clientIps = proxyIps
			}
		} else {
			clientIps = c.SourceIPs
		}
		slog.Info("prepare tendbha", slog.String("clientIps", strings.Join(clientIps, ",")))
		// TenDBHA 要在所有存储实例执行授权
		for _, s := range ele.Storages {
			if _, ok := workingMySQLInstances[ele.BkCloudId]; !ok {
				workingMySQLInstances[ele.BkCloudId] = make([]string, 0)
			}
			workingMySQLInstances[ele.BkCloudId] = append(
				workingMySQLInstances[ele.BkCloudId],
				fmt.Sprintf(`%s:%d`, s.IP, s.Port),
			)
		}
	}

	return
}

func (c *PrivTaskPara) prepareTenDBCluster(targetMetaInfos []*service.Instance) (clientIps []string, workingMySQLInstances map[int64][]string) {
	clientIps = c.SourceIPs
	workingMySQLInstances = make(map[int64][]string)

	// 对应的 spider 上执行授权
	// 这里不会涉及中控实例
	for _, ele := range targetMetaInfos {
		if ele.EntryRole == internal.EntryRoleMasterEntry {
			for _, s := range ele.SpiderMaster {
				if _, ok := workingMySQLInstances[ele.BkCloudId]; !ok {
					workingMySQLInstances[ele.BkCloudId] = make([]string, 0)
				}
				workingMySQLInstances[ele.BkCloudId] = append(
					workingMySQLInstances[ele.BkCloudId],
					fmt.Sprintf(`%s:%d`, s.IP, s.Port),
				)
			}
		} else {
			for _, s := range ele.SpiderSlave {
				if _, ok := workingMySQLInstances[ele.BkCloudId]; !ok {
					workingMySQLInstances[ele.BkCloudId] = make([]string, 0)
				}
				workingMySQLInstances[ele.BkCloudId] = append(
					workingMySQLInstances[ele.BkCloudId],
					fmt.Sprintf(`%s:%d`, s.IP, s.Port),
				)
			}
		}
	}

	return
}

package service

import (
	"encoding/json"
	"fmt"
	"net/http"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/priv-service/util"

	"golang.org/x/exp/slog"
)

const mysql string = "mysql" // 包含tendbha和tendbsingle
const tendbha string = "tendbha"
const tendbsingle string = "tendbsingle"
const tendbcluster string = "tendbcluster"
const machineTypeBackend string = "backend"
const machineTypeSingle string = "single"
const machineTypeRemote string = "remote"
const machineTypeProxy string = "proxy"
const machineTypeSpider string = "spider"
const backendSlave string = "backend_slave"
const running string = "running"
const tdbctl string = "tdbctl"

// GetAllClustersInfo TODO
/*
GetAllClustersInfo 获取业务下所有集群信息

	[{
		  "db_module_id": 126,
		  "bk_biz_id": "3",
		  "cluster_type": "tendbsingle",
		  "proxies": [],
		  "storages": [
		    {
		      "ip": "1.1.1.1.",
		      "instance_role": "orphan",
		      "port": 30000
		    }
		  ],
		  "immute_domain": "singledb.1.hayley.db"
		},
		{
		  "db_module_id": 500,
		  "bk_biz_id": "3",
		  "cluster_type": "tendbha",
		  "proxies": [
		    {
		      "ip": "1.1.1.1",
		      "admin_port": 41000,
		      "port": 40000
		    },
		    {
		      "ip": "2.2.2.2",
		      "admin_port": 41000,
		      "port": 40000
		    }
		  ],
		  "storages": [
		    {
		      "ip": "3.3.3.3",
		      "instance_role": "backend_slave",
		      "port": 30000
		    },
		    {
		      "ip": "4.4.4.4",
		      "instance_role": "backend_master",
		      "port": 40000
		    }
		  ],
		  "immute_domain": "gamedb.2.hayley.db"
		}]
*/
func GetAllClustersInfo(c *util.Client, id BkBizIdPara) ([]Cluster, error) {
	var resp []Cluster
	result, err := c.Do(http.MethodGet, "/db_meta/priv_manager/biz_clusters", id)
	if err != nil {
		slog.Error("priv_manager/biz_clusters", err)
		return resp, err
	}
	if err := json.Unmarshal(result.Data, &resp); err != nil {
		slog.Error("/db_meta/priv_manager/biz_clusters", err)
		return resp, err
	}
	return resp, nil
}

// GetCluster 根据域名获取集群信息
func GetCluster(c *util.Client, ClusterType string, dns Domain) (Instance, error) {
	var resp Instance
	url := fmt.Sprintf("/db_meta/priv_manager/%s/cluster_instances", ClusterType)
	result, err := c.Do(http.MethodGet, url, dns)
	if err != nil {
		slog.Error(url, err)
		return resp, errno.DomainNotExists.Add(fmt.Sprintf(" %s: %s", dns.EntryName, err.Error()))
	}
	if err := json.Unmarshal(result.Data, &resp); err != nil {
		return resp, err
	}
	return resp, nil
}

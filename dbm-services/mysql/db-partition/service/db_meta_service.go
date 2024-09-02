/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package service

import (
	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/db-partition/util"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"

	"github.com/spf13/viper"
)

// Tendbha TODO
const Tendbha string = "tendbha"

// Tendbsingle TODO
const Tendbsingle string = "tendbsingle"

// Tendbcluster TODO
const Tendbcluster string = "tendbcluster"

const Fail string = "failed"

const Success string = "succeeded"

// BackendMaster TODO
const BackendMaster string = "backend_master"

// Orphan TODO
const Orphan string = "orphan"

// CreateDbmTicket bk-dbm生成单据的接口
func CreateDbmTicket(config Ticket) (int, error) {
	var ticketId int
	type Data struct {
		Id                int     `json:"id"`
		Creator           string  `json:"creator"`
		CreateAt          string  `json:"create_at"`
		Updater           string  `json:"updater"`
		UpdateAt          string  `json:"update_at"`
		TicketType        string  `json:"ticket_type"`
		Status            string  `json:"status"`
		Remark            string  `json:"remark"`
		Group             string  `json:"group"`
		Details           Details `json:"details"`
		TicketTypeDisplay string  `json:"ticket_type_display"`
		StatusDisplay     string  `json:"status_display"`
		CostTime          int     `json:"cost_time"`
		BkBizName         string  `json:"bk_biz_name"`
		BkAppAbbr         string  `json:"bk_app_abbr"`
		IgnoreDuplication bool    `json:"ignore_duplication"`
		BkBizId           int     `json:"bk_biz_id"`
		IsReviewed        bool    `json:"is_reviewed"`
	}

	var resp Data
	result, err := util.TicketClient.Do(http.MethodPost, "tickets/", config)
	if err != nil {
		slog.Error("msg", err)
		return ticketId, err
	}
	if err = json.Unmarshal(result.Data, &resp); err != nil {
		return ticketId, err
	}
	return resp.Id, nil
}

// Domain GetClusterInfo 函数的入参
type Domain struct {
	EntryName string `json:"entry_name" url:"entry_name"`
}

// Instance GetCluster 函数返回的结构体
type Instance struct {
	Proxies      []Proxy   `json:"proxies"`
	Storages     []Storage `json:"storages"`
	SpiderMaster []Proxy   `json:"spider_master"`
	SpiderSlave  []Proxy   `json:"spider_slave"`
	ClusterType  string    `json:"cluster_type"`
	BkBizId      int64     `json:"bk_biz_id"`
	DbModuleId   int64     `json:"db_module_id"`
	BindTo       string    `json:"bind_to"`
	EntryRole    string    `json:"entry_role"`
	BkCloudId    int       `json:"bk_cloud_id"`
	ImmuteDomain string    `json:"immute_domain"`
}

// Proxy proxy 实例
type Proxy struct {
	IP        string `json:"ip"`
	Port      int    `json:"port"`
	AdminPort int    `json:"admin_port"`
	Status    string `json:"status"`
}

// Storage mysql 后端节点
type Storage struct {
	IP           string `json:"ip"`
	Port         int    `json:"port"`
	InstanceRole string `json:"instance_role"`
	Status       string `json:"status"`
}

// Cluster GetAllClustersInfo 函数返回 Cluster 数组
type Cluster struct {
	Id           int64     `json:"id"`
	DbModuleId   int64     `json:"db_module_id"`
	BkBizId      int64     `json:"bk_biz_id"`
	Proxies      []Proxy   `json:"proxies"`
	Storages     []Storage `json:"storages"`
	ClusterType  string    `json:"cluster_type"`
	ImmuteDomain string    `json:"immute_domain"`
	BkCloudId    int       `json:"bk_cloud_id"`
}

// BkBizId 业务 id，QueryAccountRule、GetAllClustersInfo 函数的入参
type BkBizId struct {
	BkBizId int64 `json:"bk_biz_id" url:"bk_biz_id"`
}

type Biz struct {
	BkBizId     int64  `json:"bk_biz_id"`
	Name        string `json:"name"`
	EnglishName string `json:"english_name"`
	Permission  struct {
		DbManage bool `json:"db_manage"`
	} `json:"permission"`
}

type DownloadPara struct {
	TicketType string   `json:"ticket_type"`
	BkBizId    int64    `json:"bk_biz_id"`
	BkCloudId  int      `json:"bk_cloud_id"`
	DbType     string   `json:"db_type"`
	Ips        []string `json:"ips"`
	CreatedBy  string   `json:"created_by"`
}

type DownloadPartitionPara struct {
	TicketType string `json:"ticket_type"`
	BkBizId    int64  `json:"bk_biz_id"`
	Files      []Info `json:"files"`
	CreatedBy  string `json:"created_by"`
	Path       string `json:"path"`
}

// DownloadDbactor 下载dbactor
func DownloadDbactor(bkCloudId int, ips []string) error {
	url := "/apis/v1/flow/scene/download_dbactor"
	_, err := util.DbmetaClient.Do(http.MethodPost, url, DownloadPara{TicketType: "download_dbactor",
		BkBizId:   viper.GetInt64("dba.bk_biz_id"),
		BkCloudId: bkCloudId, DbType: "mysql", Ips: ips, CreatedBy: "admin"})
	if err != nil {
		slog.Error("msg", url, err)
		return errno.DownloadDbactorFail.Add(err.Error())
	}
	return nil
}

func DownloadFiles(files []Info) error {
	path := "mysql/partition"
	url := "/apis/v1/flow/scene/download_file"
	_, err := util.DbmetaClient.Do(http.MethodPost, url, DownloadPartitionPara{TicketType: "download_file",
		BkBizId: viper.GetInt64("dba.bk_biz_id"),
		Files:   files, CreatedBy: "admin", Path: path})
	if err != nil {
		slog.Error("msg", url, err)
		return errno.DownloadFileFail.Add(err.Error())
	}
	return nil
}

// GetCluster 根据域名获取集群信息
func GetCluster(dns Domain, ClusterType string) (Instance, error) {
	var resp Instance
	url := fmt.Sprintf("/apis/proxypass/dbmeta/priv_manager/mysql/%s/cluster_instances/", ClusterType)
	result, err := util.DbmetaClient.Do(http.MethodPost, url, dns)
	if err != nil {
		slog.Error("msg", url, err)
		return resp, errno.DomainNotExists.Add(fmt.Sprintf(" %s: %s", dns.EntryName, err.Error()))
	}
	if err = json.Unmarshal(result.Data, &resp); err != nil {
		slog.Error("msg", url, err)

		return resp, err
	}
	return resp, nil
}

// GetAllClustersInfo 获取业务下所有集群信息
func GetAllClustersInfo(id BkBizId) ([]Cluster, error) {
	var resp []Cluster
	url := "/apis/proxypass/dbmeta/priv_manager/biz_clusters/"
	result, err := util.DbmetaClient.Do(http.MethodPost, url, id)
	if err != nil {
		slog.Error("msg", url, err)
		return resp, err
	}
	if err = json.Unmarshal(result.Data, &resp); err != nil {
		slog.Error("msg", url, err)
		return resp, err
	}
	return resp, nil
}

func ListBizs() ([]Biz, error) {
	var resp []Biz
	url := "/apis/cmdb/list_bizs/"
	result, err := util.DbmetaClient.Do(http.MethodGet, url, nil)
	if err != nil {
		slog.Error("msg", url, err)
		return resp, err
	}
	if err = json.Unmarshal(result.Data, &resp); err != nil {
		slog.Error("msg", url, err)
		return resp, err
	}
	return resp, nil
}

/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
 * an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
 * specific language governing permissions and limitations under the License.
 */

package cron

import (
	"dbm-services/mysql/db-partition/util"
	"fmt"
	"log/slog"
	"sync"
	"time"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/db-partition/model"
	"dbm-services/mysql/db-partition/monitor"
	"dbm-services/mysql/db-partition/service"
)

// Scheduler TODO
var Scheduler string

// Run TODO
func (m PartitionJob) Run() {
	var err error
	var key string
	Scheduler = "127.0.0.1"
	offetSeconds := m.ZoneOffset * 60 * 60
	zone := time.FixedZone(m.ZoneName, offetSeconds)
	m.CronDate = time.Now().In(zone).Format("20060102")
	key = fmt.Sprintf("%s_%s_%d_%s", m.CronType, m.Hour, m.ZoneOffset, m.CronDate)
	flag, err := model.Lock(key)
	if err != nil {
		dimension := monitor.NewDeveloperEventDimension(Scheduler)
		content := fmt.Sprintf("partition error. set redis mutual exclusion error: %s", err.Error())
		monitor.SendEvent(monitor.PartitionDeveloperEvent, dimension, content, Scheduler)
		slog.Error("msg", "model.Lock err", err)
	} else if flag {
		m.ExecutePartition(service.Tendbha)
		m.ExecutePartition(service.Tendbcluster)
	} else {
		slog.Warn("set redis mutual exclusion fail, do nothing", "key", key)
	}
}

// ExecutePartition 执行业务的分区
func (m PartitionJob) ExecutePartition(clusterType string) {
	zone := fmt.Sprintf("%+03d:00", m.ZoneOffset)
	needMysql, errOuter := service.NeedPartition(m.CronType, clusterType, m.ZoneOffset, m.CronDate)
	if errOuter != nil {
		dimension := monitor.NewDeveloperEventDimension(Scheduler)
		content := fmt.Sprintf("partition error. get need partition list fail: %s", errOuter.Error())
		monitor.SendEvent(monitor.PartitionDeveloperEvent, dimension, content, Scheduler)
		slog.Error("msg", "get need partition list fail", errOuter)
		return
	}
	var UniqMap = make(map[int]struct{})
	var UniqMachine = make(map[string]struct{})
	var cloudMachineList = make(map[int64][]string)
	if clusterType != service.Tendbha && service.Tendbcluster != clusterType {
		slog.Error(fmt.Sprintf("cluster type %s not support", clusterType))
		return
	}

	for _, need := range needMysql {
		if _, isExists := UniqMap[need.BkBizId]; isExists == false {
			UniqMap[need.BkBizId] = struct{}{}
			clusters, err := service.GetAllClustersInfo(service.BkBizId{BkBizId: int64(need.BkBizId)})
			if err != nil {
				dimension := monitor.NewDeveloperEventDimension(Scheduler)
				content := fmt.Sprintf("partition error. "+
					"get cluster from dbmeta/priv_manager/biz_clusters error: %s", err.Error())
				monitor.SendEvent(monitor.PartitionDeveloperEvent, dimension, content, Scheduler)
				slog.Error("msg", "partition error. "+
					"get cluster from dbmeta/priv_manager/biz_clusters error", err)
				continue
			}
			for _, cluster := range clusters {
				if clusterType == service.Tendbha {
					for _, storage := range cluster.Storages {
						if storage.InstanceRole == service.Orphan || storage.InstanceRole == service.BackendMaster {
							if _, existFlag := UniqMachine[fmt.Sprintf("%s|%d",
								storage.IP, cluster.BkCloudId)]; existFlag == false {
								cloudMachineList[cluster.BkCloudId] = append(
									cloudMachineList[cluster.BkCloudId], storage.IP)
							}
						}
					}
				} else {
					for _, storage := range cluster.Storages {
						if storage.InstanceRole == service.RemoteMaster {
							if _, existFlag := UniqMachine[fmt.Sprintf("%s|%d",
								storage.IP, cluster.BkCloudId)]; existFlag == false {
								cloudMachineList[cluster.BkCloudId] = append(
									cloudMachineList[cluster.BkCloudId], storage.IP)
							}
						}
					}
				}
			}
		}
	}
	var wgDownload sync.WaitGroup
	tokenBucketDownload := make(chan int, 5)
	for cloud, machines := range cloudMachineList {
		tmp := util.SplitArray(machines, 20)
		for _, ips := range tmp {
			wgDownload.Add(1)
			tokenBucketDownload <- 0
			go func(cloud int64, ips []string) {
				defer func() {
					<-tokenBucketDownload
					wgDownload.Done()
				}()
				// 按照机器提前下载好dbactor，减少重复下次
				err := service.DownloadDbactor(cloud, ips)
				if err != nil {
					dimension := monitor.NewDeveloperEventDimension(Scheduler)
					content := fmt.Sprintf("%v download dbactor fail: %s", ips, err.Error())
					monitor.SendEvent(monitor.PartitionDeveloperEvent, dimension, content, Scheduler)
					slog.Error("msg", "download dbactor fail. "+
						"dbmeta/apis/v1/flow/scene/download_dbactor/ error", err)
					return
				}
				// 下发dbactor时间，避免造成瓶颈
				time.Sleep(2 * time.Minute)
			}(cloud, ips)
		}
	}
	wgDownload.Wait()
	close(tokenBucketDownload)

	var wg sync.WaitGroup
	tokenBucket := make(chan int, 10)
	for _, item := range needMysql {
		wg.Add(1)
		tokenBucket <- 0
		go func(item *service.Checker) {
			defer func() {
				<-tokenBucket
				wg.Done()
			}()
			item.FromCron = true
			objects, err := (*item).DryRun()
			if err != nil {
				code, _ := errno.DecodeErr(err)
				if code == errno.NothingToDo.Code {
					// 当天首次执行发现没有需要执行的sql，记录日志。重试没有执行的sql，不需要记录日志。
					if m.CronType == "daily" {
						_ = service.AddLog(item.ConfigId, item.BkBizId, item.ClusterId, *item.BkCloudId, 0,
							item.ImmuteDomain, zone, m.CronDate, Scheduler, errno.NothingToDo.Message, service.CheckSucceeded,
							item.ClusterType)
					}
				} else {
					dimension := monitor.NewPartitionEventDimension(item.BkBizId, item.DbAppAbbr, item.BkBizName,
						*item.BkCloudId, item.ImmuteDomain)
					content := fmt.Sprintf("partition error. get partition sql fail: %s", err.Error())
					monitor.SendEvent(monitor.PartitionEvent, dimension, content, "127.0.0.1")
					_ = service.AddLog(item.ConfigId, item.BkBizId, item.ClusterId, *item.BkCloudId, 0,
						item.ImmuteDomain, zone, m.CronDate, Scheduler, content, service.CheckFailed, item.ClusterType)
					slog.Error(fmt.Sprintf("%v", *item), "get partition sql fail", err)
				}
				return
			}
			slog.Info("do create partition ticket")
			service.CreatePartitionTicket(*item, objects, m.ZoneOffset, m.CronDate, Scheduler)
			time.Sleep(30 * time.Second)
		}(item)
	}
	wg.Wait()
	close(tokenBucket)
}

// ExecutePartitionOneTime 一次性调度
func (m PartitionJob) ExecutePartitionOneTime(clusterType string) {
	needMysql, errOuter := service.NeedPartition(m.CronType, clusterType, m.ZoneOffset, m.CronDate)
	if errOuter != nil {
		slog.Error("testtest", "get need partition list fail", errOuter)
		return
	}
	var UniqMap = make(map[int]struct{})
	var UniqMachine = make(map[string]struct{})
	var cloudMachineList = make(map[int64][]string)
	if clusterType != service.Tendbha && service.Tendbcluster != clusterType {
		slog.Error(fmt.Sprintf("cluster type %s not support", clusterType))
		return
	}

	for _, need := range needMysql {
		if _, isExists := UniqMap[need.BkBizId]; isExists == false {
			UniqMap[need.BkBizId] = struct{}{}
			clusters, err := service.GetAllClustersInfo(service.BkBizId{BkBizId: int64(need.BkBizId)})
			if err != nil {
				dimension := monitor.NewDeveloperEventDimension(Scheduler)
				content := fmt.Sprintf("partition error. "+
					"get cluster from dbmeta/priv_manager/biz_clusters error: %s", err.Error())
				monitor.SendEvent(monitor.PartitionDeveloperEvent, dimension, content, Scheduler)
				slog.Error("msg", "partition error. "+
					"get cluster from dbmeta/priv_manager/biz_clusters error", err)
				continue
			}
			for _, cluster := range clusters {
				if clusterType == service.Tendbha {
					for _, storage := range cluster.Storages {
						if storage.InstanceRole == service.Orphan || storage.InstanceRole == service.BackendMaster {
							if _, existFlag := UniqMachine[fmt.Sprintf("%s|%d",
								storage.IP, cluster.BkCloudId)]; existFlag == false {
								cloudMachineList[cluster.BkCloudId] = append(
									cloudMachineList[cluster.BkCloudId], storage.IP)
							}
						}
					}
				} else {
					for _, storage := range cluster.Storages {
						if storage.InstanceRole == service.RemoteMaster {
							if _, existFlag := UniqMachine[fmt.Sprintf("%s|%d",
								storage.IP, cluster.BkCloudId)]; existFlag == false {
								cloudMachineList[cluster.BkCloudId] = append(
									cloudMachineList[cluster.BkCloudId], storage.IP)
							}
						}
					}
				}
			}
		}
	}

	var wgDownload sync.WaitGroup
	tokenBucketDownload := make(chan int, 5)
	for cloud, machines := range cloudMachineList {
		tmp := util.SplitArray(machines, 20)
		for _, ips := range tmp {
			wgDownload.Add(1)
			tokenBucketDownload <- 0
			go func(cloud int64, ips []string) {
				defer func() {
					<-tokenBucketDownload
					wgDownload.Done()
				}()
				// 按照机器提前下载好dbactor，减少重复下次
				err := service.DownloadDbactor(cloud, ips)
				if err != nil {
					slog.Error("msg", "download dbactor fail. "+
						"dbmeta/apis/v1/flow/scene/download_dbactor error", err)
					return
				}
				// 下发dbactor时间，避免造成瓶颈
				time.Sleep(2 * time.Minute)
			}(cloud, ips)
		}
	}
	wgDownload.Wait()
	close(tokenBucketDownload)

	var wg sync.WaitGroup
	tokenBucket := make(chan int, 10)
	for _, item := range needMysql {
		wg.Add(1)
		tokenBucket <- 0
		go func(item *service.Checker) {
			defer func() {
				<-tokenBucket
				wg.Done()
			}()
			objects, err := (*item).DryRun()
			if err != nil {
				code, _ := errno.DecodeErr(err)
				if code != errno.NothingToDo.Code {
					slog.Error(fmt.Sprintf("%v", *item), "get partition sql fail", err)
				}
				return
			}
			slog.Info("do create partition ticket")
			service.CreatePartitionTicket(*item, objects, m.ZoneOffset, m.CronDate, Scheduler)
			time.Sleep(30 * time.Second)
		}(item)
	}
	wg.Wait()
	close(tokenBucket)
}

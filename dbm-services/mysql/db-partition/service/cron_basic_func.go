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
	"context"
	"dbm-services/mysql/db-partition/util"
	"encoding/json"
	"fmt"
	"log/slog"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	"golang.org/x/time/rate"

	"dbm-services/mysql/db-partition/model"
	"dbm-services/mysql/db-partition/monitor"
)

// Run 执行Job
func (m PartitionJob) Run() {
	var err error
	var key string
	offetSeconds := m.ZoneOffset * 60 * 60
	zone := time.FixedZone(m.ZoneName, offetSeconds)
	m.CronDate = time.Now().In(zone).Format("20060102")
	key = fmt.Sprintf("%s_%s_%d_%s", m.CronType, m.Hour, m.ZoneOffset, m.CronDate)
	flag, err := model.Lock(key)
	if err != nil {
		msg := "partition error. set redis mutual exclusion error"
		SendMonitor(msg, err)
		slog.Error("msg", msg, err)
	} else if flag {
		m.ExecuteTendbhaPartition()
		m.ExecuteTendbclusterPartition()
		if m.CronType == Alarm {
			// 巡检最近3天执行失败的或者未执行的
			CheckLogSendMonitor(Tendbha, m.CronDate)
			CheckLogSendMonitor(Tendbcluster, m.CronDate)
		}
	} else {
		slog.Warn("set redis mutual exclusion fail, do nothing", "key", key)
	}
}

// ExecuteTendbhaPartition 执行tendbha的分区
func (m PartitionJob) ExecuteTendbhaPartition() {
	slog.Info("do ExecuteTendbhaPartition")
	timeStr := time.Now().Format(time.RFC3339)
	needMysql, errOuter := NeedPartition(m.CronType, Tendbha, m.ZoneOffset, m.CronDate)
	if errOuter != nil {
		msg := "partition error. get need partition list fail"
		SendMonitor(msg, errOuter)
		slog.Error("msg", msg, errOuter)
		return
	}
	// 找到distinct业务distinct业务、distinct集群、集群和业务的所属关系、规则和集群的所属关系
	var uniqBiz = make(map[int64]struct{})
	fromCron := true
	for _, need := range needMysql {
		if _, isExists := uniqBiz[need.BkBizId]; isExists == false {
			uniqBiz[need.BkBizId] = struct{}{}
		}
	}
	// 规则属于哪个集群
	var clusterConfigs = make(map[int][]*PartitionConfig)
	for _, need := range needMysql {
		clusterConfigs[need.ClusterId] = append(clusterConfigs[need.ClusterId], need)
	}
	// 集群的主库实例
	master := make(map[int64]Host)
	// 集群的主库机器
	uniqHost := make(map[string][]int64)
	master, uniqHost, errOuter = GetHostAndMaster(uniqBiz)
	if errOuter != nil {
		return
	}
	slog.Info("msg", "master", master, "host", uniqHost)
	// 需要下载dbactor的机器
	var cloudMachineList = make(map[int64][]string)
	var machineFileName = make(map[string]string)
	for host, clusters := range uniqHost {
		tmp := strings.Split(host, "|")
		ip := tmp[0]
		cloud, _ := strconv.ParseInt(tmp[1], 10, 64)
		var objects []PartitionObject
		for _, cluster := range clusters {
			port := master[cluster].Port
			// 获取需要执行的分区语句，哪些分区规则不需要执行
			sqls, _, nothingToDo, err := CheckPartitionConfigs(clusterConfigs[int(cluster)], "mysql",
				1, fromCron, Host{Ip: ip, Port: port, BkCloudId: cloud})
			if err != nil {
				msg := "get partition sql fail"
				SendMonitor(msg, err)
				slog.Error("msg", msg, err)
				break
			}
			if len(sqls) > 0 {
				slog.Info("msg", "sql", sqls)
				objects = append(objects, PartitionObject{Ip: ip, Port: port, ShardName: "null",
					ExecuteObjects: sqls})
			}
			// 检查不需要执行语句，记录的分区日志中
			if len(nothingToDo) > 0 {
				err = AddLogBatch(nothingToDo, m.CronDate, Scheduler,
					"nothing to do", Success, Tendbha)
				if err != nil {
					msg := "add log fail"
					SendMonitor(msg, err)
					slog.Error("msg", msg, err)
					break
				}
			}
		}
		if len(objects) == 0 {
			continue
		}
		slog.Info("msg", "objects", objects)
		filename := fmt.Sprintf("partition_%s_%s_%s_%s.json", ip, m.CronDate, m.CronType, timeStr)
		err := UploadObejct(objects, filename)
		if err != nil {
			continue
		}
		cloudMachineList[cloud] = append(cloudMachineList[cloud], ip)
		machineFileName[host] = filename
		slog.Info("machineFileName", "host", host, "filename", filename)
	}
	slog.Info("test", "cloudMachineList", cloudMachineList, "machineFileName", machineFileName)
	DownLoadFilesCreateTicketByMachine(cloudMachineList, machineFileName, Tendbha, m.CronDate)
}

// ExecuteTendbclusterPartition 执行tendbcluster的分区
func (m PartitionJob) ExecuteTendbclusterPartition() {
	slog.Info("do ExecuteTendbclusterPartition")
	fromCron := true
	timeStr := time.Now().Format(time.RFC3339)
	needMysql, errOuter := NeedPartition(m.CronType, Tendbcluster, m.ZoneOffset, m.CronDate)
	if errOuter != nil {
		msg := "partition error. get need partition list fail"
		SendMonitor(msg, errOuter)
		slog.Error("msg", msg, errOuter)
		return
	}
	// 规则属于哪个集群
	var clusterConfigs = make(map[string][]*PartitionConfig)
	for _, need := range needMysql {
		cluster := fmt.Sprintf("%s|%d|%d", need.ImmuteDomain, need.Port, need.BkCloudId)
		clusterConfigs[cluster] = append(clusterConfigs[cluster], need)
	}
	// 需要下载dbactor的机器
	var machineFileName = make(map[string]string)
	var clusterIps = make(map[string][]string)
	for cluster := range clusterConfigs {
		// 获取集群结构
		hostNodes, splitCnt, err := GetTendbclusterInstances(cluster)
		if err != nil {
			msg := fmt.Sprintf("get tendbcluster %s nodes error", cluster)
			SendMonitor(msg, err)
			slog.Error("msg", msg, err)
			continue
		}
		slog.Info("spider struct", "hostNodes", hostNodes, "splitCnt", splitCnt)
		var nothing []PartitionConfig
		var doSomething []PartitionConfig
		var objects []PartitionObject
		configs := clusterConfigs[cluster]
		for host, instances := range hostNodes {
			tmp := strings.Split(host, "|")
			ip := tmp[0]
			for _, ins := range instances {
				newconfigs := make([]*PartitionConfig, len(configs))
				for k, v := range configs {
					newconfig := *v
					if ins.Wrapper == "mysql" {
						newconfig.DbLike = fmt.Sprintf("%s_%s", newconfig.DbLike, ins.SplitNum)
					}
					newconfigs[k] = &newconfig
				}
				// 获取一个集群中的一个实例需要执行的所有分区语句
				sqls, do, nothingToDo, errInner := CheckPartitionConfigs(newconfigs, ins.Wrapper,
					splitCnt, fromCron, Host{Ip: ins.Ip, Port: ins.Port, BkCloudId: int64(ins.Cloud)})
				if errInner != nil {
					msg := "get partition sql fail"
					SendMonitor(msg, errInner)
					slog.Error("msg", msg, errInner)
					break
				}
				if len(sqls) > 0 {
					objects = append(objects, PartitionObject{Ip: ins.Ip, Port: ins.Port, ShardName: ins.ServerName,
						ExecuteObjects: sqls})
				}
				nothing = append(nothing, nothingToDo...)
				doSomething = append(doSomething, do...)
			}
			// 需要执行的规则与不需要执行的均记录到日志中，即使记录日志失败，仍然继续执行分区
			NeedExecuteList(doSomething, nothing, m.CronDate, Tendbcluster)
			if len(objects) == 0 {
				continue
			}
			filename := fmt.Sprintf("partition_%s_%s_%s_%s.json", ip, m.CronDate, m.CronType, timeStr)
			err = UploadObejct(objects, filename)
			if err != nil {
				continue
			}
			clusterIps[cluster] = append(clusterIps[cluster], ip)
			machineFileName[host] = filename
			slog.Info("clusterIps", "cluster", cluster, "ip", ip)
			slog.Info("machineFileName", "host", host, "filename", filename)
		}
		slog.Info("test", "cloudMachineList", clusterIps, "machineFileName", machineFileName)
	}
	DownLoadFilesCreateTicketByCluster(clusterIps, machineFileName, Tendbcluster, m.CronDate)
}

// NeedExecuteList spider集群需要多个节点在执行分区规则，只有所有节点均不需要执行sql，才不不需要下发分区任务
func NeedExecuteList(doSomething []PartitionConfig, nothing []PartitionConfig, vdate, clusterType string) {
	var uniq = make(map[int]struct{})
	var doList []PartitionConfig
	var doIds []int
	var uniqNothing = make(map[int]struct{})
	var nothingList []PartitionConfig

	for _, item := range doSomething {
		if _, isExists := uniq[item.ID]; isExists == false {
			uniq[item.ID] = struct{}{}
			doList = append(doList, item)
			doIds = append(doIds, item.ID)
		}
	}
	for _, item := range nothing {
		if _, isExists := uniqNothing[item.ID]; isExists == false {
			uniqNothing[item.ID] = struct{}{}
			if !util.HasElem(item.ID, doIds) {
				nothingList = append(nothingList, item)
			}
		}
	}
	err := AddLogBatch(nothingList, vdate, Scheduler, "nothing to do", Success, clusterType)
	if err != nil {
		msg := "add log fail"
		SendMonitor(msg, err)
		slog.Error("msg", msg, err)
	}
}

// UploadObejct 分区结构转换为文件上传到介质中心
func UploadObejct(objects []PartitionObject, filename string) error {
	err := ObjectToFile(objects, filename)
	if err != nil {
		msg := fmt.Sprintf("object to file %s fail", filename)
		SendMonitor(msg, err)
		slog.Error("msg", msg, err)
		return err
	}
	// 上传到介质中心
	resp, err := UploadDirectToBkRepo(filename)
	if err != nil {
		msg := fmt.Sprintf("upload %s to bkrepo error", filename)
		SendMonitor(msg, err)
		slog.Error("msg", msg, err)
		return err
	}
	if resp.Code != 0 {
		msg := fmt.Sprintf(
			"upload %s to bkrepo respone error. respone code is %d,respone msg:%s,traceId:%s",
			filename,
			resp.Code,
			resp.Message,
			resp.RequestId,
		)
		SendMonitor(msg, fmt.Errorf("upload error"))
		slog.Error("msg", msg)
		return fmt.Errorf("upload error")
	}
	_ = os.Remove(filename)
	return nil
}

// GetHostAndMaster 获取tendbha主实例和主实例所在的机器
func GetHostAndMaster(uniqBiz map[int64]struct{}) (map[int64]Host, map[string][]int64, error) {
	var master = make(map[int64]Host)
	var uniqHost = make(map[string][]int64)
	for biz := range uniqBiz {
		clusters, err := GetAllClustersInfo(BkBizId{BkBizId: biz})
		if err != nil {
			msg := "get cluster from dbmeta/priv_manager/biz_clusters error"
			SendMonitor(msg, err)
			slog.Error("msg", msg, err)
			return nil, nil, err
		}
		for _, cluster := range clusters {
			if cluster.ClusterType == Tendbha || cluster.ClusterType == Tendbsingle {
				for _, storage := range cluster.Storages {
					if storage.InstanceRole == Orphan || storage.InstanceRole == BackendMaster {
						master[cluster.Id] = Host{Ip: storage.IP, Port: storage.Port, BkCloudId: cluster.BkCloudId}
						tmp := fmt.Sprintf("%s|%d", storage.IP, cluster.BkCloudId)
						uniqHost[tmp] = append(uniqHost[tmp], cluster.Id)
						break
					}
				}
			}
		}
	}
	return master, uniqHost, nil
}

// GetTendbclusterInstances 获取tendbcluster中的节点
func GetTendbclusterInstances(cluster string) (map[string][]SpiderNode, int, error) {
	tmp := strings.Split(cluster, "|")
	domain := tmp[0]
	port, _ := strconv.ParseInt(tmp[1], 10, 64)
	cloud, _ := strconv.Atoi(tmp[2])
	address := fmt.Sprintf("%s:%d", domain, port)
	var splitCnt int
	var tdbctlPrimary string
	// 查询tdbctl
	dbctlSql := "select HOST,PORT,server_name as SPLIT_NUM, SERVER_NAME, WRAPPER from mysql.servers " +
		"where wrapper='TDBCTL' and server_name like 'TDBCTL%' ;"
	getTdbctlPrimary := "tdbctl get primary;"
	queryRequest := QueryRequest{Addresses: []string{address}, Cmds: []string{dbctlSql}, Force: true, QueryTimeout: 30,
		BkCloudId: cloud}
	output, err := OneAddressExecuteSql(queryRequest)
	if err != nil {
		return nil, splitCnt, fmt.Errorf("execute [%s] get spider info error: %s", dbctlSql, err.Error())
	} else if len(output.CmdResults[0].TableData) == 0 {
		return nil, splitCnt, fmt.Errorf("no spider tdbctl found")
	}

	// 查询tdbctl主节点
	for _, item := range output.CmdResults[0].TableData {
		tdbctl := fmt.Sprintf("%s:%s", item["HOST"].(string), item["PORT"].(string))
		queryRequest = QueryRequest{Addresses: []string{tdbctl}, Cmds: []string{getTdbctlPrimary}, Force: true,
			QueryTimeout: 30, BkCloudId: cloud}
		primary, err := OneAddressExecuteSql(queryRequest)
		if err != nil {
			slog.Warn(fmt.Sprintf("execute [%s] error: %s", getTdbctlPrimary, err.Error()))
			continue
		}
		if len(primary.CmdResults[0].TableData) == 0 {
			slog.Error(fmt.Sprintf("execute [%s] nothing return", getTdbctlPrimary))
			return nil, splitCnt, fmt.Errorf("execute [%s] nothing return", getTdbctlPrimary)
		}
		slog.Info("data:", primary.CmdResults[0].TableData)
		tdbctlPrimary = primary.CmdResults[0].TableData[0]["SERVER_NAME"].(string)
		break
	}
	if tdbctlPrimary == "" {
		slog.Error(fmt.Sprintf("execute [%s] SERVER_NAME is null", getTdbctlPrimary))
		return nil, splitCnt, fmt.Errorf("execute [%s] SERVER_NAME is null", getTdbctlPrimary)
	}
	// 查询remote master各分片实例和tdbctl主节点
	splitSql := fmt.Sprintf("select HOST,PORT,replace(server_name,'SPT','') as SPLIT_NUM, SERVER_NAME, WRAPPER "+
		"from mysql.servers where wrapper in ('mysql','TDBCTL') and "+
		"(server_name like 'SPT%%' or server_name like '%s')", tdbctlPrimary)
	queryRequest = QueryRequest{Addresses: []string{address}, Cmds: []string{splitSql}, Force: true, QueryTimeout: 30,
		BkCloudId: cloud}
	output, err = OneAddressExecuteSql(queryRequest)
	if err != nil {
		return nil, splitCnt, fmt.Errorf("execute [%s] get spider remote and tdbctl master error: %s", splitSql, err.Error())
	}
	// 查询一台remote机器上有多少个实例，用于评估存储空间
	cntSql := "select count(*) as COUNT from mysql.servers where WRAPPER='mysql' and " +
		"SERVER_NAME like 'SPT%' group by host order by 1 desc limit 1;"
	queryRequest = QueryRequest{Addresses: []string{address}, Cmds: []string{cntSql}, Force: true, QueryTimeout: 30,
		BkCloudId: cloud}
	output1, err := OneAddressExecuteSql(queryRequest)
	if err != nil {
		return nil, splitCnt, fmt.Errorf("execute [%s] get spider split count error: %s", cntSql, err.Error())
	}
	splitCnt, _ = strconv.Atoi(output1.CmdResults[0].TableData[0]["COUNT"].(string))
	var hostNodes = make(map[string][]SpiderNode)
	for _, item := range output.CmdResults[0].TableData {
		vip := item["HOST"].(string)
		vport, _ := strconv.Atoi(item["PORT"].(string))
		vslitnum := item["SPLIT_NUM"].(string)
		wrapper := item["WRAPPER"].(string)
		serverName := item["SERVER_NAME"].(string)
		vhost := fmt.Sprintf("%s|%d", vip, cloud)
		hostNodes[vhost] = append(hostNodes[vhost], SpiderNode{vip, vport,
			cloud, vslitnum, wrapper, serverName})
	}
	return hostNodes, splitCnt, nil
}

// DownLoadFilesCreateTicketByMachine tendbha按照机器粒度下载文件、创建分区单据
func DownLoadFilesCreateTicketByMachine(cloudMachineList map[int64][]string, machineFileName map[string]string,
	clusterType string, vdate string) {
	var wg sync.WaitGroup
	limit := rate.Every(time.Second * 20)
	burst := 5 // 桶容量 5
	limiter := rate.NewLimiter(limit, burst)

	for cloud, machines := range cloudMachineList {
		tmp := util.SplitArray(machines, 20)
		for _, ips := range tmp {
			wg.Add(1)
			go func(cloud int64, ips []string) {
				defer func() {
					wg.Done()
				}()
				err := limiter.Wait(context.Background())
				if err != nil {
					msg := "dbmeta/apis/v1/flow/scene/download_dbactor/ error"
					SendMonitor(msg, err)
					slog.Error("msg", msg, err)
					return
				}
				// 按照机器下载好dbactor
				err = DownloadDbactor(cloud, ips)
				// dbactor下载失败，可以继续执行分区的单据，机器上可能已经存在dbactor
				if err != nil {
					dimension := monitor.NewDeveloperEventDimension(Scheduler, monitor.PartitionCron)
					content := fmt.Sprintf("%v download dbactor fail: %s", ips, err.Error())
					monitor.SendEvent(dimension, content, Scheduler)
					slog.Error("msg", "download dbactor fail. "+
						"dbmeta/apis/v1/flow/scene/download_dbactor/ error", err)
				}
				var files []Info
				for _, ip := range ips {
					files = append(files, Info{BkCloudId: cloud, Ip: ip,
						FileName: machineFileName[fmt.Sprintf("%s|%d", ip, cloud)]})
				}
				// 下载分区文件
				err = DownloadFiles(files)
				if err != nil {
					msg := "download partition file error"
					SendMonitor(msg, err)
					slog.Error("msg", msg, err)
					return
				}
				time.Sleep(60 * time.Second)
				// 创建执行分区单据
				err = CreatePartitionTicket(files, clusterType, "mixed", vdate)
				if err != nil {
					msg := "create ticket error"
					SendMonitor(msg, err)
					slog.Error("msg", msg, err)
					return
				}
			}(cloud, ips)
		}
	}
	wg.Wait()
}

// DownLoadFilesCreateTicketByCluster tendbcluster按照集群粒度下载文件，执行分区规则
func DownLoadFilesCreateTicketByCluster(clusterIps map[string][]string, machineFileName map[string]string,
	clusterType string, vdate string) {
	var wg sync.WaitGroup
	limit := rate.Every(time.Second * 20)
	burst := 5 // 桶容量 5
	limiter := rate.NewLimiter(limit, burst)

	for cluster, machines := range clusterIps {
		vcluster := strings.Split(cluster, "|")
		domain := vcluster[0]
		cloud, _ := strconv.Atoi(vcluster[2])
		wg.Add(1)
		var clusterFiles []Info
		go func(domain string, cloud int, machines []string) {
			defer func() {
				wg.Done()
			}()
			err := limiter.Wait(context.Background())
			if err != nil {
				msg := "get token error"
				SendMonitor(msg, err)
				slog.Error("msg", msg, err)
				return
			}
			tmp := util.SplitArray(machines, 20)
			for _, ips := range tmp {
				// 按照机器下载好dbactor
				err = DownloadDbactor(int64(cloud), ips)
				// dbactor下载失败，可以继续执行分区的单据，机器上可能已经存在dbactor
				if err != nil {
					dimension := monitor.NewDeveloperEventDimension(Scheduler, monitor.PartitionCron)
					content := fmt.Sprintf("%v download dbactor fail: %s", ips, err.Error())
					monitor.SendEvent(dimension, content, Scheduler)
					slog.Error("msg", "download dbactor fail. "+
						"dbmeta/apis/v1/flow/scene/download_dbactor/ error", err)
				}
				var files []Info
				for _, ip := range ips {
					files = append(files, Info{BkCloudId: int64(cloud), Ip: ip,
						FileName: machineFileName[fmt.Sprintf("%s|%d", ip, cloud)]})
				}
				// 下载分区文件
				err = DownloadFiles(files)
				if err != nil {
					msg := "download partition file error"
					SendMonitor(msg, err)
					slog.Error("msg", msg, err)
					return
				}
				clusterFiles = append(clusterFiles, files...)
			}
			time.Sleep(60 * time.Second)
			// 创建执行分区单据
			err = CreatePartitionTicket(clusterFiles, clusterType, domain, vdate)
			if err != nil {
				msg := "create ticket error"
				SendMonitor(msg, err)
				slog.Error("msg", msg, err)
				return
			}
		}(domain, cloud, machines)
	}
	wg.Wait()
}

// SendMonitor 发送日志
func SendMonitor(msg string, err error) {
	dimension := monitor.NewDeveloperEventDimension(Scheduler, monitor.PartitionCron)
	content := fmt.Sprintf("%s: %s", msg, err.Error())
	monitor.SendEvent(dimension, content, Scheduler)
}

// ObjectToFile 分区结构体转换为文件
func ObjectToFile(objects []PartitionObject, filename string) error {
	b, err := json.Marshal(objects)
	if err != nil {
		msg := "json.Marshal error"
		SendMonitor(msg, err)
		slog.Error("msg", msg, err)
		return err
	}
	inputFile, err := os.OpenFile(filename,
		os.O_CREATE|os.O_RDWR, 0644)
	if err != nil {
		msg := fmt.Sprintf("create file %s error", filename)
		SendMonitor(msg, err)
		slog.Error("msg", msg, err)
		return err
	}
	if _, err = inputFile.Write(b); err != nil {
		_ = inputFile.Close()
		_ = os.Remove(filename)
		msg := fmt.Sprintf("write file %s error", filename)
		SendMonitor(msg, err)
		slog.Error("msg", msg, err)
		return err
	}
	return nil
}

// CheckLogSendMonitor 检查分区日志，连续多少天失败或者没有执行，告知平台负责人
func CheckLogSendMonitor(clusterType string, cronDate string) {
	// 判断是mysql集群还是spider集群
	var tb, log string
	switch clusterType {
	case Tendbha, Tendbsingle:
		tb = MysqlPartitionConfig
		log = MysqlPartitionCronLogTable
	case Tendbcluster:
		tb = SpiderPartitionConfig
		log = SpiderPartitionCronLogTable
	default:
		return
	}

	// 查到所有的规则，去除近xxx天曾经成功执行过的分区规则，其余告警
	var all []*PartitionConfig
	var faildays []PartitionConfig
	continueDays := 7
	err := model.DB.Self.Table(tb).Where(fmt.Sprintf(
		"phase in (?,?) and create_time> date_sub(now(), interval %d day)", continueDays),
		online, offline).Scan(&all).Error
	if err != nil {
		msg := "send monitor error. get partition configs error"
		SendMonitor(msg, err)
		slog.Error("msg", msg, err)
		return
	}
	type Ids struct {
		ID int `json:"id" gorm:"column:id;primary_key;auto_increment"`
	}
	var succeeded []*Ids
	vsql := fmt.Sprintf("select distinct(id) as id from %s where status like '%s' "+
		"and cron_date > date_sub(now(), interval %d day)", log, Success, continueDays)
	err = model.DB.Self.Raw(vsql).Scan(&succeeded).Error
	if err != nil {
		msg := "send monitor error. get partition logs error"
		SendMonitor(msg, err)
		slog.Error("msg", msg, err)
		return
	}
	var clusterTable = make(map[string]string)
	var uniqCluster = make(map[string]struct{})

	for _, item := range all {
		failFlag := true
		for _, ok := range succeeded {
			if (*item).ID == (*ok).ID {
				failFlag = false
				break
			}
		}
		if failFlag == true {
			clusterTable[item.ImmuteDomain] = fmt.Sprintf("%s[%s.%s]", clusterTable[item.ImmuteDomain],
				item.DbLike, item.TbLike)
			if _, isExists := uniqCluster[item.ImmuteDomain]; isExists == false {
				uniqCluster[item.ImmuteDomain] = struct{}{}
			}
			faildays = append(faildays, *item)
		}
	}
	err = AddLogBatch(faildays, cronDate, Scheduler,
		fmt.Sprintf("partition failed or not be run for %d days", continueDays), Fail, clusterType)
	if err != nil {
		msg := "add log fail"
		SendMonitor(msg, err)
		slog.Error("msg", msg, err)
	}
	for domain := range uniqCluster {
		content := fmt.Sprintf("partition failed for %d days: %s", continueDays, clusterTable[domain])
		dimension := monitor.NewDeveloperEventDimension(Scheduler, domain)
		slog.Info("monitor", "content", content, "dimension", dimension)
		monitor.SendEvent(dimension, content, Scheduler)
	}
}

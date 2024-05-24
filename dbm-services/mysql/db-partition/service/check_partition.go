package service

import (
	"context"
	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/db-partition/model"
	"errors"
	"fmt"
	"log/slog"
	"strings"
	"sync"
	"time"

	"golang.org/x/time/rate"
)

// DryRun 生成分区sql，页面展示
func (m *Checker) DryRun() ([]PartitionObject, error) {
	slog.Info("do service DryRun")
	var objects []PartitionObject
	var errOuter error
	if m.BkBizId == 0 {
		return objects, errno.BkBizIdIsEmpty
	}
	if m.ClusterId == 0 {
		return objects, errno.ClusterIdIsEmpty
	}
	if m.BkCloudId == nil {
		return objects, errno.CloudIdRequired
	}
	if m.ConfigId == 0 {
		return objects, errno.RuleIdNull
	}
	var configs []*PartitionConfig
	var tbName string
	switch m.ClusterType {
	case Tendbha, Tendbsingle:
		tbName = MysqlPartitionConfig
	case Tendbcluster:
		tbName = SpiderPartitionConfig
	default:
		slog.Error(m.ClusterType, "error", errno.NotSupportedClusterType.Error())
		return objects, errno.NotSupportedClusterType
	}
	errOuter = model.DB.Self.Table(tbName).Where("bk_biz_id = ? and cluster_id = ? and id = ?", m.BkBizId, m.ClusterId,
		m.ConfigId).Scan(&configs).Error
	if errOuter != nil {
		slog.Error("msg", fmt.Sprintf("query %s err", tbName), errOuter)
		return objects, errOuter
	}
	if len(configs) == 0 {
		return objects, errno.PartitionConfigNotExisted
	}

	slog.Info(fmt.Sprintf("configs:%v", configs))
	switch m.ClusterType {
	case Tendbha, Tendbsingle:
		ins, err := GetMaster(m.ImmuteDomain, m.ClusterType)
		if err != nil {
			slog.Error("msg", "GetClusterMasterError", err)
			return objects, err
		}
		sqls, _, _, err := CheckPartitionConfigs(configs, "mysql",
			1, false, Host{Ip: ins.Ip, Port: ins.Port, BkCloudId: ins.BkCloudId})
		if err != nil {
			slog.Error("msg", "CheckPartitionConfigs", err)
			return objects, errno.GetPartitionSqlFail.Add(fmt.Sprintf("%s:%d\n%s", ins.Ip,
				ins.Port, err.Error()))
		}
		if len(sqls) == 0 {
			return objects, errno.NothingToDo
		}
		objects = append(objects, PartitionObject{Ip: ins.Ip, Port: ins.Port, ShardName: "null",
			ExecuteObjects: sqls})
	case Tendbcluster:
		cluster := fmt.Sprintf("%s|%d|%d", m.ImmuteDomain, m.Port, m.BkCloudId)
		hostNodes, splitCnt, err := GetTendbclusterInstances(cluster)
		if err != nil {
			slog.Error("msg", "GetTendbclusterInstances", err)
			return objects, err
		}
		for _, instances := range hostNodes {
			for _, ins := range instances {
				newconfigs := make([]*PartitionConfig, len(configs))
				for k, v := range configs {
					newconfig := *v
					if ins.Wrapper == "mysql" {
						newconfig.DbLike = fmt.Sprintf("%s_%s", newconfig.DbLike, ins.SplitNum)
					}
					newconfigs[k] = &newconfig
				}
				sqls, _, _, errInner := CheckPartitionConfigs(newconfigs, ins.Wrapper,
					splitCnt, false, Host{Ip: ins.Ip, Port: ins.Port, BkCloudId: int64(ins.Cloud)})
				if errInner != nil {
					slog.Error("msg", "CheckPartitionConfigs", err)
					return objects, errno.GetPartitionSqlFail.Add(fmt.Sprintf("%s:%d\n%s", ins.Ip,
						ins.Port, errInner.Error()))
				}
				if len(sqls) == 0 {
					continue
				}
				objects = append(objects, PartitionObject{Ip: ins.Ip, Port: ins.Port, ShardName: ins.ServerName,
					ExecuteObjects: sqls})
			}
		}
		if len(objects) == 0 {
			return objects, errno.NothingToDo
		}
	default:
		slog.Error(m.ClusterType, "error", errors.New("not supported db type"))
		return objects, errno.NotSupportedClusterType
	}
	return objects, nil
}

/*
// CheckSpiderPartitionConfigs TODO
func (m *Checker) CheckSpiderPartitionConfigs(configs []*PartitionConfig) ([]PartitionObject, error) {
	fmt.Printf("do CheckSpiderPartitionConfigs")

	address := fmt.Sprintf("%s:%d", m.ImmuteDomain, m.Port)
	backends, splitCnt, err := GetSpiderBackends(address, *m.BkCloudId)
	if err != nil {
		return nil, err
	}
	var all []PartitionObject
	for _, item := range backends {
		newconfigs := make([]*PartitionConfig, len(configs))
		host := item["HOST"].(string)
		port, _ := strconv.Atoi(item["PORT"].(string))
		for k, v := range configs {
			newconfig := *v
			newconfig.ImmuteDomain = host
			newconfig.Port = port
			if item["WRAPPER"] == "mysql" {
				newconfig.DbLike = fmt.Sprintf("%s_%s", newconfig.DbLike, item["SPLIT_NUM"].(string))
			}
			newconfigs[k] = &newconfig
		}
		execute, err := CheckPartitionConfigs(newconfigs, item["WRAPPER"].(string), splitCnt, m.FromCron)
		if err != nil {
			slog.Error("msg", "CheckPartitionConfigs", err)
			return all, errno.GetPartitionSqlFail.Add(fmt.Sprintf("spit%s %s:%s\n%s", item["SPLIT_NUM"], item["HOST"],
				item["PORT"], err.Error()))
		}
		all = append(all, PartitionObject{host, port, item["SERVER_NAME"].(string), execute})
	}
	return all, nil
}
*/

// CheckPartitionConfigs TODO
func CheckPartitionConfigs(configs []*PartitionConfig, dbtype string, splitCnt int, fromCron bool, host Host) ([]PartitionSql,
	[]PartitionConfig, []PartitionConfig, error) {
	fmt.Printf("do CheckPartitionConfigs")
	var errMsg Messages
	sqlSet := PartitionSqlSet{}
	nothingToDoSet := ConfigSet{}
	wg := sync.WaitGroup{}
	limit := rate.Every(time.Millisecond * 200) // QPS：5
	burst := 10                                 // 桶容量 10
	limiter := rate.NewLimiter(limit, burst)
	for _, config := range configs {
		wg.Add(1)
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		go func(config *PartitionConfig) {
			err := limiter.Wait(context.Background())
			if err != nil {
				errMsg.mu.Lock()
				errMsg.list = append(errMsg.list, err.Error())
				errMsg.mu.Unlock()
				return
			}
			slog.Info(fmt.Sprintf("%s:%v", "CheckOnePartitionConfig", config))
			err = CheckOnePartitionConfig(ctx, cancel, *config, &wg, &sqlSet, &nothingToDoSet, dbtype, splitCnt,
				fromCron, host)
			if err != nil {
				errMsg.mu.Lock()
				errMsg.list = append(errMsg.list, err.Error())
				errMsg.mu.Unlock()
			}
		}(config)
	}
	wg.Wait()
	if len(errMsg.list) > 0 {
		return sqlSet.PartitionSqls, sqlSet.Configs, nothingToDoSet.Configs, fmt.Errorf(strings.Join(errMsg.list, "\n"))
	}
	return sqlSet.PartitionSqls, sqlSet.Configs, nothingToDoSet.Configs, nil
}

// CheckOnePartitionConfig TODO
func CheckOnePartitionConfig(ctx context.Context, cancel context.CancelFunc, config PartitionConfig,
	wg *sync.WaitGroup, sqlSet *PartitionSqlSet, nothingToDoSet *ConfigSet,
	dbtype string, splitCnt int, fromCron bool, host Host) error {
	fmt.Printf("do CheckOnePartitionConfig")
	var addSql, dropSql []string
	var err error
	var initSql []InitSql
	defer func() {
		wg.Done()
		cancel()
	}()

	finish := make(chan int, 1)
	errorChan := make(chan error, 1)
	go func() {
		defer func() {
			finish <- 1
		}()
		initSql, addSql, dropSql, err = config.GetPartitionDbLikeTbLike(dbtype, splitCnt, fromCron, host)
		if err != nil {
			errorChan <- err
			return
		}

		if len(addSql) != 0 || len(dropSql) != 0 || len(initSql) != 0 {
			sqlSet.Mu.Lock()
			sqlSet.PartitionSqls = append(sqlSet.PartitionSqls, PartitionSql{config.ID, config.DbLike, config.TbLike, initSql,
				addSql, dropSql})
			sqlSet.Configs = append(sqlSet.Configs, config)
			sqlSet.Mu.Unlock()
		} else {
			// 集群没有需要执行的分区语句并且在获取分区语句时没有错误
			nothingToDoSet.Mu.Lock()
			nothingToDoSet.Configs = append(nothingToDoSet.Configs, config)
			nothingToDoSet.Mu.Unlock()
		}
		return
	}()

	select {
	case <-finish:
		return nil
	case errOuter := <-errorChan:
		return errOuter
	case <-ctx.Done():
		errOuter := fmt.Errorf("partition rule: [dblike:`%s` tblike:`%s`] get partition sql timeout",
			config.DbLike, config.TbLike)
		return errOuter
	}
}

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
		cluster := fmt.Sprintf("%s|%d|%d", m.ImmuteDomain, m.Port, *m.BkCloudId)
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
					splitCnt, false, Host{Ip: ins.Ip, Port: ins.Port, BkCloudId: ins.Cloud})
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

// CheckPartitionConfigs 检查一批分区规则是否需要执行，生成分区语句
func CheckPartitionConfigs(configs []*PartitionConfig, dbtype string, splitCnt int, fromCron bool, host Host) ([]PartitionSql,
	[]IdLog, []IdLog, error) {
	fmt.Printf("do CheckPartitionConfigs")
	sqlSet := PartitionSqlSet{}
	nothingToDoSet := ConfigIdLogSet{}
	checkFailSet := ConfigIdLogSet{}
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
				checkFailSet.Mu.Lock()
				checkFailSet.IdLogs = append(checkFailSet.IdLogs, IdLog{(*config).ID, err.Error()})
				checkFailSet.Mu.Unlock()
				return
			}
			CheckOnePartitionConfig(ctx, cancel, *config, &wg, &sqlSet, &nothingToDoSet, &checkFailSet, dbtype, splitCnt,
				fromCron, host)
		}(config)
	}
	wg.Wait()
	if len(checkFailSet.IdLogs) > 0 {
		var msg string
		for _, log := range checkFailSet.IdLogs {
			msg = fmt.Sprintf("%s\n%s", msg, log.Log)
		}
		msg = strings.TrimPrefix(msg, "\n")
		return sqlSet.PartitionSqls, nothingToDoSet.IdLogs, checkFailSet.IdLogs, fmt.Errorf(msg)
	}
	return sqlSet.PartitionSqls, nothingToDoSet.IdLogs, checkFailSet.IdLogs, nil
}

// CheckOnePartitionConfig 检查一个分区规则是否需要执行，生成分区语句
func CheckOnePartitionConfig(ctx context.Context, cancel context.CancelFunc, config PartitionConfig,
	wg *sync.WaitGroup, sqlSet *PartitionSqlSet, nothingToDoSet *ConfigIdLogSet, checkFailSet *ConfigIdLogSet,
	dbtype string, splitCnt int, fromCron bool, host Host) {
	fmt.Printf("do CheckOnePartitionConfig")
	var addSql, dropSql []string
	var err error
	var initSql []InitSql
	defer func() {
		wg.Done()
		cancel()
	}()

	finish := make(chan int, 1)
	go func() {
		defer func() {
			finish <- 1
		}()
		initSql, addSql, dropSql, err = config.GetPartitionDbLikeTbLike(dbtype, splitCnt, fromCron, host)
		if err != nil {
			checkFailSet.Mu.Lock()
			checkFailSet.IdLogs = append(checkFailSet.IdLogs, IdLog{ConfigId: config.ID, Log: err.Error()})
			checkFailSet.Mu.Unlock()
			return
		}
		if len(addSql) != 0 || len(dropSql) != 0 || len(initSql) != 0 {
			sqlSet.Mu.Lock()
			sqlSet.PartitionSqls = append(sqlSet.PartitionSqls, PartitionSql{config.ID, config.DbLike, config.TbLike, initSql,
				addSql, dropSql})
			sqlSet.Mu.Unlock()
		} else {
			// 集群没有需要执行的分区语句并且在获取分区语句时没有错误
			nothingToDoSet.Mu.Lock()
			nothingToDoSet.IdLogs = append(nothingToDoSet.IdLogs, IdLog{ConfigId: config.ID})
			nothingToDoSet.Mu.Unlock()
		}
		return
	}()

	select {
	case <-finish:
		return
	case <-ctx.Done():
		checkFailSet.Mu.Lock()
		checkFailSet.IdLogs = append(checkFailSet.IdLogs, IdLog{ConfigId: config.ID,
			Log: fmt.Sprintf("partition rule: [dblike:`%s` tblike:`%s`] get partition sql timeout",
				config.DbLike, config.TbLike)})
		checkFailSet.Mu.Unlock()
		return
	}
}

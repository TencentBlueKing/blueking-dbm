package service

import (
	"context"
	"errors"
	"fmt"
	"strconv"
	"strings"
	"sync"
	"time"

	"dbm-services/common/go-pubpkg/errno"
	"dbm-services/mysql/db-partition/model"

	"golang.org/x/exp/slog"
)

// DryRun TODO
func (m *Checker) DryRun() ([]PartitionObject, error) {
	slog.Info("do service DryRun")
	var objects []PartitionObject
	var sqls []PartitionSql
	var err error
	var needPartition bool
	if m.BkBizId == 0 {
		return objects, errno.BkBizIdIsEmpty
	}
	if m.ClusterId == 0 {
		return objects, errno.ClusterIdIsEmpty
	}
	if m.BkCloudId == nil {
		return objects, errno.CloudIdRequired
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
	if m.ConfigId == 0 {
		err = model.DB.Self.Table(tbName).Where("bk_biz_id = ? and cluster_id = ?", m.BkBizId, m.ClusterId).Scan(&configs).
			Error
		if err != nil {
			slog.Error("msg", fmt.Sprintf("query %s err", tbName), err)
			return objects, err
		}
	} else {
		err = model.DB.Self.Table(tbName).Where("bk_biz_id = ? and cluster_id = ? and id = ?", m.BkBizId, m.ClusterId,
			m.ConfigId).Scan(&configs).Error
		if err != nil {
			slog.Error("msg", fmt.Sprintf("query %s err", tbName), err)
			return objects, err
		}
	}
	if len(configs) == 0 {
		return objects, errno.PartitionConfigNotExisted
	}

	slog.Info(fmt.Sprintf("configs:%v", configs))
	switch m.ClusterType {
	case Tendbha, Tendbsingle:
		newConfigs, err := GetMaster(configs, m.ImmuteDomain, m.ClusterType)
		if err != nil {
			slog.Error("msg", "GetClusterMasterError", err)
			return objects, err
		}
		sqls, err = m.CheckPartitionConfigs(newConfigs, "mysql", 1)
		if err != nil {
			slog.Error("msg", "CheckPartitionConfigs", err)
			return objects, err
		}
		objects = []PartitionObject{{"0.0.0.0", 0, "null", sqls}}
	case Tendbcluster:
		objects, err = m.CheckSpiderPartitionConfigs(configs)
		if err != nil {
			slog.Error("msg", "CheckSpiderPartitionConfigs", err)
			return objects, err
		}
	default:
		slog.Error(m.ClusterType, "error", errors.New("not supported db type"))
		return objects, errno.NotSupportedClusterType
	}

	for _, item := range objects {
		for _, execute := range item.ExecuteObjects {
			// 集群没有需要执行的分区语句并且在获取分区语句时没有错误，则不生成单据
			if len(execute.AddPartition) != 0 || len(execute.DropPartition) != 0 || len(execute.InitPartition) != 0 {
				needPartition = true
				break
			}
		}
	}
	if needPartition == false {
		return objects, errno.NothingToDo
	}
	return objects, nil
}

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
		execute, err := m.CheckPartitionConfigs(newconfigs, item["WRAPPER"].(string), splitCnt)
		if err != nil {
			slog.Error("msg", "CheckPartitionConfigs", err)
			return all, errno.GetPartitionSqlFail.Add(fmt.Sprintf("spit%s %s:%s\n%s", item["SPLIT_NUM"], item["HOST"],
				item["PORT"], err.Error()))
		}
		all = append(all, PartitionObject{host, port, item["SERVER_NAME"].(string), execute})
	}

	return all, nil
}

// CheckPartitionConfigs TODO
func (m *Checker) CheckPartitionConfigs(configs []*PartitionConfig, dbtype string, splitCnt int) ([]PartitionSql,
	error) {
	fmt.Printf("do CheckPartitionConfigs")
	var errMsg Messages
	sqlSet := PartitionSqlSet{}
	wg := sync.WaitGroup{}
	tokenBucket := make(chan int, 10)
	for _, config := range configs {
		wg.Add(1)
		tokenBucket <- 0
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		go func(config *PartitionConfig) {
			slog.Info(fmt.Sprintf("%s:%v", "CheckOnePartitionConfig", config))
			err := m.CheckOnePartitionConfig(ctx, cancel, *config, &wg, &tokenBucket, &sqlSet, dbtype, splitCnt)
			if err != nil {
				errMsg.mu.Lock()
				errMsg.list = append(errMsg.list, err.Error())
				errMsg.mu.Unlock()
			}
		}(config)
	}
	wg.Wait()
	close(tokenBucket)
	if len(errMsg.list) > 0 {
		return sqlSet.PartitionSqls, fmt.Errorf(strings.Join(errMsg.list, "\n"))
	}
	return sqlSet.PartitionSqls, nil
}

// CheckOnePartitionConfig TODO
func (m *Checker) CheckOnePartitionConfig(ctx context.Context, cancel context.CancelFunc, config PartitionConfig,
	wg *sync.WaitGroup, tokenBucket *chan int, sqlSet *PartitionSqlSet, dbtype string, splitCnt int) error {
	fmt.Printf("do CheckOnePartitionConfig")
	var addSql, dropSql []string
	var err error
	var initSql []InitSql
	defer func() {
		<-*tokenBucket
		wg.Done()
		cancel()
	}()

	finish := make(chan int, 1)
	errorChan := make(chan error, 1)
	go func() {
		defer func() {
			finish <- 1
		}()
		initSql, addSql, dropSql, err = config.GetPartitionDbLikeTbLike(dbtype, splitCnt)
		if err != nil {
			errorChan <- err
			return
		}
		sqlSet.Mu.Lock()
		sqlSet.PartitionSqls = append(sqlSet.PartitionSqls, PartitionSql{config.ID, config.DbLike, config.TbLike, initSql,
			addSql, dropSql})
		sqlSet.Mu.Unlock()
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

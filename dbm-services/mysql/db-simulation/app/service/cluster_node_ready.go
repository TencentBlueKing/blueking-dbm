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
	"fmt"
	"time"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-simulation/app/service/readyutil"
)

const (
	clusterNodeReadyRetryTimes = 60
	clusterNodeReadyRetryDelay = 1 * time.Second
	createNodeRetryTimes       = 10
	createNodeRetryDelay       = 2 * time.Second
)

// waitClusterNodesReady waits until MySQL TCP select 1 succeeds on each probe port of the pod.
func (k *DbPodSets) waitClusterNodesReady(podIp string) error {
	if k.BaseInfo == nil {
		return errors.New("cluster node readiness probe failed: BaseInfo is nil")
	}
	pwd := k.BaseInfo.RootPwd
	for _, port := range readyutil.ClusterNodeProbePorts(len(k.SpiderPods)) {
		port := port
		logger.Info("waiting cluster node ready at %s:%d", podIp, port)
		fnc := func() error {
			worker, err := cmutil.NewDbWorker(fmt.Sprintf("%s:%s@tcp(%s:%d)/?timeout=5s",
				DefaultUser, pwd, podIp, port))
			if err != nil {
				logger.Warn("cluster node %s:%d not ready yet: %s", podIp, port, err.Error())
				return err
			}
			defer worker.Db.Close()
			if _, err = worker.Db.Exec("select 1"); err != nil {
				logger.Warn("cluster node %s:%d select 1 failed: %s", podIp, port, err.Error())
				return err
			}
			return nil
		}
		if err := cmutil.Retry(cmutil.RetryConfig{
			Times:     clusterNodeReadyRetryTimes,
			DelayTime: clusterNodeReadyRetryDelay,
		}, fnc); err != nil {
			return errors.Wrapf(err, "cluster node TCP readiness probe timeout at %s:%d", podIp, port)
		}
		logger.Info("cluster node ready at %s:%d", podIp, port)
	}
	logger.Info("all cluster nodes TCP ready on pod %s", podIp)
	return nil
}

// execCreateClusterSQL executes one topology SQL; CREATE NODE gets limited short retries on connect/12034.
func (k *DbPodSets) execCreateClusterSQL(sql string) error {
	if k.DbWork == nil || k.DbWork.Db == nil {
		return errors.New("exec create cluster sql failed: DbWork is nil")
	}
	if !readyutil.IsCreateNodeSQL(sql) {
		_, err := k.DbWork.Db.Exec(sql)
		return err
	}

	var lastErr error
	for i := 0; i < createNodeRetryTimes; i++ {
		_, lastErr = k.DbWork.Db.Exec(sql)
		if lastErr == nil {
			return nil
		}
		if !readyutil.IsRetryableCreateNodeError(lastErr) {
			return lastErr
		}
		logger.Warn("CREATE NODE retryable failure (%d/%d): %s", i+1, createNodeRetryTimes, lastErr.Error())
		if i < createNodeRetryTimes-1 {
			time.Sleep(createNodeRetryDelay)
		}
	}
	return errors.Wrap(lastErr, "CREATE NODE retries exhausted")
}

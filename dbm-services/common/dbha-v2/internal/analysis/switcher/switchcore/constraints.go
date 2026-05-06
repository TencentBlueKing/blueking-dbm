/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package switchcore

import (
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/pkg/logger"
)

const (
	ClusterLevelSwitchDefaultMaxClusterNum  = 32
	ClusterLevelSwitchDefaultMaxInstanceNum = 64

	DbmApiDefaultMaxConcurrentRequests = 16

	defaultDbConnectTimeout = 3 * time.Second
)

// ClusterLevelSwitchMaxClusterConcurrency returns a positive cap for
// parallel cluster-level switch workers.
func ClusterLevelSwitchMaxClusterConcurrency() int {
	n := config.Cfg.Workflow.SwitchFlow.ClusterLevelSwitchMaxClusterNum
	if n <= 0 {
		logger.Warn("max cluster number(%d) for cluster level switch is invalid, using default %d",
			n, ClusterLevelSwitchDefaultMaxClusterNum)
		return ClusterLevelSwitchDefaultMaxClusterNum
	}
	return n
}

// ClusterLevelSwitchMaxInstanceConcurrency returns the cap for
// parallel per-instance work inside one cluster (e.g. pre-switch checks).
func ClusterLevelSwitchMaxInstanceConcurrency() int {
	n := config.Cfg.Workflow.SwitchFlow.ClusterLevelSwitchMaxInstanceNum
	if n <= 0 {
		logger.Warn("clusterLevelSwitchMaxInstanceNum(%d) is invalid, using default %d",
			n, ClusterLevelSwitchDefaultMaxInstanceNum)
		return ClusterLevelSwitchDefaultMaxInstanceNum
	}
	return n
}

// DbmApiMaxConcurrentRequests returns the cap for
// parallel in-flight DBM API calls (e.g. per-instance status update).
func DbmApiMaxConcurrentRequests() int {
	n := config.Cfg.Workflow.SwitchFlow.DbmApiMaxConcurrentRequests
	if n <= 0 {
		logger.Warn("dbmApiMaxConcurrentRequests(%d) is invalid, using default %d",
			n, DbmApiDefaultMaxConcurrentRequests)
		return DbmApiDefaultMaxConcurrentRequests
	}
	return n
}

// DbConnectTimeout returns workflow.switchflow.dbConnectTimeout, or default when unset.
func DbConnectTimeout() time.Duration {
	d := config.Cfg.Workflow.SwitchFlow.DbConnectTimeout
	if d <= 0 {
		return defaultDbConnectTimeout
	}
	return d
}

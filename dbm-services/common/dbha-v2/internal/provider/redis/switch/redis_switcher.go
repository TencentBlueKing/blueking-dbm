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

package redisswitch

import (
	"context"
	"slices"
	"sync"

	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchcore"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

var _ switcher.Switcher = (*Redis)(nil)

var (
	clusterProtocolClusterTypes = []haprobe.DbmMetadataClusterType{
		haprobe.DbmMetadataClusterTypePredixyRedisCluster,
		haprobe.DbmMetadataClusterTypePredixyTendisplusCluster,
	}

	twemproxyClusterTypes = []haprobe.DbmMetadataClusterType{
		haprobe.DbmMetadataClusterTypeTwemproxyRedis,
		haprobe.DbmMetadataClusterTypeTwemproxyTendisSSD,
	}
)

// isClusterProtocolClusterType reports whether the cluster elects a new master by itself.
func isClusterProtocolClusterType(clusterType haprobe.DbmMetadataClusterType) bool {
	return slices.Contains(clusterProtocolClusterTypes, clusterType)
}

// isTwemproxyClusterType reports whether the proxy layer is twemproxy.
func isTwemproxyClusterType(clusterType haprobe.DbmMetadataClusterType) bool {
	return slices.Contains(twemproxyClusterTypes, clusterType)
}

// Redis implements the Switcher interface for Redis database instances.
type Redis struct {
}

// DbTypeName returns the Redis database type identifier.
func (r *Redis) DbTypeName() haprobe.DbType {
	return haprobe.DbTypeRedis
}

// shouldHandleSwitchInstance reports whether redis switch takes over this instance.
// Cluster-protocol storage is not switched here; the cluster elects a new master itself.
func (r *Redis) shouldHandleSwitchInstance(inst *dbm.DbInstMetadata) bool {
	if inst == nil {
		return false
	}

	if !isClusterProtocolClusterType(inst.ClusterType) {
		return true
	}

	if inst.MachineType == haprobe.DbmMetadataMachineTypePredixy {
		return true
	}

	return false
}

// InstanceLevelSwitch handles Redis instance switching operations.
func (r *Redis) InstanceLevelSwitch(ctx context.Context, switchLoggers []switchlogger.DbSwitchLogger,
	req *switcher.Request) *switcher.Response {
	rsp := &switcher.Response{
		FailureInsts: map[switchcore.MetadataKey]*dbm.DbInstMetadata{},
	}

	seenInsts := make(map[switchcore.MetadataKey]struct{})
	var wg sync.WaitGroup

	for _, inst := range req.InstData {
		if inst == nil {
			logger.Warn("Redis switcher get nil instance")
			continue
		}

		instKey := switchcore.GenerateMetadataKey(inst.BkCloudID, inst.IP, inst.Port)
		if _, exists := seenInsts[instKey]; exists {
			logger.Warn("Redis switcher got duplicate instance in request, inst: %s", instKey)
			continue
		}
		seenInsts[instKey] = struct{}{}

		wg.Add(1)
		go func(inst *dbm.DbInstMetadata, instKey switchcore.MetadataKey) {
			defer wg.Done()

			swReporter := switcher.NewSwitchReporter(switchLoggers, switchcore.InstMetadataMap{instKey: inst},
				req.SwitchID, req.ActionScope)
			swReporter.ReportSwitchLogf(switchlogger.SwitchInfo, "start to switch the single redis instance")

			if !r.shouldHandleSwitchInstance(inst) {
				swReporter.ReportSwitchLogf(switchlogger.SwitchSuccess,
					"skip current redis switch for cluster protocol storage, clusterType:%s, machineType:%s, role:%s",
					inst.ClusterType, inst.MachineType, inst.InstanceRole)
				return
			}

			swInst, newErr := NewSwitchInstance(inst, req.SwitchID, req.ActionScope)
			if newErr != nil {
				swReporter.ReportSwitchLogf(switchlogger.SwitchFail, "failed to create redis switcher, errmsg: %s", newErr.Error())
				rsp.AddFailureInst(instKey, inst)
				return
			}

			swInst.SetSwitchLogger(switchLoggers)

			if switchSuccess, swErr := switchcore.SwitchSingleInstance(ctx, swInst); !switchSuccess {
				swReporter.ReportSwitchLogf(switchlogger.SwitchFail, "failed to switch the single redis instance, errmsg: %s",
					swErr.Error())
				rsp.AddFailureInst(instKey, inst)
				return
			}

			rsp.RecordInstanceNewMaster(instKey, swInst)

			swReporter.ReportSwitchLogf(switchlogger.SwitchSuccess, "successfully switched the single redis instance: %s",
				instKey)
		}(inst, instKey)
	}

	wg.Wait()

	if rsp.FailureInstCount() == 0 {
		return rsp
	}

	rsp.Err = switcher.ErrSwitchPartialSuccess
	return rsp
}

// Switch handles Redis switching operations. Only instance-level switch is supported.
func (r *Redis) Switch(ctx context.Context, req *switcher.Request) *switcher.Response {
	rsp := &switcher.Response{
		FailureInsts: map[switchcore.MetadataKey]*dbm.DbInstMetadata{},
	}

	if req == nil {
		rsp.Err = gerrors.Newf(gerrors.Failure, "Redis switcher get nil switch request")
		logger.Error("%s", rsp.Err.Error())
		return rsp
	}

	switchLoggers, releaseLoggers, newLoggerErr := switchlogger.NewSwitchLoggers()
	if newLoggerErr != nil {
		logger.Error("Redis switcher failed to create switch logger: %s", newLoggerErr)
	}
	defer releaseLoggers()

	switch req.ActionScope {
	case hamodel.ActionScopeTypeDbInstance:
		return r.InstanceLevelSwitch(ctx, switchLoggers, req)

	default:
		rsp.Err = gerrors.Newf(gerrors.Failure, "Redis switcher got unknown action scope: %s", req.ActionScope)
		logger.Error("%s", rsp.Err.Error())

		for _, instData := range req.GetDbInstMetadata() {
			instKey := switchcore.GenerateMetadataKey(instData.BkCloudID, instData.IP, instData.Port)
			rsp.AddFailureInst(instKey, instData)
		}

		return rsp
	}
}

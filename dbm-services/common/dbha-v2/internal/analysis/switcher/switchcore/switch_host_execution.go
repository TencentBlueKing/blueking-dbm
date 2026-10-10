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
	"context"
	"fmt"
	"sync"

	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
	"dbm-services/common/dbha-v2/pkg/gerrors"
)

// errIfCtxDoneInHostSwitch returns the error if ctx is non-nil
// and the context is canceled or expired, otherwise nil.
func errIfCtxDoneInHostSwitch(ctx context.Context, ins SwitchableInstance) error {
	return errIfCtxDoneInInstanceSwitch(ctx, ins)
}

// newSharedClusterLockLogFunc returns a log function for a cluster lock that is shared by multiple
// same-host instances. The lockLogPrefix tags every lock log so the single shared lock is visible
// (callers describe what shares it), and the log is reported to each instance in the group.
func newSharedClusterLockLogFunc(lockLogPrefix string,
	group map[MetadataKey]SwitchableInstance) switchlogger.SwitchLogFunc {
	return func(level switchlogger.SwitchLogLevel, format string, args ...any) bool {
		msg := lockLogPrefix + fmt.Sprintf(format, args...)
		ok := true
		for _, ins := range group {
			if !ins.ReportLogf(level, "%s", msg) {
				ok = false
			}
		}
		return ok
	}
}

// checkStatusForHostSwitch serially validates the status of every instance on the same host.
// Instance status is held in memory, so the check is fast and does not need parallelism.
// It returns the keys of instances whose pre-status check fails.
func checkStatusForHostSwitch(ctx context.Context, swInstMap map[MetadataKey]SwitchableInstance) []MetadataKey {
	failedInsts := make([]MetadataKey, 0)

	for instKey, ins := range swInstMap {
		if err := errIfCtxDoneInHostSwitch(ctx, ins); err != nil {
			failedInsts = append(failedInsts, instKey)
			continue
		}

		if (ins.GetStatus() == dbm.Running) || (ins.GetStatus() == dbm.Available) {
			ins.ReportLogf(switchlogger.SwitchInfo, "pre-status check pass with status:%s", ins.GetStatus())
			continue
		}

		ins.ReportLogf(switchlogger.SwitchError, "pre-status check unpass for wrong status:%s", ins.GetStatus())
		failedInsts = append(failedInsts, instKey)
	}

	return failedInsts
}

// setStatusForHostSwitch marks all instances on the same host as unavailable with a single
// batch DBM API call, instead of one API call per instance.
func setStatusForHostSwitch(ctx context.Context, swInstMap map[MetadataKey]SwitchableInstance) error {
	if len(swInstMap) == 0 {
		return nil
	}

	if ctx != nil {
		if err := ctx.Err(); err != nil {
			return err
		}
	}

	// instances on the same host share the same bk_cloud_id (host key is bk_cloud_id + ip)
	var bkCloudID int
	insts := make([]dbm.InstWithinCloud, 0, len(swInstMap))
	for _, ins := range swInstMap {
		bkCloudID = ins.GetBkCloudID()
		insts = append(insts, dbm.InstWithinCloud{IP: ins.GetIP(), Port: ins.GetPort()})
	}

	dbmClient := &dbm.Client{}
	if err := dbmClient.UpdateBatchInstancesStatus(bkCloudID, insts, dbm.Unavailable); err != nil {
		retErr := gerrors.Newf(gerrors.Failure, "failed to set instances unavailable in batch: %s", err.Error())
		for _, ins := range swInstMap {
			ins.ReportLogf(switchlogger.SwitchError, "%s", retErr.Error())
		}
		return retErr
	}

	for _, ins := range swInstMap {
		ins.ReportLogf(switchlogger.SwitchInfo, "successfully set instance unavailable")
	}

	return nil
}

// checkOnSameHost runs CheckBeforeSwitch for all instances on the same host concurrently.
// Instances are grouped by cluster so each cluster is locked only once (rather than once per instance);
// clusters are processed in parallel, and instances within a cluster are checked in parallel under the
// single cluster lock.
// It returns the set of instances that need no switch and the keys of instances whose check fails.
func checkOnSameHost(ctx context.Context, swInstMap map[MetadataKey]SwitchableInstance) (
	switchNotRequiredInsts map[MetadataKey]struct{}, checkFailedInsts []MetadataKey) {
	switchNotRequiredInsts = make(map[MetadataKey]struct{})
	checkFailedInsts = make([]MetadataKey, 0)

	// group instances on the host by cluster
	clusterGroups := make(map[ClusterKey]map[MetadataKey]SwitchableInstance)
	for instKey, ins := range swInstMap {
		clusterKey := GenerateClusterKey(ins.GetBkCloudID(), ins.GetClusterID())
		if clusterGroups[clusterKey] == nil {
			clusterGroups[clusterKey] = make(map[MetadataKey]SwitchableInstance)
		}
		clusterGroups[clusterKey][instKey] = ins
	}

	var mu sync.Mutex
	var wg sync.WaitGroup

	for clusterKey, group := range clusterGroups {
		wg.Add(1)

		go func(clusterKey ClusterKey, group map[MetadataKey]SwitchableInstance) {
			defer wg.Done()

			notRequired, failed := checkOnSameHostSameCluster(ctx, clusterKey, group)

			mu.Lock()
			for instKey := range notRequired {
				switchNotRequiredInsts[instKey] = struct{}{}
			}
			checkFailedInsts = append(checkFailedInsts, failed...)
			mu.Unlock()
		}(clusterKey, group)
	}

	wg.Wait()

	return switchNotRequiredInsts, checkFailedInsts
}

// checkOnSameHostSameCluster runs CheckBeforeSwitch for the instances that are on the same host and
// belong to the same cluster. The cluster is locked only once for all these instances, and the
// instances are checked in parallel under that single cluster lock.
// It returns the set of instances that need no switch and the keys of instances whose check fails.
func checkOnSameHostSameCluster(ctx context.Context, clusterKey ClusterKey,
	group map[MetadataKey]SwitchableInstance) (
	switchNotRequiredInsts map[MetadataKey]struct{}, checkFailedInsts []MetadataKey) {
	switchNotRequiredInsts = make(map[MetadataKey]struct{})
	checkFailedInsts = make([]MetadataKey, 0)

	// lock the cluster once for all of its instances on this host
	lockLogFunc := newSharedClusterLockLogFunc("[shared by same-host-same-cluster instance(s)] ", group)
	unlock, lockErr := LockClusterWithTimeout(lockLogFunc, clusterKey, ClusterLockTimeout())
	if lockErr != nil {
		for instKey := range group {
			checkFailedInsts = append(checkFailedInsts, instKey)
		}
		return switchNotRequiredInsts, checkFailedInsts
	}
	defer unlock()

	var mu sync.Mutex
	var wg sync.WaitGroup

	// check the instances within this cluster in parallel under the single cluster lock
	for instKey, ins := range group {
		wg.Add(1)

		go func(instKey MetadataKey, ins SwitchableInstance) {
			defer wg.Done()

			if err := errIfCtxDoneInHostSwitch(ctx, ins); err != nil {
				mu.Lock()
				checkFailedInsts = append(checkFailedInsts, instKey)
				mu.Unlock()
				return
			}

			checkRes, _ := checkBeforeSwitch(ins)
			switch checkRes {
			case SwitchRequired:
				// instance requires switching, nothing to record
			case SwitchNotNeeded:
				mu.Lock()
				switchNotRequiredInsts[instKey] = struct{}{}
				mu.Unlock()
			default:
				mu.Lock()
				checkFailedInsts = append(checkFailedInsts, instKey)
				mu.Unlock()
			}
		}(instKey, ins)
	}

	wg.Wait()

	return switchNotRequiredInsts, checkFailedInsts
}

// hostSwitchGroupKey returns the group key that decides which same-host instances switch together
// under one shared cluster lock. Instances in different clusters always get different keys. Within
// the same cluster, providers that implement HostSwitchGroupScopeProvider may share a scope so they
// switch in parallel; every other instance gets a key of its own (kept serial via the cluster lock).
func hostSwitchGroupKey(instKey MetadataKey, ins SwitchableInstance) string {
	clusterKey := GenerateClusterKey(ins.GetBkCloudID(), ins.GetClusterID())

	if p, ok := ins.(HostSwitchGroupScopeProvider); ok {
		if scope, shared := p.HostSwitchGroupScope(); shared && scope != "" {
			return fmt.Sprintf("%s|%s", clusterKey, scope)
		}
	}

	return fmt.Sprintf("%s|%s", clusterKey, instKey)
}

// processOnSameHost performs the actual switch for the given same-host instances.
// Instances are split into groups (see hostSwitchGroupKey); each group acquires the cluster lock once
// and switches its instances in parallel under that single lock, and groups run in parallel goroutines.
func processOnSameHost(ctx context.Context, swInstMap map[MetadataKey]SwitchableInstance) (
	errMap map[MetadataKey]error) {
	errMap = make(map[MetadataKey]error)

	// skip before locking any cluster if the switching context is already done
	for instKey, ins := range swInstMap {
		if err := errIfCtxDoneInHostSwitch(ctx, ins); err != nil {
			errMap[instKey] = err
		}
	}
	if len(errMap) > 0 {
		return errMap
	}

	// group same-host instances for the actual switch, remembering each group's cluster
	groups := make(map[string]map[MetadataKey]SwitchableInstance)
	groupClusterKeys := make(map[string]ClusterKey)
	for instKey, ins := range swInstMap {
		groupKey := hostSwitchGroupKey(instKey, ins)
		if groups[groupKey] == nil {
			groups[groupKey] = make(map[MetadataKey]SwitchableInstance)
		}
		groups[groupKey][instKey] = ins
		groupClusterKeys[groupKey] = GenerateClusterKey(ins.GetBkCloudID(), ins.GetClusterID())
	}

	var mu sync.Mutex
	var wg sync.WaitGroup

	// instSem bounds the total number of instances being switched concurrently on this host,
	// shared across all switch groups (each group acquires a slot per instance before switching it).
	instSem := make(chan struct{}, HostLevelSwitchMaxInstanceConcurrency())

	for groupKey, group := range groups {
		wg.Add(1)

		go func(clusterKey ClusterKey, group map[MetadataKey]SwitchableInstance, groupKey string) {
			defer wg.Done()

			groupErrMap := processOnSameHostGroup(ctx, clusterKey, group, groupKey, instSem)

			mu.Lock()
			for instKey, err := range groupErrMap {
				errMap[instKey] = err
			}
			mu.Unlock()
		}(groupClusterKeys[groupKey], group, groupKey)
	}

	wg.Wait()

	return errMap
}

// processOnSameHostGroup acquires the cluster lock once for the group and switches the group's
// instances in parallel under that single lock. The caller guarantees every instance in the group
// belongs to clusterKey. instSem is the host-wide semaphore bounding the number of instances being
// switched concurrently across all groups; each instance acquires a slot before its switch.
func processOnSameHostGroup(ctx context.Context, clusterKey ClusterKey,
	group map[MetadataKey]SwitchableInstance, groupKey string, instSem chan struct{}) (errMap map[MetadataKey]error) {
	errMap = make(map[MetadataKey]error)
	if len(group) == 0 {
		return errMap
	}

	// lock the cluster once for all instances in this switch group
	lockLogFunc := newSharedClusterLockLogFunc(fmt.Sprintf("[shared by same host switch group(key=%s)] ", groupKey), group)
	unlock, lockErr := LockClusterWithTimeout(lockLogFunc, clusterKey, ClusterLockTimeout())
	if lockErr != nil {
		for instKey := range group {
			errMap[instKey] = lockErr
		}
		return errMap
	}
	defer unlock()

	var mu sync.Mutex
	var wg sync.WaitGroup

	// switch the instances within this group in parallel under the single cluster lock,
	// bounded by the host-wide instance semaphore
	for instKey, ins := range group {
		wg.Add(1)
		instSem <- struct{}{}

		go func(instKey MetadataKey, ins SwitchableInstance) {
			defer wg.Done()
			defer func() { <-instSem }()

			if err := doSwitchForHostInstance(ctx, ins); err != nil {
				mu.Lock()
				errMap[instKey] = err
				mu.Unlock()
			}
		}(instKey, ins)
	}

	wg.Wait()

	return errMap
}

// doSwitchForHostInstance runs the switch processing work for one instance on the same host.
// The caller must already hold the instance's cluster lock.
func doSwitchForHostInstance(ctx context.Context, ins SwitchableInstance) (processErr error) {
	if err := errIfCtxDoneInHostSwitch(ctx, ins); err != nil {
		return err
	}

	if err := ins.DoSwitch(); err != nil {
		processErr = gerrors.Newf(gerrors.Failure, "failed to do switch: %s", err.Error())
		ins.ReportLogf(switchlogger.SwitchError, "%s", processErr.Error())
		return processErr
	}
	ins.ReportLogf(switchlogger.SwitchInfo, "successfully do switch")

	if err := errIfCtxDoneInHostSwitch(ctx, ins); err != nil {
		return err
	}

	if err := ins.UpdateMetaInfo(); err != nil {
		processErr = gerrors.Newf(gerrors.Failure, "failed to update meta info: %s", err.Error())
		ins.ReportLogf(switchlogger.SwitchError, "%s", processErr.Error())
		return processErr
	}
	ins.ReportLogf(switchlogger.SwitchInfo, "successfully update meta info")

	if err := errIfCtxDoneInHostSwitch(ctx, ins); err != nil {
		return err
	}

	if err := ins.DoFinal(); err != nil {
		processErr = gerrors.Newf(gerrors.Failure, "failed to do final step: %s", err.Error())
		ins.ReportLogf(switchlogger.SwitchError, "%s", processErr.Error())
		return processErr
	}
	ins.ReportLogf(switchlogger.SwitchInfo, "successfully do final step")

	return nil
}

// SwitchSameHostInstances switches instances on the same host.
// It returns true if all instances are switched successfully, otherwise returns false.
// The errMap is a map of instance key to error, only contains the errors of instances that failed to switch.
func SwitchSameHostInstances(ctx context.Context, swInstMap map[MetadataKey]SwitchableInstance) (
	switchSuccess bool, errMap map[MetadataKey]error) {
	errMap = make(map[MetadataKey]error)

	// Step 1: serially check the status of all instances on the host (fast, in-memory).
	if statusFailedInsts := checkStatusForHostSwitch(ctx, swInstMap); len(statusFailedInsts) > 0 {
		err := gerrors.Newf(gerrors.Failure, "pre-status check unpass for some instances on the same host, "+
			"failed instances: [%s]", JoinMetadataKeys(statusFailedInsts, ", "))
		for instKey := range swInstMap {
			errMap[instKey] = err
		}
		return false, errMap
	}

	// Step 2: set all instances unavailable with a single batch DBM API call.
	if err := setStatusForHostSwitch(ctx, swInstMap); err != nil {
		for instKey := range swInstMap {
			errMap[instKey] = err
		}
		return false, errMap
	}

	// Step 3: check-before-switch in parallel, locking each cluster only once.
	switchNotRequiredInsts, checkFailedInsts := checkOnSameHost(ctx, swInstMap)

	// Once any instance fails the check, terminate the switch process of all instances on the same host
	if len(checkFailedInsts) > 0 {
		err := gerrors.Newf(gerrors.Failure, "check before switch unpass for some instances on the same host, "+
			"failed instances: [%s]", JoinMetadataKeys(checkFailedInsts, ", "))

		for instKey := range swInstMap {
			if _, exists := switchNotRequiredInsts[instKey]; exists {
				continue
			}
			errMap[instKey] = err
		}

		return false, errMap
	}

	// Step 4: do the actual switch for instances that require switching.
	instsToSwitch := make(map[MetadataKey]SwitchableInstance, len(swInstMap))
	for instKey, swInst := range swInstMap {
		if _, exists := switchNotRequiredInsts[instKey]; exists {
			continue
		}
		instsToSwitch[instKey] = swInst
	}

	// errMap is empty here: steps 1-3 return early on any failure.
	errMap = processOnSameHost(ctx, instsToSwitch)

	if len(errMap) > 0 {
		return false, errMap
	}

	return true, nil
}

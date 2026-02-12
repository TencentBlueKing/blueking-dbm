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
	"fmt"
	"strings"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchmutex"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
)

type SwitchCheckCode int
type MetadataKey string
type ClusterKey string
type HostKey struct {
	BkCloudID int
	IP        string
}

func (hostKey HostKey) String() string {
	return fmt.Sprintf("%d:%s", hostKey.BkCloudID, hostKey.IP)
}

type InstMetadataMap map[MetadataKey]*dbm.DbInstMetadata

const (
	// SwitchRequired indicates that switching is required
	SwitchRequired SwitchCheckCode = iota
	// SwitchNotNeeded indicates that there is no need to switch
	SwitchNotNeeded
	// SwitchCheckUnpass indicates that the switch check unpass
	SwitchCheckUnpass
)

const defaultClusterLockTimeout = 10 * time.Second

// SwitchableInstance defines the interface for database instances that support switching operations.
// It provides a standardized set of methods for handling instance failover and switchover procedures.
type SwitchableInstance interface {
	// CheckBeforeSwitch performs pre-switch validation and returns whether switching is needed
	CheckBeforeSwitch() (SwitchCheckCode, error)

	// DoFinal executes final cleanup and post-switch operations
	DoFinal() error

	// DoSwitch performs the actual instance switching logic
	DoSwitch() error

	// GetInstanceInfo returns descriptive information about the instance
	GetInstanceInfo() string

	// GetBkCloudID returns the cloud ID of the instance
	GetBkCloudID() int

	// GetCluster returns the cluster name of the instance
	GetCluster() string

	// GetClusterID returns the cluster ID of the instance
	GetClusterID() int

	// GetIP returns the instance IP
	GetIP() string

	// GetPort returns the instance port
	GetPort() int

	// GetStatus retrieves the current status of the instance
	GetStatus() dbm.DbmMetadataStatus

	// ReportLogf records switch operation logs at specified level
	ReportLogf(level switchlogger.SwitchLogLevel, format string, args ...any) bool

	// RollBack reverts any changes made during a failed switch attempt
	RollBack() error

	// SetInstanceUnavailable marks the instance as unavailable for service
	SetInstanceUnavailable() error

	// SetSwitchLogger sets the loggers for recording switch operations
	SetSwitchLogger(loggers []switchlogger.DbSwitchLogger)

	// UpdateMetaInfo updates instance metadata after successful switch
	UpdateMetaInfo() error

	// SetSwitchID sets the switch request ID
	SetSwitchID(switchID string)

	// SetActionScope sets the action scope of the switch task
	SetActionScope(actionScope hamodel.ActionScopeType)
}

// GenerateMetadataKey generates a unique key for instance metadata
func GenerateMetadataKey(bkCloudId int, ip string, port int) MetadataKey {
	return MetadataKey(fmt.Sprintf("%d:%s:%d", bkCloudId, ip, port))
}

// ExtractMetadataKeys extracts the keys of the instance data map as a slice of strings.
func ExtractMetadataKeys[T any](instDataMap map[MetadataKey]T) []string {
	keys := make([]string, 0, len(instDataMap))

	for instKey := range instDataMap {
		keys = append(keys, string(instKey))
	}

	return keys
}

// GenerateClusterKey generates a unique key for cluster-level lock.
func GenerateClusterKey(bkCloudId int, clusterId int) ClusterKey {
	return ClusterKey(fmt.Sprintf("%d:%d", bkCloudId, clusterId))
}

// GenerateHostKey generates a unique key for host-level grouping.
func GenerateHostKey(bkCloudId int, ip string) HostKey {
	return HostKey{
		BkCloudID: bkCloudId,
		IP:        ip,
	}
}

func ParseHostKey(hostKey HostKey) (bkCloudId int, ip string) {
	return hostKey.BkCloudID, hostKey.IP
}

func lockClusterWithTimeout(ins SwitchableInstance, clusterKey ClusterKey, timeout time.Duration) (func(), error) {
	if clusterKey == "" {
		return nil, gerrors.New(gerrors.Failure, "cluster key is empty")
	}

	ins.ReportLogf(switchlogger.SwitchInfo, "try to acquire cluster lock: %s, timeout: %s", clusterKey, timeout)
	mutex := switchmutex.Get(string(clusterKey))
	if !mutex.TryLock(timeout) {
		ins.ReportLogf(switchlogger.SwitchError, "timeout to acquire cluster lock: %s", clusterKey)
		return nil, gerrors.Newf(gerrors.Failure, "timeout to acquire cluster lock: %s", clusterKey)
	}

	ins.ReportLogf(switchlogger.SwitchInfo, "successfully acquired cluster lock: %s", clusterKey)
	return func() {
		mutex.Unlock()
		ins.ReportLogf(switchlogger.SwitchInfo, "released cluster lock: %s", clusterKey)
	}, nil
}

func checkBeforeSwitch(ins SwitchableInstance) (checkResult SwitchCheckCode, retErr error) {
	checkRes, checkErr := ins.CheckBeforeSwitch()

	switch checkRes {
	case SwitchRequired:
		ins.ReportLogf(switchlogger.SwitchInfo, "check result before switch: switch required")

	case SwitchNotNeeded:
		ins.ReportLogf(switchlogger.SwitchInfo, "check result before switch: no need to switch")

	default:
		errMsg := "check result before switch: check unpass"
		if checkErr != nil {
			errMsg += fmt.Sprintf(", errmsg: %s", checkErr.Error())
		}

		ins.ReportLogf(switchlogger.SwitchError, "%s", errMsg)
		retErr = gerrors.Newf(gerrors.Failure, "%s", errMsg)
	}

	return checkRes, retErr
}

// SwitchSingleInstance executes the standardized switching procedure for a single database instance.
func SwitchSingleInstance(ins SwitchableInstance) (switchSuccess bool, retErr error) {
	ins.ReportLogf(switchlogger.SwitchInfo, "start to switch single instance: %s", ins.GetInstanceInfo())

	// rollback when error occurs
	defer func() {
		if switchSuccess {
			ins.ReportLogf(switchlogger.SwitchInfo, "successfully switch single instance: %s", ins.GetInstanceInfo())
			return
		}
		ins.ReportLogf(switchlogger.SwitchError, "failed to switch single instance: %s", ins.GetInstanceInfo())

		if rollbackErr := ins.RollBack(); rollbackErr != nil {
			ins.ReportLogf(switchlogger.SwitchError, "failed to rollback switch: %s", rollbackErr.Error())
			retErr = gerrors.Newf(gerrors.Failure, "switch errmsg: %s, rollback errmsg: %s",
				retErr.Error(), rollbackErr.Error())
		}
	}()

	if (ins.GetStatus() != dbm.Running) && (ins.GetStatus() != dbm.Available) {
		retErr = gerrors.Newf(gerrors.Failure, "pre-status check unpass for wrong status:%s", ins.GetStatus())
		ins.ReportLogf(switchlogger.SwitchError, "%s", retErr.Error())
		return false, retErr
	}
	ins.ReportLogf(switchlogger.SwitchInfo, "pre-status check pass with status:%s", ins.GetStatus())

	if err := ins.SetInstanceUnavailable(); err != nil {
		retErr = gerrors.Newf(gerrors.Failure, "failed to set instance unavailable: %s", err.Error())
		ins.ReportLogf(switchlogger.SwitchError, "%s", retErr.Error())
		return false, retErr
	}
	ins.ReportLogf(switchlogger.SwitchInfo, "successfully set instance unavailable")

	// lock the cluster that the instance belongs to
	clusterKey := GenerateClusterKey(ins.GetBkCloudID(), ins.GetClusterID())
	unlock, lockErr := lockClusterWithTimeout(ins, clusterKey, defaultClusterLockTimeout)
	if lockErr != nil {
		retErr = lockErr
		return false, retErr
	}
	defer unlock()

	checkRes, checkErr := checkBeforeSwitch(ins)
	if checkRes == SwitchCheckUnpass {
		return false, checkErr
	}

	if checkRes == SwitchNotNeeded {
		return true, nil
	}

	if err := ins.DoSwitch(); err != nil {
		retErr = gerrors.Newf(gerrors.Failure, "failed to do switch: %s", err.Error())
		ins.ReportLogf(switchlogger.SwitchError, "%s", retErr.Error())
		return false, retErr
	}
	ins.ReportLogf(switchlogger.SwitchInfo, "successfully do switch")

	if err := ins.UpdateMetaInfo(); err != nil {
		retErr = gerrors.Newf(gerrors.Failure, "failed to update meta info: %s", err.Error())
		ins.ReportLogf(switchlogger.SwitchError, "%s", retErr.Error())
		return false, retErr
	}
	ins.ReportLogf(switchlogger.SwitchInfo, "successfully update meta info")

	if err := ins.DoFinal(); err != nil {
		retErr = gerrors.Newf(gerrors.Failure, "failed to do final step: %s", err.Error())
		ins.ReportLogf(switchlogger.SwitchError, "%s", retErr.Error())
		return false, retErr
	}
	ins.ReportLogf(switchlogger.SwitchInfo, "successfully do final step")

	return true, nil
}

// prepareForHostSwitch routine function that does switch preparation work for one instance on the same host
func prepareForHostSwitch(ins SwitchableInstance) (needDoSwitch bool, retErr error) {
	if (ins.GetStatus() != dbm.Running) && (ins.GetStatus() != dbm.Available) {
		retErr = gerrors.Newf(gerrors.Failure, "pre-status check unpass for wrong status:%s", ins.GetStatus())
		ins.ReportLogf(switchlogger.SwitchError, "%s", retErr.Error())
		return false, retErr
	}
	ins.ReportLogf(switchlogger.SwitchInfo, "pre-status check pass with status:%s", ins.GetStatus())

	if err := ins.SetInstanceUnavailable(); err != nil {
		retErr = gerrors.Newf(gerrors.Failure, "failed to set instance unavailable: %s", err.Error())
		ins.ReportLogf(switchlogger.SwitchError, "%s", retErr.Error())
		return false, retErr
	}
	ins.ReportLogf(switchlogger.SwitchInfo, "successfully set instance unavailable")

	// lock cluster before check node status
	clusterKey := GenerateClusterKey(ins.GetBkCloudID(), ins.GetClusterID())
	unlock, err := lockClusterWithTimeout(ins, clusterKey, defaultClusterLockTimeout)
	if err != nil {
		return false, err
	}
	defer unlock()

	// check node status
	checkRes, checkErr := checkBeforeSwitch(ins)
	if checkRes != SwitchRequired {
		return false, checkErr
	}

	return true, nil
}

// processForHostSwitch routine function that does switch processing work for one instance on the same host
func processForHostSwitch(ins SwitchableInstance) (processErr error) {
	// lock cluster before do switch
	clusterKey := GenerateClusterKey(ins.GetBkCloudID(), ins.GetClusterID())
	unlock, err := lockClusterWithTimeout(ins, clusterKey, defaultClusterLockTimeout)
	if err != nil {
		return err
	}
	defer unlock()

	if err := ins.DoSwitch(); err != nil {
		processErr = gerrors.Newf(gerrors.Failure, "failed to do switch: %s", err.Error())
		ins.ReportLogf(switchlogger.SwitchError, "%s", processErr.Error())
		return processErr
	}
	ins.ReportLogf(switchlogger.SwitchInfo, "successfully do switch")

	if err := ins.UpdateMetaInfo(); err != nil {
		processErr = gerrors.Newf(gerrors.Failure, "failed to update meta info: %s", err.Error())
		ins.ReportLogf(switchlogger.SwitchError, "%s", processErr.Error())
		return processErr
	}
	ins.ReportLogf(switchlogger.SwitchInfo, "successfully update meta info")

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
func SwitchSameHostInstances(swInstMap map[MetadataKey]SwitchableInstance) (switchSuccess bool, errMap map[MetadataKey]error) {
	prepareFailedInsts := make([]string, 0)
	switchNotRequiredInsts := map[MetadataKey]struct{}{}
	errMap = make(map[MetadataKey]error)

	var mu sync.Mutex
	var wg sync.WaitGroup

	// do switch preparation work for all instances on the same host concurrently
	for instKey, ins := range swInstMap {
		wg.Add(1)

		go func(instKey MetadataKey, ins SwitchableInstance) {
			defer wg.Done()

			needDoSwitch, err := prepareForHostSwitch(ins)
			if err != nil {
				mu.Lock()
				prepareFailedInsts = append(prepareFailedInsts, string(instKey))
				mu.Unlock()
				return
			}

			if needDoSwitch {
				return
			}

			mu.Lock()
			switchNotRequiredInsts[instKey] = struct{}{}
			mu.Unlock()
		}(instKey, ins)
	}

	wg.Wait()

	// Once there is an instance preparation failed, terminate the switch process of all instances on the same host
	if len(prepareFailedInsts) > 0 {
		err := gerrors.Newf(gerrors.Failure, "failed to do switch preparation for some instances on the same host, "+
			"failed instances: [%s]", strings.Join(prepareFailedInsts, ", "))

		for instKey := range swInstMap {
			if _, exists := switchNotRequiredInsts[instKey]; exists {
				continue
			}
			errMap[instKey] = err
		}

		return false, errMap
	}

	// do switch for all instances on the same host concurrently
	for instKey, swInst := range swInstMap {
		if _, exists := switchNotRequiredInsts[instKey]; exists {
			continue
		}

		wg.Add(1)

		go func(instKey MetadataKey, ins SwitchableInstance) {
			defer wg.Done()

			if err := processForHostSwitch(ins); err != nil {
				mu.Lock()
				errMap[instKey] = err
				mu.Unlock()
			}
		}(instKey, swInst)
	}

	wg.Wait()

	if len(errMap) > 0 {
		return false, errMap
	}

	return true, nil
}

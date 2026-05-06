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
	"strings"
	"sync"

	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
	"dbm-services/common/dbha-v2/pkg/gerrors"
)

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
	unlock, err := lockClusterWithTimeout(ins.ReportLogf, clusterKey, defaultClusterLockTimeout)
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
	unlock, err := lockClusterWithTimeout(ins.ReportLogf, clusterKey, defaultClusterLockTimeout)
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

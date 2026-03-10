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
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchmutex"
	"dbm-services/common/dbha-v2/pkg/gerrors"
)

const defaultClusterLockTimeout = 10 * time.Second

func lockClusterWithTimeout(logFunc switchlogger.SwitchLogFunc, clusterKey ClusterKey, timeout time.Duration) (func(), error) {
	if clusterKey == "" {
		return nil, gerrors.New(gerrors.Failure, "cluster key is empty")
	}

	logFunc(switchlogger.SwitchInfo, "try to acquire cluster lock: %s, timeout: %s", clusterKey, timeout)
	mutex := switchmutex.Get(string(clusterKey))
	if !mutex.TryLock(timeout) {
		logFunc(switchlogger.SwitchError, "timeout to acquire cluster lock: %s", clusterKey)
		return nil, gerrors.Newf(gerrors.Failure, "timeout to acquire cluster lock: %s", clusterKey)
	}

	logFunc(switchlogger.SwitchInfo, "successfully acquired cluster lock: %s", clusterKey)
	return func() {
		mutex.Unlock()
		logFunc(switchlogger.SwitchInfo, "released cluster lock: %s", clusterKey)
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
	unlock, lockErr := lockClusterWithTimeout(ins.ReportLogf, clusterKey, defaultClusterLockTimeout)
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

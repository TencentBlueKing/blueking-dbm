/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of sw software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and sw permission notice shall be included in all
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

package switcher

import (
	"fmt"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
)

// SwitchableInstance defines the interface for database instances that support switching operations.
// It provides a standardized set of methods for handling instance failover and switchover procedures.
type SwitchableInstance interface {
	// CheckBeforeSwitch performs pre-switch validation and returns whether switching is needed
	CheckBeforeSwitch() (bool, error)

	// DoFinal executes final cleanup and post-switch operations
	DoFinal() error

	// DoSwitch performs the actual instance switching logic
	DoSwitch() error

	// GetInstanceInfo returns descriptive information about the instance
	GetInstanceInfo() string

	// GetStatus retrieves the current status of the instance
	GetStatus() hamodel.DbmMetadataStatus

	// ReportLog records switch operation logs at specified level
	ReportLog(level SwitchLogLevel, message string) bool

	// RollBack reverts any changes made during a failed switch attempt
	RollBack() error

	// SetInstanceUnavailable marks the instance as unavailable for service
	SetInstanceUnavailable() error

	// UpdateMetaInfo updates instance metadata after successful switch
	UpdateMetaInfo() error
}

// SwitchSingleInstance executes the standardized switching procedure for a single database instance.
func SwitchSingleInstance(ins SwitchableInstance) (success bool, retErr error) {
	logger.Debug("single instance switch begin: %s", ins.GetInstanceInfo())

	// rollback when need
	defer func() {
		if success {
			return
		}

		if rollbackErr := ins.RollBack(); rollbackErr != nil {
			errMsg := fmt.Sprintf("failed to rollback switch: %s", rollbackErr.Error())
			logger.Error("%s, instance{%s}", errMsg, ins.GetInstanceInfo())
			ins.ReportLog(SwitchFail, errMsg)
			retErr = gerrors.Newf(gerrors.Failure, "%s[rollback failed: %s]", retErr.Error(), rollbackErr.Error())
		}
	}()

	ins.ReportLog(SwitchInfo, "do pre-check before switch")
	if (ins.GetStatus() != hamodel.RUNNING) && (ins.GetStatus() != hamodel.AVAILABLE) {
		retErr = gerrors.Newf(gerrors.Failure, "pre-check unpass for wrong status:%s", ins.GetStatus())
		success = false
		return
	}

	if err := ins.SetInstanceUnavailable(); err != nil {
		retErr = gerrors.New(gerrors.Failure, fmt.Sprintf("failed to set instance unavailable :%s", err.Error()))
		logger.Error("%s, instance{%s}", retErr.Error(), ins.GetInstanceInfo())
		success = false
		return
	}
	ins.ReportLog(SwitchInfo, "set instance unavailable successfully")

	if checkpass, err := ins.CheckBeforeSwitch(); !checkpass {
		if err == nil {
			logger.Info("check result: no need to switch, instance{%s}", ins.GetInstanceInfo())
			success = true
			return
		}

		retErr = gerrors.New(gerrors.Failure, fmt.Sprintf("check unpass before switch: %s", err.Error()))
		logger.Error("%s, instance{%s}", retErr.Error(), ins.GetInstanceInfo())
		success = false
		return
	}

	ins.ReportLog(SwitchInfo, "pre-check pass, start to do switch")

	if err := ins.DoSwitch(); err != nil {
		retErr = gerrors.New(gerrors.Failure, fmt.Sprintf("do switch failed: %s", err.Error()))
		logger.Error("%s, instance{%s}", retErr.Error(), ins.GetInstanceInfo())
		success = false
		return
	}

	ins.ReportLog(SwitchInfo, "do switch successfully, try to update meta info")

	if err := ins.UpdateMetaInfo(); err != nil {
		retErr = gerrors.New(gerrors.Failure, fmt.Sprintf("failed to update meta info: %s", err.Error()))
		logger.Error("%s, instance{%s}", retErr.Error(), ins.GetInstanceInfo())
		success = false
		return
	}

	ins.ReportLog(SwitchInfo, "update meta info successfully, try to do the final step")

	if err := ins.DoFinal(); err != nil {
		retErr = gerrors.New(gerrors.Failure, fmt.Sprintf("final step failed: %s", err.Error()))
		logger.Error("%s, instance{%s}", retErr.Error(), ins.GetInstanceInfo())
		success = false
		return
	}

	ins.ReportLog(SwitchInfo, "switch instance successfully")
	logger.Debug("single instance switch end: %s", ins.GetInstanceInfo())
	success = true
	return
}

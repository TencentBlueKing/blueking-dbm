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

package switcher

import (
	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"fmt"
)

type SwitchCheckCode int

const (
	// SwitchRequired indicates that switching is required
	SwitchRequired SwitchCheckCode = iota
	// SwitchNotNeeded indicates that there is no need to switch
	SwitchNotNeeded
	// SwitchCheckUnpass indicates that the switch check unpass
	SwitchCheckUnpass
)

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

	// GetStatus retrieves the current status of the instance
	GetStatus() dbm.DbmMetadataStatus

	// ReportLogf records switch operation logs at specified level
	ReportLogf(level SwitchLogLevel, format string, args ...any) bool

	// RollBack reverts any changes made during a failed switch attempt
	RollBack() error

	// SetInstanceUnavailable marks the instance as unavailable for service
	SetInstanceUnavailable() error

	// SetSwitchLogger sets the loggers for recording switch operations
	SetSwitchLogger(loggers []switchlogger.DbSwitchLogger)

	// UpdateMetaInfo updates instance metadata after successful switch
	UpdateMetaInfo() error
}

// SwitchSingleInstance executes the standardized switching procedure for a single database instance.
func SwitchSingleInstance(ins SwitchableInstance) (retErr error) {
	ins.ReportLogf(SwitchInfo, "start to switch single instance: %s", ins.GetInstanceInfo())

	// rollback when error occurs
	defer func() {
		if retErr == nil {
			ins.ReportLogf(SwitchSuccess, "successfully switch single instance: %s", ins.GetInstanceInfo())
			return
		}
		ins.ReportLogf(SwitchFail, "failed to switch single instance: %s", ins.GetInstanceInfo())

		if rollbackErr := ins.RollBack(); rollbackErr != nil {
			ins.ReportLogf(SwitchFail, "failed to rollback switch: %s", rollbackErr.Error())
			retErr = gerrors.Newf(gerrors.Failure, "switch errmsg: %s, rollback errmsg: %s",
				retErr.Error(), rollbackErr.Error())
		}
	}()

	if (ins.GetStatus() != dbm.Running) && (ins.GetStatus() != dbm.Available) {
		retErr = gerrors.Newf(gerrors.Failure, "pre-status check unpass for wrong status:%s", ins.GetStatus())
		ins.ReportLogf(SwitchFail, "%s", retErr.Error())
		return
	}
	ins.ReportLogf(SwitchInfo, "pre-status check pass with status:%s", ins.GetStatus())

	if err := ins.SetInstanceUnavailable(); err != nil {
		retErr = gerrors.Newf(gerrors.Failure, "failed to set instance unavailable: %s", err.Error())
		ins.ReportLogf(SwitchFail, "%s", retErr.Error())
		return
	}
	ins.ReportLogf(SwitchInfo, "successfully set instance unavailable")

	checkRes, checkErr := ins.CheckBeforeSwitch()
	switch checkRes {
	case SwitchRequired:
		ins.ReportLogf(SwitchInfo, "check result before switch: switch required")
	case SwitchNotNeeded:
		ins.ReportLogf(SwitchInfo, "check result before switch: no need to switch")
		return
	default:
		errMsg := "check result before switch: check unpass"
		if checkErr != nil {
			errMsg += fmt.Sprintf(", errmsg: %s", checkErr.Error())
		}
		ins.ReportLogf(SwitchFail, "%s", errMsg)
		return
	}

	if err := ins.DoSwitch(); err != nil {
		retErr = gerrors.Newf(gerrors.Failure, "failed to do switch: %s", err.Error())
		ins.ReportLogf(SwitchFail, "%s", retErr.Error())
		return
	}
	ins.ReportLogf(SwitchInfo, "successfully do switch")

	if err := ins.UpdateMetaInfo(); err != nil {
		retErr = gerrors.Newf(gerrors.Failure, "failed to update meta info: %s", err.Error())
		ins.ReportLogf(SwitchFail, "%s", retErr.Error())
		return
	}
	ins.ReportLogf(SwitchInfo, "successfully update meta info")

	if err := ins.DoFinal(); err != nil {
		retErr = gerrors.Newf(gerrors.Failure, "failed to do final step: %s", err.Error())
		ins.ReportLogf(SwitchFail, "%s", retErr.Error())
		return
	}
	ins.ReportLogf(SwitchInfo, "successfully do final step")

	return
}

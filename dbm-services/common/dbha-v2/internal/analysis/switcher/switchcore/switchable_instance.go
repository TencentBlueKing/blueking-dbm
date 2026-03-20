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
	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
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

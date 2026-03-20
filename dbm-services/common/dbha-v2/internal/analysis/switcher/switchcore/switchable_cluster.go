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
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
)

// SwitchableCluster defines the interface for database clusters that support switching operations.
type SwitchableCluster interface {
	// CheckBeforeSwitch performs pre-switch validation and returns whether switching is needed
	CheckBeforeSwitch() (SwitchCheckCode, error)

	// DoFinal executes final cleanup and post-switch operations
	DoFinal() error

	// DoSwitch performs the actual instance switching logic
	DoSwitch() error

	// GetApp returns the business ID as string
	GetApp() string

	// GetBkCloudID returns the cloud ID of the cluster
	GetBkCloudID() int

	// GetCluster returns the cluster name of the cluster
	GetCluster() string

	// GetClusterID returns the cluster ID of the cluster
	GetClusterID() int

	// GetSwitchInstances returns the broken instances in the cluster
	GetSwitchInstances() InstMetadataMap

	// GetClusterInfo returns formatted cluster information string
	GetClusterInfo() string

	// ReportLogf records instance switching operation logs with specified level
	ReportLogf(instKey MetadataKey, level switchlogger.SwitchLogLevel, format string, args ...any) bool

	// ReportClusterLogf records cluster switching operation logs with specified level
	ReportClusterLogf(level switchlogger.SwitchLogLevel, format string, args ...any) bool

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
}

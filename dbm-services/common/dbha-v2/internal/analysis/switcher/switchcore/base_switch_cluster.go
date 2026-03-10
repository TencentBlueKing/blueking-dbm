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
	"strconv"
	"strings"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// BaseSwitchCluster is the base implementation of the SwitchableCluster interface
type BaseSwitchCluster struct {
	// The switch ID corresponds to a switch request
	SwitchID string

	BkCloudID   int
	BkBizID     int
	Cluster     string
	ClusterID   int
	ClusterType haprobe.DbmMetadataClusterType

	// Http client for DBM
	DbmClient *dbm.Client

	// loggers for recording switch operation
	switchLoggers []switchlogger.DbSwitchLogger

	// The instances that were requested to be switched
	SwitchInstances InstMetadataMap
}

// GetApp returns the business ID as string
func (cluster *BaseSwitchCluster) GetApp() string {
	return strconv.Itoa(cluster.BkBizID)
}

// GetBkCloudID returns the cloud ID of the cluster.
func (cluster *BaseSwitchCluster) GetBkCloudID() int {
	return cluster.BkCloudID
}

// GetCluster returns the cluster name.
func (cluster *BaseSwitchCluster) GetCluster() string {
	return cluster.Cluster
}

// GetClusterID returns the cluster ID.
func (cluster *BaseSwitchCluster) GetClusterID() int {
	return cluster.ClusterID
}

// GetSwitchInstances returns the broken instances in the cluster
func (cluster *BaseSwitchCluster) GetSwitchInstances() InstMetadataMap {
	return cluster.SwitchInstances
}

// GetClusterInfo returns formatted cluster information string
func (cluster *BaseSwitchCluster) GetClusterInfo() string {
	infoStr := fmt.Sprintf("{bk_cloud_id:%d, bk_biz_id:%d, cluster:%s, cluster_id:%d, "+
		"cluster_type:%s, broken_instances:[%s]}",
		cluster.BkCloudID, cluster.BkBizID, cluster.Cluster, cluster.ClusterID,
		cluster.ClusterType, strings.Join(ExtractMetadataKeys(cluster.SwitchInstances), ", "))
	return infoStr
}

// SetSwitchLogger sets the loggers for recording switch operations.
func (cluster *BaseSwitchCluster) SetSwitchLogger(loggers []switchlogger.DbSwitchLogger) {
	cluster.switchLoggers = loggers
}

// SetSwitchID sets the switch request ID.
func (cluster *BaseSwitchCluster) SetSwitchID(switchID string) {
	cluster.SwitchID = switchID
}

// SetInstanceUnavailable marks instances as unavailable before switching.
func (cluster *BaseSwitchCluster) SetInstanceUnavailable() error {
	failedInsts := []string{}
	for instKey, instMeta := range cluster.SwitchInstances {
		err := cluster.DbmClient.UpdateInstanceStatus(instMeta.BkCloudID, instMeta.IP, instMeta.Port, dbm.Unavailable)
		if err == nil {
			cluster.ReportLogf(instKey, switchlogger.SwitchInfo, "successfully set instance unavailable: %s", string(instKey))
			continue
		}

		failedInsts = append(failedInsts, string(instKey))
		cluster.ReportLogf(instKey, switchlogger.SwitchError,
			"failed to set instance unavailable, inst: %s, err: %s", string(instKey), err.Error())
	}

	if len(failedInsts) > 0 {
		return gerrors.Newf(gerrors.Failure,
			"failed to set unavailable status for instances: %s", strings.Join(failedInsts, ", "))
	}
	return nil
}

// DeleteOneInstanceNameService removes one broken-down instance from DNS, CLB, and Polaris entries
func (cluster *BaseSwitchCluster) DeleteOneInstanceNameService(instKey MetadataKey) error {
	instMeta, exists := cluster.SwitchInstances[instKey]
	if !exists {
		return gerrors.Newf(gerrors.Failure, "unknown instance(%s) in switch cluster(%s)", instKey, cluster.Cluster)
	}

	logFunc := func(level switchlogger.SwitchLogLevel, format string, args ...any) bool {
		return cluster.ReportLogf(instKey, level, format, args...)
	}

	manager := NewNameServiceManager(instMeta.BkCloudID, instMeta.IP, instMeta.Port, instMeta.MachineType,
		strconv.Itoa(instMeta.BkBizID), cluster.DbmClient, logFunc)

	entry := instMeta.BindEntry

	return manager.DeleteNameService(entry)
}

// CheckBeforeSwitch performs pre-switch validation and returns whether switching is needed
func (cluster *BaseSwitchCluster) CheckBeforeSwitch() (SwitchCheckCode, error) {
	return SwitchRequired, nil
}

// DoSwitch performs the actual instance switching logic
func (cluster *BaseSwitchCluster) DoSwitch() error {
	return nil
}

// UpdateMetaInfo updates instance metadata after successful switch
func (cluster *BaseSwitchCluster) UpdateMetaInfo() error {
	return nil
}

// DoFinal executes final cleanup and post-switch operations
func (cluster *BaseSwitchCluster) DoFinal() error {
	return nil
}

// RollBack performs rollback operations for the switching process
func (cluster *BaseSwitchCluster) RollBack() error {
	return nil
}

// RealReportLog records switching operation logs with specified level
// instance metadata is optional, if not provided, it will be set to an empty instance metadata
func (cluster *BaseSwitchCluster) RealReportLog(instMeta *dbm.DbInstMetadata, level switchlogger.SwitchLogLevel, message string) bool {
	// use default logger if no logger is provided
	if len(cluster.switchLoggers) == 0 {
		cluster.switchLoggers = []switchlogger.DbSwitchLogger{switchlogger.NewLogToStdHandler()}
		logger.Warn("no switch loggers provided for cluster(%s), using default logger for switch log",
			cluster.Cluster)
	}

	if instMeta == nil {
		instMeta = &dbm.DbInstMetadata{}
	}

	logTime := time.Now()
	logRecord := hamodel.DbSwitchingLog{
		SwitchID:    cluster.SwitchID,
		ActionScope: string(hamodel.ActionScopeTypeCluster),
		BkBizID:     cluster.BkBizID,
		BkCloudID:   cluster.BkCloudID,
		DbIP:        instMeta.IP,
		DbPort:      instMeta.Port,
		ClusterID:   cluster.ClusterID,
		ClusterName: cluster.Cluster,
		DbTypeName:  string(instMeta.MachineType),
		Level:       string(level),
		Content:     message,
		CreatedTime: logTime,
	}

	for _, swlogger := range cluster.switchLoggers {
		if logErr := swlogger.Append(&logRecord); logErr != nil {
			logger.Error("failed to append switch log record, inst: %s, err: %s",
				GenerateMetadataKey(instMeta.BkCloudID, instMeta.IP, instMeta.Port), logErr.Error())
		}
	}
	return true
}

// ReportLog records instance switching operation logs with specified level
func (cluster *BaseSwitchCluster) ReportLog(instKey MetadataKey, level switchlogger.SwitchLogLevel, message string) bool {
	instMeta, exists := cluster.SwitchInstances[instKey]
	if !exists {
		logger.Error("unknown instance(%s) in switch cluster(%s)", instKey, cluster.Cluster)
		return false
	}

	return cluster.RealReportLog(instMeta, level, message)
}

// ReportLogf records formatted instance switching operation logs
func (cluster *BaseSwitchCluster) ReportLogf(instKey MetadataKey, level switchlogger.SwitchLogLevel, format string, args ...any) bool {
	return cluster.ReportLog(instKey, level, fmt.Sprintf(format, args...))
}

// ReportClusterLogf records formatted cluster switching operation logs
func (cluster *BaseSwitchCluster) ReportClusterLogf(level switchlogger.SwitchLogLevel, format string, args ...any) bool {
	return cluster.RealReportLog(nil, level, fmt.Sprintf(format, args...))
}

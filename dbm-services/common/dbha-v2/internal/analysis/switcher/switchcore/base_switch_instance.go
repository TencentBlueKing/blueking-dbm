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
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

const (
	InstanceRoleNotAvailable string = "N/A"
)

// BaseSwitchInstance provides base functionality for database instance switching operations
// It contains instance metadata and common switching methods used across different database types
type BaseSwitchInstance struct {
	// The switch ID corresponds to a switch request
	SwitchID string

	// The action scope of the switch task
	ActionScope hamodel.ActionScopeType

	// The following are instance metadata information from DBM
	IP           string
	Port         int
	Status       dbm.DbmMetadataStatus
	BkCloudID    int
	BkIdcCityID  int
	BkBizID      int
	Cluster      string
	ClusterID    int
	ClusterType  haprobe.DbmMetadataClusterType
	MachineType  haprobe.DbmMetadataMachineType
	InstanceRole dbm.DbmMetadataInstanceRole

	// Http client for DBM
	DbmClient *dbm.Client
	// loggers for recording switch operation
	switchLoggers []switchlogger.DbSwitchLogger
}

// GetStatus returns the current status of the instance
func (sw *BaseSwitchInstance) GetStatus() dbm.DbmMetadataStatus {
	return sw.Status
}

// GetApp returns the business ID as string
func (sw *BaseSwitchInstance) GetApp() string {
	return strconv.Itoa(sw.BkBizID)
}

// GetInstanceRole returns the role of this instance
func (sw *BaseSwitchInstance) GetInstanceRole() dbm.DbmMetadataInstanceRole {
	return dbm.DbmMetadataInstanceRole(InstanceRoleNotAvailable)
}

// GetInstanceInfo returns formatted instance information string
func (sw *BaseSwitchInstance) GetInstanceInfo() string {
	infoStr := fmt.Sprintf("{bk_cloud_id:%d, ip:%s, port:%d, bk_idc_city_id:%d, bk_biz_id:%d, status:%s, "+
		"cluster:%s, cluster_id:%d, cluster_type:%s, machine_type:%s, role:%s}",
		sw.BkCloudID, sw.IP, sw.Port, sw.BkIdcCityID, sw.BkBizID, sw.Status, sw.Cluster,
		sw.ClusterID, sw.ClusterType, sw.MachineType, sw.InstanceRole)
	return infoStr
}

// GetBkCloudID returns the cloud ID of the instance.
func (sw *BaseSwitchInstance) GetBkCloudID() int {
	return sw.BkCloudID
}

// GetCluster returns the cluster name of the instance.
func (sw *BaseSwitchInstance) GetCluster() string {
	return sw.Cluster
}

// GetClusterID returns the cluster ID of the instance.
func (sw *BaseSwitchInstance) GetClusterID() int {
	return sw.ClusterID
}

// GetIP returns the instance IP.
func (sw *BaseSwitchInstance) GetIP() string {
	return sw.IP
}

// GetPort returns the instance port.
func (sw *BaseSwitchInstance) GetPort() int {
	return sw.Port
}

// SetSwitchID sets the switch request ID.
func (sw *BaseSwitchInstance) SetSwitchID(switchID string) {
	sw.SwitchID = switchID
}

// SetActionScope sets the action scope of the switch task.
func (sw *BaseSwitchInstance) SetActionScope(actionScope hamodel.ActionScopeType) {
	sw.ActionScope = actionScope
}

// SetInstanceUnavailable marks the instance as unavailable
func (sw *BaseSwitchInstance) SetInstanceUnavailable() error {
	err := sw.DbmClient.UpdateInstanceStatus(sw.BkCloudID, sw.IP, sw.Port, dbm.Unavailable)
	return err
}

func (sw *BaseSwitchInstance) releaseDNSEntry(dnsEntries []dbm.BindEntryDnsInfo) bool {
	allSuccess := true
	if len(dnsEntries) == 0 {
		sw.ReportLog(switchlogger.SwitchInfo, "no dns entry to release")
		return allSuccess
	}

	for _, dns := range dnsEntries {
		if (sw.MachineType == haprobe.DbmMetadataMachineTypeProxy) ||
			(sw.MachineType == haprobe.DbmMetadataMachineTypeSpider) {
			addressNum, err := sw.DbmClient.GetAddressNumberOfDomain(sw.BkCloudID, dns.DomainName)
			if err != nil {
				sw.ReportLogf(switchlogger.SwitchWarn, "failed to get address number of domain (%s): %s",
					dns.DomainName, err.Error())
				allSuccess = false
				continue
			}
			sw.ReportLogf(switchlogger.SwitchInfo, "found %d addresses in domain (%s)", addressNum, dns.DomainName)
			if addressNum <= 1 {
				sw.ReportLogf(switchlogger.SwitchWarn, "only single address in domain (%s), skip this release", dns.DomainName)
				continue
			}
		}

		for _, ip := range dns.BindIps {
			if ip != sw.IP || dns.BindPort != sw.Port {
				continue
			}

			ins := fmt.Sprintf("%s#%d", ip, dns.BindPort)
			err := sw.DbmClient.DeleteFromDomain(sw.BkCloudID, dns.DomainName, ins, sw.GetApp())
			if err == nil {
				sw.ReportLogf(switchlogger.SwitchInfo, "successfully delete this instance(%s) from domain(%s)",
					ins, dns.DomainName)
				break
			}

			sw.ReportLogf(switchlogger.SwitchWarn, "failed to delete this instance(%s) from domain(%s): %s",
				ins, dns.DomainName, err.Error())
			allSuccess = false
			break
		}
	}

	if allSuccess {
		sw.ReportLog(switchlogger.SwitchInfo, "successfully release this instance from all dns entries")
	}

	return allSuccess
}

func (sw *BaseSwitchInstance) releaseCLBEntry(clbEntries []dbm.BindEntryClbInfo) bool {
	allSuccess := true
	if clbEntries == nil {
		sw.ReportLog(switchlogger.SwitchInfo, "no clb entry to release")
		return allSuccess
	}

	for _, clb := range clbEntries {
		for _, ip := range clb.BindIps {
			if ip != sw.IP || clb.BindPort != sw.Port {
				continue
			}

			ins := fmt.Sprintf("%s:%d", ip, clb.BindPort)
			err := sw.DbmClient.DeleteFromCLB(
				sw.BkCloudID, clb.Region, clb.LoadBalanceId, clb.ListenId, ins,
			)
			if err == nil {
				sw.ReportLogf(switchlogger.SwitchInfo, "successfully delete %s from clb(%s:%s:%s)",
					ins, clb.Region, clb.LoadBalanceId, clb.ListenId)
				break
			}

			sw.ReportLogf(switchlogger.SwitchWarn, "failed to delete %s from clb(%s:%s:%s): %s",
				ins, clb.Region, clb.LoadBalanceId, clb.ListenId, err.Error())
			allSuccess = false
			break
		}
	}

	if allSuccess {
		sw.ReportLog(switchlogger.SwitchInfo, "successfully release this instance from all clb entries")
	}

	return allSuccess
}

func (sw *BaseSwitchInstance) releasePolarisEntry(polarisEntries []dbm.BindEntryPolarisInfo) bool {
	allSuccess := true
	if polarisEntries == nil {
		sw.ReportLog(switchlogger.SwitchInfo, "no polaris entry to release")
		return allSuccess
	}

	for _, pinfo := range polarisEntries {
		for _, ip := range pinfo.BindIps {
			if ip != sw.IP || pinfo.BindPort != sw.Port {
				continue
			}

			ins := fmt.Sprintf("%s:%d", ip, pinfo.BindPort)
			err := sw.DbmClient.DeleteFromPolaris(
				sw.BkCloudID, pinfo.Service, pinfo.Token, ins,
			)
			if err == nil {
				sw.ReportLogf(switchlogger.SwitchInfo, "successfully delete (%s) from polaris %s:%s",
					ins, pinfo.Service, pinfo.Token)
				break
			}

			sw.ReportLogf(switchlogger.SwitchWarn, "failed to delete (%s) from polaris %s:%s: %s",
				ins, pinfo.Service, pinfo.Token, err.Error())
			allSuccess = false
			break
		}
	}

	if allSuccess {
		sw.ReportLog(switchlogger.SwitchInfo, "successfully release this instance from all polaris entries")
	}

	return allSuccess
}

// DeleteNameService removes broken-down instance from DNS, CLB, and Polaris entries
// This is only applicable for proxy nodes
func (sw *BaseSwitchInstance) DeleteNameService(entry dbm.DbmMetadataBindEntry) error {
	dnsFlag := sw.releaseDNSEntry(entry.DNS)
	clbFlag := sw.releaseCLBEntry(entry.CLB)
	polarisFlag := sw.releasePolarisEntry(entry.Polaris)

	if !(dnsFlag && clbFlag && polarisFlag) {
		return gerrors.New(gerrors.Failure, "failed to release this instance from all entries")
	}

	sw.ReportLog(switchlogger.SwitchInfo, "successfully release this instance from all entries")
	return nil
}

// UpdateMetaInfo updates metadata information for the instance
func (sw *BaseSwitchInstance) UpdateMetaInfo() error {
	return nil
}

// RollBack performs rollback operations for the switching process
func (sw *BaseSwitchInstance) RollBack() error {
	return nil
}

// CheckBeforeSwitch performs pre-switch validation checks
func (sw *BaseSwitchInstance) CheckBeforeSwitch() (SwitchCheckCode, error) {
	return SwitchRequired, nil
}

// DoFinal executes final operations after successful switching
func (sw *BaseSwitchInstance) DoFinal() error {
	return nil
}

// SetSwitchLogger sets the logger for recording switching operations
func (sw *BaseSwitchInstance) SetSwitchLogger(loggers []switchlogger.DbSwitchLogger) {
	sw.switchLoggers = loggers
}

// ReportLog records switching operation logs with specified level
func (sw *BaseSwitchInstance) ReportLog(level switchlogger.SwitchLogLevel, message string) bool {
	logTime := time.Now()
	logRecord := hamodel.DbSwitchingLog{
		SwitchID:    sw.SwitchID,
		ActionScope: string(sw.ActionScope),
		BkBizID:     sw.BkBizID,
		BkCloudID:   sw.BkCloudID,
		DbIP:        sw.IP,
		DbPort:      sw.Port,
		ClusterID:   sw.ClusterID,
		ClusterName: sw.Cluster,
		DbTypeName:  string(sw.MachineType),
		Level:       string(level),
		Content:     message,
		CreatedTime: logTime,
	}

	// use default logger if no logger is provided
	if len(sw.switchLoggers) == 0 {
		sw.switchLoggers = []switchlogger.DbSwitchLogger{switchlogger.NewLogToStdHandler()}
		logger.Info("no switch loggers provided for instance(%s:%d), using default logger for switch log",
			sw.IP, sw.Port)
	}

	for _, swlogger := range sw.switchLoggers {
		if logErr := swlogger.Append(&logRecord); logErr != nil {
			logger.Warn("failed to append switch log record, inst: %d:%s:%d, err: %s",
				sw.BkCloudID, sw.IP, sw.Port, logErr.Error())
		}
	}
	return true
}

// ReportLogf records formatted switching operation logs
func (sw *BaseSwitchInstance) ReportLogf(level switchlogger.SwitchLogLevel, format string, args ...any) bool {
	return sw.ReportLog(level, fmt.Sprintf(format, args...))
}

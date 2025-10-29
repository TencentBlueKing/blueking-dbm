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
	"encoding/json"
	"fmt"
	"strconv"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
)

const (
	InstanceRoleNotAvailable string = "N/A"
)

type SwitchLogLevel string

// switch log level
const (
	SwitchInfo    SwitchLogLevel = "info"
	SwitchWarn    SwitchLogLevel = "warn"
	SwitchFail    SwitchLogLevel = "failed"
	SwitchSuccess SwitchLogLevel = "success"
)

// BaseSwitchInstance provides base functionality for database instance switching operations
// It contains instance metadata and common switching methods used across different database types
type BaseSwitchInstance struct {
	// The following are instance metadata information from DBM

	Ip           string
	Port         int
	Status       hamodel.DbmMetadataStatus
	BkCloudID    int
	BkIdcCityID  int
	BkBizID      int
	Cluster      string
	ClusterID    int
	ClusterType  hamodel.DbmMetadataClusterType
	MachineType  hamodel.DbmMetadataMachineType
	InstanceRole hamodel.DbmMetadataInstanceRole

	// Http client for DBM
	dbmClient *DbmClient
}

// GetStatus returns the current status of the instance
func (sw *BaseSwitchInstance) GetStatus() hamodel.DbmMetadataStatus {
	return sw.Status
}

// GetApp returns the business ID as string
func (sw *BaseSwitchInstance) GetApp() string {
	return strconv.Itoa(sw.BkBizID)
}

// GetInstanceRole returns the role of this instance
func (sw *BaseSwitchInstance) GetInstanceRole() hamodel.DbmMetadataInstanceRole {
	return hamodel.DbmMetadataInstanceRole(InstanceRoleNotAvailable)
}

// GetInstanceInfo returns formatted instance information string
func (sw *BaseSwitchInstance) GetInstanceInfo() string {
	infoStr := fmt.Sprintf("{bk_cloud_id:%d, ip:%s, port:%d, bk_idc_city_id:%d, bk_biz_id:%d, status:%s, "+
		"cluster:%s, cluster_id:%d, cluster_type:%s, machine_type:%s, role:%s}",
		sw.BkCloudID, sw.Ip, sw.Port, sw.BkIdcCityID, sw.BkBizID, sw.Status, sw.Cluster,
		sw.ClusterID, sw.ClusterType, sw.MachineType, sw.InstanceRole)
	return infoStr
}

// SetInstanceUnavailable marks the instance as unavailable
func (sw *BaseSwitchInstance) SetInstanceUnavailable() error {
	err := sw.dbmClient.UpdateInstanceStatus(sw.Ip, sw.Port, hamodel.UNAVAILABLE)
	return err
}

func (sw *BaseSwitchInstance) releaseDNSEntry(dnsEntries []hamodel.BindEntryDnsInfo) bool {
	allSuccess := true
	if dnsEntries == nil {
		return allSuccess
	}

	sw.ReportLog(SwitchInfo, fmt.Sprintf("try to release dns entry (%s:%d)", sw.Ip, sw.Port))
	for _, dns := range dnsEntries {
		if (sw.MachineType == hamodel.DbmMetadataMachineTypeProxy) ||
			(sw.MachineType == hamodel.DbmMetadataMachineTypeSpider) {
			addressNum, err := sw.dbmClient.GetAddressNumberOfDomain(dns.DomainName)
			if err != nil {
				sw.ReportLog(SwitchFail,
					fmt.Sprintf("failed to get address number of domain (%s): %v", dns.DomainName, err))
				allSuccess = false
				continue
			}
			sw.ReportLog(SwitchInfo, fmt.Sprintf("found %d addresses in domain (%s)",
				addressNum, dns.DomainName))
			if addressNum <= 1 {
				sw.ReportLog(SwitchWarn,
					fmt.Sprintf("only single address in domain (%s), skip release domain", dns.DomainName))
				continue
			}
		}
		for _, ip := range dns.BindIps {
			if ip != sw.Ip || dns.BindPort != sw.Port {
				continue
			}

			ins := fmt.Sprintf("%s#%d", ip, dns.BindPort)
			err := sw.dbmClient.DeleteFromDomain(dns.DomainName, ins, sw.GetApp())
			if err != nil {
				sw.ReportLog(SwitchFail, fmt.Sprintf("delete ip(%s) from domain(%s) failed: %s",
					ip, dns.DomainName, err.Error()))
				allSuccess = false
			}
			break
		}
	}
	if allSuccess {
		sw.ReportLog(SwitchInfo, fmt.Sprintf("release dns entry success (%s:%d)", sw.Ip, sw.Port))
	}

	return allSuccess
}

func (sw *BaseSwitchInstance) releaseCLBEntry(clbEntries []hamodel.BindEntryClbInfo) bool {
	allSuccess := true
	if clbEntries == nil {
		return allSuccess
	}

	sw.ReportLog(SwitchInfo, fmt.Sprintf("try to release clb entry (%s:%d)", sw.Ip, sw.Port))
	for _, clb := range clbEntries {
		for _, ip := range clb.BindIps {
			if ip != sw.Ip || clb.BindPort != sw.Port {
				continue
			}

			ins := fmt.Sprintf("%s:%d", ip, clb.BindPort)
			err := sw.dbmClient.DeleteFromCLB(
				clb.Region, clb.LoadBalanceId, clb.ListenId, ins,
			)
			if err != nil {
				sw.ReportLog(SwitchFail,
					fmt.Sprintf("delte %s from clb(%s:%s:%s) failed: %s",
						ins, clb.Region, clb.LoadBalanceId, clb.ListenId, err.Error()))
				allSuccess = false
			}
			break
		}
	}
	if allSuccess {
		sw.ReportLog(SwitchInfo, fmt.Sprintf("release clb entry success (%s:%d)", sw.Ip, sw.Port))
	}

	return allSuccess
}

func (sw *BaseSwitchInstance) releasePolarisEntry(polarisEntries []hamodel.BindEntryPolarisInfo) bool {
	allSuccess := true
	if polarisEntries == nil {
		return allSuccess
	}

	sw.ReportLog(SwitchInfo, fmt.Sprintf("try to release polaris entry (%s:%d)", sw.Ip, sw.Port))
	for _, pinfo := range polarisEntries {
		for _, ip := range pinfo.BindIps {
			if ip != sw.Ip || pinfo.BindPort != sw.Port {
				continue
			}

			ins := fmt.Sprintf("%s:%d", ip, pinfo.BindPort)
			err := sw.dbmClient.DeleteFromPolaris(
				pinfo.Service, pinfo.Token, ins,
			)
			if err != nil {
				sw.ReportLog(SwitchFail,
					fmt.Sprintf("delete (%s) from polaris %s:%s failed: %s",
						ins, pinfo.Service, pinfo.Token, err.Error()))
				allSuccess = false
			}
			break
		}
	}
	if allSuccess {
		sw.ReportLog(SwitchInfo, fmt.Sprintf("release polaris entry success (%s:%d)", sw.Ip, sw.Port))
	}

	return allSuccess
}

// DeleteNameService removes broken-down instance from DNS, CLB, and Polaris entries
// This is only applicable for proxy nodes
func (sw *BaseSwitchInstance) DeleteNameService(entry hamodel.DbmMetadataBindEntry) error {
	dnsFlag := sw.releaseDNSEntry(entry.DNS)
	clbFlag := sw.releaseCLBEntry(entry.CLB)
	polarisFlag := sw.releasePolarisEntry(entry.Polaris)

	if !(dnsFlag && clbFlag && polarisFlag) {
		errMsg := fmt.Sprintf("Failed to release broken-down instance(%s:%d) from all entries", sw.Ip, sw.Port)
		return gerrors.New(gerrors.Failure, errMsg)
	}

	sw.ReportLog(SwitchInfo,
		fmt.Sprintf("Success to release instance(%s:%d) from all entries[dns/clb/polaris]", sw.Ip, sw.Port))
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
func (sw *BaseSwitchInstance) CheckBeforeSwitch() (bool, error) {
	return true, nil
}

// DoFinal executes final operations after successful switching
func (sw *BaseSwitchInstance) DoFinal() error {
	return nil
}

// ReportLog records switching operation logs with specified level
func (sw *BaseSwitchInstance) ReportLog(level SwitchLogLevel, message string) bool {
	logTime := time.Now()
	logRecord := hamodel.HASwitchLogs{
		App:      strconv.Itoa(sw.BkBizID),
		SwitchID: 0,
		IP:       sw.Ip,
		Port:     sw.Port,
		Result:   string(level),
		Comment:  message,
		Datetime: &logTime,
	}

	logJson, err := json.Marshal(logRecord)
	if err != nil {
		logger.Error("failed to marshal switch log record: %s", err.Error())
		return false
	}

	logger.Info("switch log: %s", string(logJson))
	return true
}

// ReportLogf records formatted switching operation logs
func (sw *BaseSwitchInstance) ReportLogf(level SwitchLogLevel, format string, args ...interface{}) bool {
	return sw.ReportLog(level, fmt.Sprintf(format, args...))
}

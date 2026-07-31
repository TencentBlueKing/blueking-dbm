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

	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
	"dbm-services/common/dbha-v2/pkg/dbtype"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// NameServiceManager handles instance entries from DNS/CLB/Polaris.
type NameServiceManager struct {
	BkCloudID   int
	IP          string
	Port        int
	MachineType haprobe.DbmMetadataMachineType
	App         string

	DbmClient *dbm.Client

	reportLogf switchlogger.SwitchLogFunc
}

// NewNameServiceManager creates a manager for an instance.
func NewNameServiceManager(bkCloudID int, ip string, port int, machineType haprobe.DbmMetadataMachineType, app string,
	dbmClient *dbm.Client, reportLogf switchlogger.SwitchLogFunc) *NameServiceManager {
	if dbmClient == nil {
		dbmClient = &dbm.Client{}
	}

	return &NameServiceManager{
		BkCloudID:   bkCloudID,
		IP:          ip,
		Port:        port,
		MachineType: machineType,
		App:         app,
		DbmClient:   dbmClient,
		reportLogf:  reportLogf,
	}
}

func (manager *NameServiceManager) logf(level switchlogger.SwitchLogLevel, format string, args ...any) {
	if manager.reportLogf != nil {
		manager.reportLogf(level, format, args...)
		return
	}
	logger.Warn(format, args...)
}

func (manager *NameServiceManager) releaseDNSEntry(dnsEntries []dbm.BindEntryDnsInfo) bool {
	allSuccess := true
	if len(dnsEntries) == 0 {
		manager.logf(switchlogger.SwitchInfo, "no dns entry to release")
		return allSuccess
	}

	for _, dns := range dnsEntries {
		if dbtype.HasDnsSingleAddressGuard(manager.MachineType) {
			addressNum, err := manager.DbmClient.GetAddressNumberOfDomain(manager.BkCloudID, dns.DomainName)
			if err != nil {
				manager.logf(switchlogger.SwitchWarn, "failed to get address number of domain (%s): %s",
					dns.DomainName, err.Error())
				allSuccess = false
				continue
			}
			manager.logf(switchlogger.SwitchInfo, "found %d addresses in domain (%s)", addressNum, dns.DomainName)
			if addressNum <= 1 {
				manager.logf(switchlogger.SwitchWarn, "only single address in domain (%s), skip this release", dns.DomainName)
				continue
			}
		}

		for _, ip := range dns.BindIps {
			if ip != manager.IP || dns.BindPort != manager.Port {
				continue
			}

			ins := fmt.Sprintf("%s#%d", ip, dns.BindPort)
			err := manager.DbmClient.DeleteFromDomain(manager.BkCloudID, dns.DomainName, ins, manager.App)
			if err == nil {
				manager.logf(switchlogger.SwitchInfo, "successfully delete this instance(%s) from domain(%s)",
					ins, dns.DomainName)
				break
			}

			manager.logf(switchlogger.SwitchWarn, "failed to delete this instance(%s) from domain(%s): %s",
				ins, dns.DomainName, err.Error())
			allSuccess = false
			break
		}
	}

	if allSuccess {
		manager.logf(switchlogger.SwitchInfo, "successfully release this instance from all dns entries")
	}

	return allSuccess
}

func (manager *NameServiceManager) releaseCLBEntry(clbEntries []dbm.BindEntryClbInfo) bool {
	allSuccess := true
	if clbEntries == nil {
		manager.logf(switchlogger.SwitchInfo, "no clb entry to release")
		return allSuccess
	}

	for _, clb := range clbEntries {
		for _, ip := range clb.BindIps {
			if ip != manager.IP || clb.BindPort != manager.Port {
				continue
			}

			ins := fmt.Sprintf("%s:%d", ip, clb.BindPort)
			err := manager.DbmClient.DeleteFromCLB(
				manager.BkCloudID, clb.Region, clb.LoadBalanceId, clb.ListenId, ins,
			)
			if err == nil {
				manager.logf(switchlogger.SwitchInfo, "successfully delete %s from clb(%s:%s:%s)",
					ins, clb.Region, clb.LoadBalanceId, clb.ListenId)
				break
			}

			manager.logf(switchlogger.SwitchWarn, "failed to delete %s from clb(%s:%s:%s): %s",
				ins, clb.Region, clb.LoadBalanceId, clb.ListenId, err.Error())
			allSuccess = false
			break
		}
	}

	if allSuccess {
		manager.logf(switchlogger.SwitchInfo, "successfully release this instance from all clb entries")
	}

	return allSuccess
}

func (manager *NameServiceManager) releasePolarisEntry(polarisEntries []dbm.BindEntryPolarisInfo) bool {
	allSuccess := true
	if polarisEntries == nil {
		manager.logf(switchlogger.SwitchInfo, "no polaris entry to release")
		return allSuccess
	}

	for _, pinfo := range polarisEntries {
		for _, ip := range pinfo.BindIps {
			if ip != manager.IP || pinfo.BindPort != manager.Port {
				continue
			}

			ins := fmt.Sprintf("%s:%d", ip, pinfo.BindPort)
			err := manager.DbmClient.DeleteFromPolaris(
				manager.BkCloudID, pinfo.Service, pinfo.Token, ins,
			)
			if err == nil {
				manager.logf(switchlogger.SwitchInfo, "successfully delete (%s) from polaris %s:%s",
					ins, pinfo.Service, pinfo.Token)
				break
			}

			manager.logf(switchlogger.SwitchWarn, "failed to delete (%s) from polaris %s:%s: %s",
				ins, pinfo.Service, pinfo.Token, err.Error())
			allSuccess = false
			break
		}
	}

	if allSuccess {
		manager.logf(switchlogger.SwitchInfo, "successfully release this instance from all polaris entries")
	}

	return allSuccess
}

// DeleteNameService removes broken-down instance from DNS, CLB, and Polaris entries.
func (manager *NameServiceManager) DeleteNameService(entry dbm.DbmMetadataBindEntry) error {
	dnsFlag := manager.releaseDNSEntry(entry.DNS)
	clbFlag := manager.releaseCLBEntry(entry.CLB)
	polarisFlag := manager.releasePolarisEntry(entry.Polaris)

	if !(dnsFlag && clbFlag && polarisFlag) {
		return gerrors.Newf(gerrors.Failure, "failed to release this instance from all entries")
	}

	manager.logf(switchlogger.SwitchInfo, "successfully release this instance from all entries")
	return nil
}

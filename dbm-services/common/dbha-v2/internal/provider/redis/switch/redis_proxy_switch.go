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

package redisswitch

import (
	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchcore"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
	"dbm-services/common/dbha-v2/pkg/gerrors"
)

var (
	_ switchcore.SwitchableInstance = (*TwemproxySwitchInstance)(nil)
	_ switchcore.SwitchableInstance = (*PredixySwitchInstance)(nil)
)

// redisGatewayInfo tracks which name-service entries a redis proxy should unbind.
type redisGatewayInfo struct {
	// DNSFlag is true when the proxy has DNS bind entries.
	DNSFlag bool
	// DNSForward is true when DNS is forwarded to another entry (usually CLB).
	// UnbindDNS should be skipped in that case.
	DNSForward bool
	// CLBFlag is true when the proxy is bound to CLB.
	CLBFlag bool
	// PolarisFlag is true when the proxy is bound to Polaris.
	PolarisFlag bool
	// bindEntry is the bind entry of the proxy in the metadata.
	bindEntry dbm.DbmMetadataBindEntry
}

// RedisProxySwitchInstance is the common proxy-layer base for redis proxy switch.
type RedisProxySwitchInstance struct {
	RedisBaseSwitchInstance

	AdminPort          int
	GatewayInfo        redisGatewayInfo
	NameServiceManager *switchcore.NameServiceManager
}

// initFromMetadata initializes the proxy switch instance from the DBM metadata.
func (ins *RedisProxySwitchInstance) initFromMetadata(metadata *dbm.DbInstMetadata) {
	ins.initBaseInfoFromMetadata(metadata)
	ins.AdminPort = metadata.AdminPort
	ins.fillGatewayInfo(metadata.BindEntry)
	ins.NameServiceManager = switchcore.NewNameServiceManager(
		ins.BkCloudID, ins.IP, ins.Port, ins.MachineType,
		ins.GetApp(), ins.DbmClient, ins.ReportLogf)
}

// fillGatewayInfo fills the gateway information from the DBM metadata.
func (ins *RedisProxySwitchInstance) fillGatewayInfo(bindEntry dbm.DbmMetadataBindEntry) {
	ins.GatewayInfo = redisGatewayInfo{
		DNSFlag:     len(bindEntry.DNS) > 0,
		DNSForward:  false,
		CLBFlag:     len(bindEntry.CLB) > 0,
		PolarisFlag: len(bindEntry.Polaris) > 0,
		bindEntry:   bindEntry,
	}

	for _, dns := range bindEntry.DNS {
		if dns.ForwardEntryId != 0 {
			ins.GatewayInfo.DNSForward = true
			break
		}
	}
}

// UnbindDNS unbinds the proxy from DNS unless DNS is unused or forwarded.
func (ins *RedisProxySwitchInstance) UnbindDNS() bool {
	if !ins.GatewayInfo.DNSFlag {
		ins.ReportLogf(switchlogger.SwitchInfo, "no dns entry to unbind")
		return true
	}

	if ins.GatewayInfo.DNSForward {
		ins.ReportLogf(switchlogger.SwitchInfo, "dns is forwarded, skip unbinding dns")
		return true
	}

	return ins.NameServiceManager.ReleaseDNSEntry(ins.GatewayInfo.bindEntry.DNS)
}

// UnbindCLB unbinds the proxy from CLB when bound.
func (ins *RedisProxySwitchInstance) UnbindCLB() bool {
	if !ins.GatewayInfo.CLBFlag {
		ins.ReportLogf(switchlogger.SwitchInfo, "no clb entry to unbind")
		return true
	}

	return ins.NameServiceManager.ReleaseCLBEntry(ins.GatewayInfo.bindEntry.CLB)
}

// UnbindPolaris unbinds the proxy from Polaris when bound.
func (ins *RedisProxySwitchInstance) UnbindPolaris() bool {
	if !ins.GatewayInfo.PolarisFlag {
		ins.ReportLogf(switchlogger.SwitchInfo, "no polaris entry to unbind")
		return true
	}

	return ins.NameServiceManager.ReleasePolarisEntry(ins.GatewayInfo.bindEntry.Polaris)
}

// unbindFromAllEntries unbinds this proxy from DNS/CLB/Polaris.
func (ins *RedisProxySwitchInstance) unbindFromAllEntries() bool {
	dnsOk := ins.UnbindDNS()
	clbOk := ins.UnbindCLB()
	polarisOk := ins.UnbindPolaris()
	return dnsOk && clbOk && polarisOk
}

// copySwitchContextFrom copies the switch context from the source instance.
func (ins *RedisProxySwitchInstance) copySwitchContextFrom(src *RedisBaseSwitchInstance) {
	ins.SetSwitchID(src.SwitchID)
	ins.SetActionScope(src.ActionScope)
	ins.SetSwitchLogger(src.GetSwitchLogger())
}

// TwemproxySwitchInstance is the twemproxy proxy-layer switchable object.
// It unbinds a broken twemproxy from name services.
type TwemproxySwitchInstance struct {
	RedisProxySwitchInstance
}

// NewTwemproxySwitchInstance creates a twemproxy switch instance from metadata.
func NewTwemproxySwitchInstance(metadata *dbm.DbInstMetadata) (*TwemproxySwitchInstance, error) {
	if metadata == nil {
		return nil, gerrors.Newf(gerrors.InvalidParameter, "nil metadata for twemproxy switch instance")
	}
	ins := &TwemproxySwitchInstance{}
	ins.initFromMetadata(metadata)
	return ins, nil
}

// CheckBeforeSwitch has nothing to check for twemproxy.
func (ins *TwemproxySwitchInstance) CheckBeforeSwitch() (switchcore.SwitchCheckCode, error) {
	return switchcore.SwitchRequired, nil
}

// DoSwitch unbinds twemproxy from DNS/CLB/Polaris.
func (ins *TwemproxySwitchInstance) DoSwitch() error {
	ins.ReportLogf(switchlogger.SwitchInfo, "switch step 1: try to delete this twemproxy from all bound entries")
	if !ins.unbindFromAllEntries() {
		return gerrors.Newf(gerrors.Failure, "failed to unbind this twemproxy from all entries")
	}

	ins.ReportLogf(switchlogger.SwitchInfo, "successfully unbound this twemproxy from all entries")
	return nil
}

// PredixySwitchInstance is the predixy proxy-layer switchable object.
// It unbinds a broken predixy from name services.
type PredixySwitchInstance struct {
	RedisProxySwitchInstance
}

// NewPredixySwitchInstance creates a predixy switch instance from metadata.
func NewPredixySwitchInstance(metadata *dbm.DbInstMetadata) (*PredixySwitchInstance, error) {
	if metadata == nil {
		return nil, gerrors.Newf(gerrors.InvalidParameter, "nil metadata for predixy switch instance")
	}
	ins := &PredixySwitchInstance{}
	ins.initFromMetadata(metadata)
	return ins, nil
}

// CheckBeforeSwitch has nothing to check for predixy.
func (ins *PredixySwitchInstance) CheckBeforeSwitch() (switchcore.SwitchCheckCode, error) {
	return switchcore.SwitchRequired, nil
}

// DoSwitch unbinds predixy from DNS/CLB/Polaris.
func (ins *PredixySwitchInstance) DoSwitch() error {
	ins.ReportLogf(switchlogger.SwitchInfo, "switch step 1: try to delete this predixy from all bound entries")
	if !ins.unbindFromAllEntries() {
		return gerrors.Newf(gerrors.Failure, "failed to unbind this predixy from all entries")
	}

	ins.ReportLogf(switchlogger.SwitchInfo, "successfully unbound this predixy from all entries")
	return nil
}

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
	"fmt"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
	"dbm-services/common/dbha-v2/pkg/monitor"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// alarmUnbindProxy posts one unbind alarm for a single proxy.
// The switch log is left unchanged; this only reports to the monitor.
func (ins *RedisStorageSwitchInstance) alarmUnbindProxy(
	machineType haprobe.DbmMetadataMachineType,
	item failedRunningProxy,
	eventName haprobe.DbEventName,
	unbindErr string,
) {
	proxy := item.proxy
	var content string
	switch eventName {
	case haprobe.DbEventNameRedisUnbindProxySuccess:
		content = fmt.Sprintf(
			"When dbha-v2 checking the storage backend, failed to query backends from this running proxy, "+
				"so unbind it from DNS/CLB/Polaris, machineType:%s, status:%s, queryErr:%s",
			machineType, proxy.Status, item.queryErr)
	case haprobe.DbEventNameRedisUnbindProxyFailure:
		content = fmt.Sprintf(
			"When dbha-v2 checking the storage backend, failed to query backends from this running proxy. Even after that, "+
				"failed to unbind it from DNS/CLB/Polaris, machineType:%s, status:%s, queryErr:%s, unbindErr:%s",
			machineType, proxy.Status, item.queryErr, unbindErr)
	default:
		ins.ReportLogf(switchlogger.SwitchWarn,
			"skip posting unbind proxy alarm, invalid event:%s, machineType:%s, ip:%s, port:%d",
			eventName, machineType, proxy.Ip, proxy.Port)
		return
	}

	target := fmt.Sprintf("%d:%s:%d", ins.BkCloudID, proxy.Ip, proxy.Port)
	monitorEvent := &monitor.EventData{
		Name:      eventName.String(),
		Target:    target,
		Timestamp: uint64(time.Now().UnixMilli()),
	}
	monitorEvent.Content.Content = content
	monitorEvent.Dimension.BkCloudId = ins.BkCloudID
	monitorEvent.Dimension.BkBizId = ins.BkBizID
	monitorEvent.Dimension.SwitchId = ins.SwitchID
	monitorEvent.Dimension.IP = proxy.Ip
	monitorEvent.Dimension.Port = proxy.Port
	monitorEvent.Dimension.DbTypeName = haprobe.DbTypeRedis
	monitorEvent.Dimension.DbEventName = eventName
	monitorEvent.Dimension.DbClusterType = ins.ClusterType
	monitorEvent.Dimension.DbMachineType = machineType
	monitorEvent.Dimension.SwitchInfoClusterDomainV1 = ins.Cluster
	monitorEvent.Dimension.SwitchInfoMachineTypeV1 = string(machineType)
	if err := monitor.PostBKMonitor(config.Cfg.Monitor.Timeout, monitorEvent); err != nil {
		ins.ReportLogf(switchlogger.SwitchWarn,
			"failed to post unbind proxy alarm, event:%s, machineType:%s, ip:%s, port:%d, errmsg:%s",
			eventName, machineType, proxy.Ip, proxy.Port, err.Error())
		return
	}
	ins.ReportLogf(switchlogger.SwitchInfo,
		"successfully posted unbind proxy alarm, event:%s, machineType:%s, ip:%s, port:%d",
		eventName, machineType, proxy.Ip, proxy.Port)
}

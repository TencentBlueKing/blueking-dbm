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

package redis

import (
	"context"
	"fmt"
	"net"
	"strings"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchcore"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	goredis "github.com/redis/go-redis/v9"
)

const (
	defaultRedisSwitchTimeout = 3 * time.Second
)

// RedisBaseSwitchInstance provides common fields and helpers for redis switching.
type RedisBaseSwitchInstance struct {
	switchcore.BaseSwitchInstance
	AccessLayer      haprobe.DbmMetadataAccessLayerType
	BindEntry        dbm.DbmMetadataBindEntry
	ProxyInstanceSet []dbm.DbmMetadataProxyInstance
	StandBySlave     *dbm.DbmMetadataSlaveInfo
}

// RedisStorageSwitchInstance handles redis/tendis storage switching.
type RedisStorageSwitchInstance struct {
	RedisBaseSwitchInstance
}

// RedisProxySwitchInstance handles redis proxy name-service offlining.
type RedisProxySwitchInstance struct {
	RedisBaseSwitchInstance
}

// NewSwitchInstance creates a redis switch instance from DBM metadata.
func NewSwitchInstance(metadata *dbm.DbInstMetadata) (switchcore.SwitchableInstance, error) {
	base := RedisBaseSwitchInstance{
		BaseSwitchInstance: switchcore.BaseSwitchInstance{
			IP:           metadata.IP,
			Port:         metadata.Port,
			Status:       metadata.Status,
			BkCloudID:    metadata.BkCloudID,
			BkIdcCityID:  metadata.BkIdcCityID,
			BkBizID:      metadata.BkBizID,
			Cluster:      metadata.Cluster,
			ClusterID:    metadata.ClusterID,
			ClusterType:  metadata.ClusterType,
			MachineType:  metadata.MachineType,
			InstanceRole: metadata.InstanceRole,
			DbmClient:    &dbm.Client{},
		},
		AccessLayer:      metadata.AccessLayer,
		BindEntry:        metadata.BindEntry,
		ProxyInstanceSet: metadata.ProxyInstanceSet,
		StandBySlave:     pickStandBySlave(metadata.Receiver),
	}

	switch metadata.AccessLayer {
	case haprobe.DbmMetadataAccessLayerTypeStorage:
		return &RedisStorageSwitchInstance{RedisBaseSwitchInstance: base}, nil
	case haprobe.DbmMetadataAccessLayerTypeProxy:
		return &RedisProxySwitchInstance{RedisBaseSwitchInstance: base}, nil
	default:
		return nil, gerrors.Newf(gerrors.InvalidParameter, "invalid redis access layer: %s", metadata.AccessLayer)
	}
}

func pickStandBySlave(slaves []dbm.DbmMetadataSlaveInfo) *dbm.DbmMetadataSlaveInfo {
	if len(slaves) == 0 {
		return nil
	}

	for _, slave := range slaves {
		if slave.IsStandBy {
			standby := slave
			return &standby
		}
	}

	standby := slaves[0]
	return &standby
}

func (sw *RedisStorageSwitchInstance) isMasterRole() bool {
	role := strings.ToLower(sw.InstanceRole.String())
	return strings.Contains(role, "master")
}

// CheckBeforeSwitch checks whether current instance requires redis switching.
func (sw *RedisStorageSwitchInstance) CheckBeforeSwitch() (switchcore.SwitchCheckCode, error) {
	if !sw.isMasterRole() {
		sw.ReportLogf(switchlogger.SwitchInfo, "storage role is not master, no need to switch, role: %s", sw.InstanceRole)
		return switchcore.SwitchNotNeeded, nil
	}

	if sw.StandBySlave == nil {
		err := gerrors.New(gerrors.Failure, "no standby slave found for redis master")
		sw.ReportLogf(switchlogger.SwitchWarn, "%s", err.Error())
		return switchcore.SwitchCheckUnpass, err
	}

	if sw.StandBySlave.Status == dbm.Unavailable {
		err := gerrors.Newf(
			gerrors.Failure,
			"standby slave is unavailable, slave: %s:%d",
			sw.StandBySlave.Ip,
			sw.StandBySlave.Port,
		)
		sw.ReportLogf(switchlogger.SwitchWarn, "%s", err.Error())
		return switchcore.SwitchCheckUnpass, err
	}

	return switchcore.SwitchRequired, nil
}

// DoSwitch promotes standby slave and updates twemproxy backend mapping when needed.
func (sw *RedisStorageSwitchInstance) DoSwitch() error {
	if sw.StandBySlave == nil {
		return gerrors.New(gerrors.Failure, "standby slave is nil in redis switch")
	}

	if err := sw.promoteStandBy(); err != nil {
		return err
	}

	if !sw.isTwemproxyCluster() {
		return nil
	}

	return sw.switchTwemproxyBackends()
}

func (sw *RedisStorageSwitchInstance) promoteStandBy() error {
	ctx, cancel := context.WithTimeout(context.Background(), defaultRedisSwitchTimeout)
	defer cancel()

	addr := net.JoinHostPort(sw.StandBySlave.Ip, fmt.Sprintf("%d", sw.StandBySlave.Port))
	cli := goredis.NewClient(&goredis.Options{
		Addr:         addr,
		DialTimeout:  defaultRedisSwitchTimeout,
		ReadTimeout:  defaultRedisSwitchTimeout,
		WriteTimeout: defaultRedisSwitchTimeout,
		PoolSize:     1,
		MinIdleConns: 0,
	})
	defer cli.Close()

	if err := cli.Ping(ctx).Err(); err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to ping standby slave(%s), errmsg: %s", addr, err.Error())
	}

	if err := cli.SlaveOf(ctx, "NO", "ONE").Err(); err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to promote standby slave(%s), errmsg: %s", addr, err.Error())
	}

	sw.ReportLogf(switchlogger.SwitchInfo, "promoted standby slave to master, slave: %s", addr)
	return nil
}

func (sw *RedisStorageSwitchInstance) isTwemproxyCluster() bool {
	return sw.ClusterType == haprobe.DbmMetadataClusterTypeTwemproxyRedis ||
		sw.ClusterType == haprobe.DbmMetadataClusterTypeTwemproxyTendisSSD
}

func (sw *RedisStorageSwitchInstance) switchTwemproxyBackends() error {
	if len(sw.ProxyInstanceSet) == 0 {
		sw.ReportLogf(switchlogger.SwitchInfo, "no twemproxy instance found, skip backend switch")
		return nil
	}

	oldMaster := fmt.Sprintf("%s:%d", sw.IP, sw.Port)
	newMaster := fmt.Sprintf("%s:%d", sw.StandBySlave.Ip, sw.StandBySlave.Port)
	command := fmt.Sprintf("change nosqlproxy %s %s\r\n", oldMaster, newMaster)

	for _, proxy := range sw.ProxyInstanceSet {
		if proxy.AdminPort <= 0 {
			continue
		}

		proxyAddr := net.JoinHostPort(proxy.Ip, fmt.Sprintf("%d", proxy.AdminPort))
		conn, err := net.DialTimeout("tcp", proxyAddr, defaultRedisSwitchTimeout)
		if err != nil {
			return gerrors.Newf(gerrors.Failure, "failed to connect twemproxy(%s), errmsg: %s", proxyAddr, err.Error())
		}

		if err = conn.SetDeadline(time.Now().Add(defaultRedisSwitchTimeout)); err != nil {
			_ = conn.Close()
			return gerrors.Newf(gerrors.Failure, "failed to set twemproxy deadline, errmsg: %s", err.Error())
		}

		if _, err = conn.Write([]byte(command)); err != nil {
			_ = conn.Close()
			return gerrors.Newf(gerrors.Failure, "failed to write twemproxy command, errmsg: %s", err.Error())
		}

		resp := make([]byte, 1024)
		n, err := conn.Read(resp)
		_ = conn.Close()
		if err != nil {
			return gerrors.Newf(gerrors.Failure, "failed to read twemproxy response, errmsg: %s", err.Error())
		}

		respStr := string(resp[:n])
		sw.ReportLogf(
			switchlogger.SwitchInfo,
			"twemproxy backend switch response, proxy: %s, response: %s",
			proxyAddr,
			respStr,
		)
	}

	return nil
}

// UpdateMetaInfo updates DBM metadata for redis/tendis master-slave role swap.
func (sw *RedisStorageSwitchInstance) UpdateMetaInfo() error {
	if sw.StandBySlave == nil {
		return nil
	}

	return sw.DbmClient.SwapTendisCluster(
		sw.BkCloudID,
		sw.Cluster,
		sw.IP,
		sw.Port,
		sw.StandBySlave.Ip,
		sw.StandBySlave.Port,
	)
}

// RollBack is currently a no-op for redis switching flow.
func (sw *RedisStorageSwitchInstance) RollBack() error {
	return nil
}

// CheckBeforeSwitch always allows proxy offlining after switchcore checks.
func (sw *RedisProxySwitchInstance) CheckBeforeSwitch() (switchcore.SwitchCheckCode, error) {
	return switchcore.SwitchRequired, nil
}

// DoSwitch removes the proxy endpoint from nameservice entries.
func (sw *RedisProxySwitchInstance) DoSwitch() error {
	return sw.DeleteNameService(sw.BindEntry)
}

// UpdateMetaInfo keeps metadata unchanged for proxy offlining.
func (sw *RedisProxySwitchInstance) UpdateMetaInfo() error {
	return nil
}

// RollBack is currently a no-op for redis proxy switching.
func (sw *RedisProxySwitchInstance) RollBack() error {
	return nil
}

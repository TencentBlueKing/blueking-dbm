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
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// NewSwitchInstance creates a Redis switch instance according to the provided metadata.
func NewSwitchInstance(metadata *dbm.DbInstMetadata, switchID string, actionScope hamodel.ActionScopeType) (
	switchableInstance switchcore.SwitchableInstance, retErr error) {

	if metadata == nil {
		return nil, gerrors.Newf(gerrors.InvalidParameter, "nil metadata for redis switch instance")
	}

	switch metadata.ClusterType {
	case haprobe.DbmMetadataClusterTypeRedis: // RedisInstance
		switchableInstance, retErr = NewRedisInstanceSwitchInstance(metadata)

	case haprobe.DbmMetadataClusterTypeTwemproxyRedis: // TwemproxyRedisInstance
		switchableInstance, retErr = NewTwemproxyRedisInstanceSwitchInstance(metadata)

	case haprobe.DbmMetadataClusterTypeTwemproxyTendisSSD: // TwemproxyTendisSSDInstance
		switchableInstance, retErr = NewTwemproxyTendisSSDInstanceSwitchInstance(metadata)

	case haprobe.DbmMetadataClusterTypePredixyRedisCluster: // PredixyRedisCluster
		switchableInstance, retErr = NewPredixyRedisClusterSwitchInstance(metadata)

	case haprobe.DbmMetadataClusterTypePredixyTendisplusCluster: // PredixyTendisplusCluster
		switchableInstance, retErr = NewPredixyTendisplusClusterSwitchInstance(metadata)

	case haprobe.DbmMetadataClusterTypePredixyTendisplusInstance: // PredixyTendisplusInstance
		switchableInstance, retErr = NewPredixyTendisplusInstanceSwitchInstance(metadata)

	default:
		return nil, gerrors.Newf(gerrors.Failure, "unsupported cluster type: %s", metadata.ClusterType)
	}

	if retErr != nil {
		return nil, retErr
	}

	switchableInstance.SetSwitchID(switchID)
	switchableInstance.SetActionScope(actionScope)
	return switchableInstance, nil
}

// Cluster constructors only compose reusable storage/proxy switch objects by machine type.
// Layer implementations live in redis_storage_switch.go and redis_proxy_switch.go.

// asSwitchable converts a concrete instance to SwitchableInstance without a typed-nil interface.
func asSwitchable(ins switchcore.SwitchableInstance, err error) (switchcore.SwitchableInstance, error) {
	if err != nil {
		return nil, err
	}
	return ins, nil
}

// NewRedisInstanceSwitchInstance creates a switch instance for RedisInstance cluster.
func NewRedisInstanceSwitchInstance(metadata *dbm.DbInstMetadata) (switchcore.SwitchableInstance, error) {
	switch metadata.MachineType {
	case haprobe.DbmMetadataMachineTypeTendisCache:
		return asSwitchable(NewRedisStorageSwitchInstance(metadata))

	default:
		logger.Error("unknown machine type for RedisInstance switch instance constructor: %s", metadata.MachineType)
		return nil, gerrors.Newf(gerrors.InvalidParameter, "invalid machine type: %s", metadata.MachineType)
	}
}

// NewTwemproxyRedisInstanceSwitchInstance creates a switch instance for TwemproxyRedisInstance cluster.
func NewTwemproxyRedisInstanceSwitchInstance(metadata *dbm.DbInstMetadata) (switchcore.SwitchableInstance, error) {
	switch metadata.MachineType {
	case haprobe.DbmMetadataMachineTypeTwemProxy:
		return asSwitchable(NewTwemproxySwitchInstance(metadata))

	case haprobe.DbmMetadataMachineTypeTendisCache:
		return asSwitchable(NewRedisStorageSwitchInstance(metadata))

	default:
		logger.Error("unknown machine type for TwemproxyRedisInstance switch instance constructor: %s",
			metadata.MachineType)
		return nil, gerrors.Newf(gerrors.InvalidParameter, "invalid machine type: %s", metadata.MachineType)
	}
}

// NewTwemproxyTendisSSDInstanceSwitchInstance creates a switch instance for TwemproxyTendisSSDInstance cluster.
func NewTwemproxyTendisSSDInstanceSwitchInstance(metadata *dbm.DbInstMetadata) (switchcore.SwitchableInstance, error) {
	switch metadata.MachineType {
	case haprobe.DbmMetadataMachineTypeTwemProxy:
		return asSwitchable(NewTwemproxySwitchInstance(metadata))

	case haprobe.DbmMetadataMachineTypeTendisSSD:
		return asSwitchable(NewRedisStorageSwitchInstance(metadata))

	default:
		logger.Error("unknown machine type for TwemproxyTendisSSDInstance switch instance constructor: %s",
			metadata.MachineType)
		return nil, gerrors.Newf(gerrors.InvalidParameter, "invalid machine type: %s", metadata.MachineType)
	}
}

// NewPredixyRedisClusterSwitchInstance creates a switch instance for PredixyRedisCluster.
func NewPredixyRedisClusterSwitchInstance(metadata *dbm.DbInstMetadata) (switchcore.SwitchableInstance, error) {
	switch metadata.MachineType {
	case haprobe.DbmMetadataMachineTypePredixy:
		return asSwitchable(NewPredixySwitchInstance(metadata))

	case haprobe.DbmMetadataMachineTypeTendisCache:
		return asSwitchable(NewRedisStorageSwitchInstance(metadata))

	default:
		logger.Error("unknown machine type for PredixyRedisCluster switch instance constructor: %s",
			metadata.MachineType)
		return nil, gerrors.Newf(gerrors.InvalidParameter, "invalid machine type: %s", metadata.MachineType)
	}
}

// NewPredixyTendisplusClusterSwitchInstance creates a switch instance for PredixyTendisplusCluster.
func NewPredixyTendisplusClusterSwitchInstance(metadata *dbm.DbInstMetadata) (switchcore.SwitchableInstance, error) {
	switch metadata.MachineType {
	case haprobe.DbmMetadataMachineTypePredixy:
		return asSwitchable(NewPredixySwitchInstance(metadata))

	case haprobe.DbmMetadataMachineTypeTendisPlus:
		return asSwitchable(NewRedisStorageSwitchInstance(metadata))

	default:
		logger.Error("unknown machine type for PredixyTendisplusCluster switch instance constructor: %s",
			metadata.MachineType)
		return nil, gerrors.Newf(gerrors.InvalidParameter, "invalid machine type: %s", metadata.MachineType)
	}
}

// NewPredixyTendisplusInstanceSwitchInstance creates a switch instance for PredixyTendisplusInstance.
// Architecture: predixy + tendisplus master-slave (StandaloneServerPool).
func NewPredixyTendisplusInstanceSwitchInstance(metadata *dbm.DbInstMetadata) (switchcore.SwitchableInstance, error) {
	switch metadata.MachineType {
	case haprobe.DbmMetadataMachineTypePredixy:
		return asSwitchable(NewPredixySwitchInstance(metadata))

	case haprobe.DbmMetadataMachineTypeTendisPlus:
		return asSwitchable(NewRedisStorageSwitchInstance(metadata))

	default:
		logger.Error("unknown machine type for PredixyTendisplusInstance switch instance constructor: %s",
			metadata.MachineType)
		return nil, gerrors.Newf(gerrors.InvalidParameter, "invalid machine type: %s", metadata.MachineType)
	}
}

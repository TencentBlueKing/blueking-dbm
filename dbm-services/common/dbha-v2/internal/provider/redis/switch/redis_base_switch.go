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
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchcore"
	redispasswd "dbm-services/common/dbha-v2/internal/provider/redis/passwd"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// RedisBaseSwitchInstance holds common redis storage/proxy switch fields filled from DBM metadata.
type RedisBaseSwitchInstance struct {
	switchcore.BaseSwitchInstance

	Password         string
	passwordResolved bool          // indicates whether the password has been resolved
	Timeout          time.Duration // timeout for redis commands execution
}

// initBaseInfoFromMetadata initializes the base information from the DBM metadata.
func (sw *RedisBaseSwitchInstance) initBaseInfoFromMetadata(metadata *dbm.DbInstMetadata) {
	sw.IP = metadata.IP
	sw.Port = metadata.Port
	sw.Status = metadata.Status
	sw.BkCloudID = metadata.BkCloudID
	sw.BkIdcCityID = metadata.BkIdcCityID
	sw.BkBizID = metadata.BkBizID
	sw.Cluster = metadata.Cluster
	sw.ClusterID = metadata.ClusterID
	sw.ClusterType = metadata.ClusterType
	sw.MachineType = metadata.MachineType
	sw.InstanceRole = metadata.InstanceRole
	sw.DbmClient = &dbm.Client{}
	sw.Timeout = redisCommandTimeout()
}

// applyPassword prefetches the password while the instance is being built.
func (sw *RedisBaseSwitchInstance) applyPassword(machineType haprobe.DbmMetadataMachineType) {
	passwd, err := redispasswd.GetDbInstPasswd(sw.BkCloudID, sw.ClusterID, machineType)
	if err != nil {
		logger.Error("get redis switch passwd failed,err:%s,info:%s", err.Error(), sw.GetInstanceInfo())
		return
	}
	sw.Password = passwd
	sw.passwordResolved = true
}

// ensurePassword resolves the password right before it is used.
func (sw *RedisBaseSwitchInstance) ensurePassword() error {
	if sw.passwordResolved {
		return nil
	}

	passwd, err := redispasswd.GetDbInstPasswd(sw.BkCloudID, sw.ClusterID, sw.MachineType)
	if err != nil {
		return err
	}

	sw.Password = passwd
	sw.passwordResolved = true
	return nil
}

// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package monitoriteminterface

import (
	"dbm-services/riak/db-tools/riak-monitor/pkg/config"
	"dbm-services/riak/db-tools/riak-monitor/pkg/internal/cst"
	"dbm-services/riak/db-tools/riak-monitor/pkg/utils"
	"fmt"
	"strings"
	"time"

	"golang.org/x/exp/slog"
)

// ConnectionCollect DB连接对象
type ConnectionCollect struct {
}

// NewConnectionCollect 新建连接
func NewConnectionCollect() (*ConnectionCollect, error) {
	if config.MonitorConfig.MachineType == cst.RiakMachineType {
		err := ConnectDB(
			config.MonitorConfig.Ip,
		)
		if err != nil {
			slog.Error(
				fmt.Sprintf("connect error: %s", config.MonitorConfig.MachineType), err,
				slog.String("ip", config.MonitorConfig.Ip),
				slog.Int("port", config.MonitorConfig.Port),
			)
			return nil, err
		}
	}
	return nil, nil
}

func ConnectDB(ip string) error {
	recheck := 1
	var riakErr error
	for i := 0; i <= recheck; i++ {
		// 设置缓冲为1防止没有接收者导致阻塞，即Detection已经超时返回
		errChan := make(chan error, 2)
		// 这里存在资源泄露的可能，因为不能主动kill掉协程，所以如果这个协程依然阻塞在连接riak，但是
		// 这个函数已经超时返回了，那么这个协程因为被阻塞一直没被释放，直到Riak连接超时，如果阻塞的时间
		// 大于下次探测该实例的时间间隔，则创建协程频率大于释放协程频率，可能会导致oom。可以考虑在Riak
		// 客户端连接设置超时时间来防止。
		go CheckRiak(ip, int(config.MonitorConfig.InteractTimeout.Seconds()), errChan)
		select {
		case riakErr = <-errChan:
			if riakErr != nil {
				slog.Error(fmt.Sprintf("The Node is out of service:%s.", riakErr.Error()))
			} else {
				return nil
			}
		case <-time.After(config.MonitorConfig.InteractTimeout):
			slog.Error(fmt.Sprintf("Connect Riak timeout recheck:%d", recheck))
			riakErr = fmt.Errorf(`['riak@%s'] down`, ip)
		}
	}
	return riakErr
}

// CheckRiak check whether riak alive
func CheckRiak(ip string, timeout int, errChan chan error) {
	foundNothing := "riak down, query heartbeat nothing return"
	down := fmt.Errorf(`['riak@%s'] down`, ip)
	query := fmt.Sprintf(`curl -s --connect-timeout %d -m %d http://%s:%d/types/default/buckets/test/keys/1000`,
		timeout, timeout, ip, cst.RiakHttpPort)
	insert := fmt.Sprintf(
		`%s -X PUT -H 'Content-Type: application/json' -d '{name: "DBATeam", members: 31}'`, query)
	_, err := utils.ExecShellCommand(false, insert)
	if err != nil {
		slog.Warn(fmt.Sprintf("Execute [ %s ] error: %s.", insert, err.Error()))
		errChan <- down
		return
	}
	stdout, err := utils.ExecShellCommand(false, query)
	if err != nil {
		slog.Warn(fmt.Sprintf(" Execute [ %s ] error: %s", query, err.Error()))
		errChan <- down
		return
	} else if strings.Contains(stdout, "not found") {
		slog.Warn(fmt.Sprintf("%s. Execute [ %s ]", foundNothing, query))
		errChan <- down
		return
	}
	errChan <- nil
}

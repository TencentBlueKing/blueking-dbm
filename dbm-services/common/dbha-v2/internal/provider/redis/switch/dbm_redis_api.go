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
	"encoding/json"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
)

// SwapRedisRoleInstance represents a single Redis instance for role swapping
type SwapRedisRoleInstance struct {
	IP   string `json:"ip"`
	Port int    `json:"port"`
}

// SwapRedisRolePayload contains the master-slave pair and cluster domain for role swapping.
// Note: master and slave should be a Redis master-slave pair.
// master should be the current redis master, slave should be the current redis slave.
type SwapRedisRolePayload struct {
	Master SwapRedisRoleInstance `json:"master"`
	Slave  SwapRedisRoleInstance `json:"slave"`
	Domain string                `json:"domain"`
}

// SwapRedisRoleRequest represents the request for swapping Redis master-slave roles.
// Payload is a single object, not an array.
type SwapRedisRoleRequest struct {
	BkCloudID    int                  `json:"bk_cloud_id"`
	DbCloudToken string               `json:"db_cloud_token"`
	Payload      SwapRedisRolePayload `json:"payload"`
}

// SwapRedisRoleResponse represents the response structure for Redis role swapping
type SwapRedisRoleResponse struct {
	dbm.ResponseCommonInfo
	Data string `json:"data"`
}

// SwapRedisRole swaps master-slave roles between two Redis instances
func SwapRedisRole(c *dbm.Client, bkCloudId int, domain string,
	masterIp string, masterPort int, slaveIp string, slavePort int) error {
	payload := SwapRedisRolePayload{
		Master: SwapRedisRoleInstance{
			IP:   masterIp,
			Port: masterPort,
		},
		Slave: SwapRedisRoleInstance{
			IP:   slaveIp,
			Port: slavePort,
		},
		Domain: domain,
	}

	req := SwapRedisRoleRequest{
		BkCloudID:    bkCloudId,
		DbCloudToken: config.Cfg.Workflow.DbmApiSwapTendisCluster.Token,
		Payload:      payload,
	}

	logger.Debug(
		"swap redis role request, bk_cloud_id: %d, domain: %s, master: %s:%d, slave: %s:%d",
		bkCloudId, domain, masterIp, masterPort, slaveIp, slavePort,
	)

	response, err := c.SendRequest(config.Cfg.Workflow.DbmApiSwapTendisCluster.Api, hanet.HttpMethodPost,
		req, config.Cfg.Workflow.DbmApiSwapTendisCluster.Timeout)
	if err != nil {
		logger.Error("failed to swap roles of redis nodes, master:%s:%d, slave:%s:%d, err:%s",
			masterIp, masterPort, slaveIp, slavePort, err.Error())
		return err
	}

	logger.Debug("swap redis role response, domain: %s, master: %s:%d, slave: %s:%d, resp_len: %d",
		domain, masterIp, masterPort, slaveIp, slavePort, len(response))

	swapResp := &SwapRedisRoleResponse{}
	if err := json.Unmarshal(response, swapResp); err != nil {
		return err
	}

	if !swapResp.Result {
		return gerrors.Newf(gerrors.Failure, "request failed: %s", swapResp.Message)
	}

	return nil
}

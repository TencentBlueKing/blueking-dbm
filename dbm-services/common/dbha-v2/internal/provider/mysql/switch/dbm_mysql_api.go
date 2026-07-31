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

package mysqlswitch

import (
	"encoding/json"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
)

// SwapMySQLRoleInstance represents a single MySQL instance for role swapping
type SwapMySQLRoleInstance struct {
	IP   string `json:"ip"`
	Port int    `json:"port"`
}

// SwapMySQLRolePayload contains two instances for MySQL role swapping
// Note: instance1 and instance2 should be a MySQL master-slave pair.
// instance1 should be backend_master, instance2 should be backend_slave.
type SwapMySQLRolePayload struct {
	Instance1 SwapMySQLRoleInstance `json:"instance1"`
	Instance2 SwapMySQLRoleInstance `json:"instance2"`
}

// SwapMySQLRoleRequest represents the request for swapping MySQL master-slave roles
type SwapMySQLRoleRequest struct {
	BkCloudID    int                    `json:"bk_cloud_id"`
	DbCloudToken string                 `json:"db_cloud_token"`
	Payloads     []SwapMySQLRolePayload `json:"payloads"`
}

// DumperSwitchInstance represents the instance information for binlog dumper switching
type DumperSwitchInstance struct {
	Ip             string `json:"ip"`
	Port           int    `json:"port"`
	BinlogFile     string `json:"binlog_file"`
	BinlogPosition uint64 `json:"binlog_position"`
}

// DumperSwitchInfo contains cluster domain and dumper instances for switching
type DumperSwitchInfo struct {
	ClusterDomain   string                 `json:"cluster_domain"`
	SwitchInstances []DumperSwitchInstance `json:"switch_instances"`
}

// DumperSwitchRequest represents the request for switching binlog dumper configuration
type DumperSwitchRequest struct {
	BkCloudID    int                `json:"bk_cloud_id"`
	DbCloudToken string             `json:"db_cloud_token"`
	BKBizID      string             `json:"bk_biz_id"`
	IsSafe       bool               `json:"is_safe"`
	SwitchInfos  []DumperSwitchInfo `json:"infos"`
}

// SwapRoleResponse represents the response structure for role swapping
type SwapRoleResponse struct {
	dbm.ResponseCommonInfo

	Data string `json:"data"`
}

// DumperSwitchResponse represents the response structure for binlog dumper switching.
// data is omitted intentionally: DBM returns a large nested object; we only check result.
type DumperSwitchResponse struct {
	dbm.ResponseCommonInfo
}

// SwapMySQLRole swaps master-slave roles between two MySQL instances
func SwapMySQLRole(c *dbm.Client, bkCloudId int, masterIp string, masterPort int, slaveIp string, slavePort int) error {
	payload := SwapMySQLRolePayload{
		Instance1: SwapMySQLRoleInstance{
			IP:   masterIp,
			Port: masterPort,
		},
		Instance2: SwapMySQLRoleInstance{
			IP:   slaveIp,
			Port: slavePort,
		},
	}

	req := SwapMySQLRoleRequest{
		BkCloudID:    bkCloudId,
		DbCloudToken: config.Cfg.Workflow.DbmApiSwapMysqlRole.Token,
		Payloads:     []SwapMySQLRolePayload{payload},
	}

	logger.Debug(
		"swap mysql role request, bk_cloud_id: %d, master: %s:%d, slave: %s:%d",
		bkCloudId,
		masterIp,
		masterPort,
		slaveIp,
		slavePort,
	)

	response, err := c.SendRequest(config.Cfg.Workflow.DbmApiSwapMysqlRole.Api, hanet.HttpMethodPost,
		req, config.Cfg.Workflow.DbmApiSwapMysqlRole.Timeout)
	if err != nil {
		logger.Error("failed to swap role of master(%s:%d) and slave(%s:%d), errmsg: %s",
			masterIp, masterPort, slaveIp, slavePort, err.Error())
		return err
	}

	logger.Debug("swap mysql role response, master: %s:%d, slave: %s:%d, resp_len: %d",
		masterIp, masterPort, slaveIp, slavePort, len(response))

	swapResp := &SwapRoleResponse{}
	if err := json.Unmarshal(response, swapResp); err != nil {
		return err
	}

	if !swapResp.Result {
		return gerrors.Newf(gerrors.Failure, "request failed: %s", swapResp.Message)
	}

	return nil
}

// SwitchBinlogDumper switches binlog dumper configuration for an application
func SwitchBinlogDumper(c *dbm.Client, bkCloudId int, app string, switchInfos []DumperSwitchInfo) error {
	req := DumperSwitchRequest{
		BkCloudID:    bkCloudId,
		DbCloudToken: config.Cfg.Workflow.DbmApiDumperSwitch.Token,
		IsSafe:       true,
		BKBizID:      app,
		SwitchInfos:  switchInfos,
	}

	logger.Debug(
		"switch binlogdumper request, bk_cloud_id: %d, bk_biz_id: %s, switch_count: %d",
		bkCloudId,
		app,
		len(switchInfos),
	)

	response, err := c.SendRequest(config.Cfg.Workflow.DbmApiDumperSwitch.Api, hanet.HttpMethodPost,
		req, config.Cfg.Workflow.DbmApiDumperSwitch.Timeout)
	if err != nil {
		logger.Error("failed to switch binlogdumper, errmsg: %s", err.Error())
		return err
	}

	logger.Debug("switch binlogdumper response, bk_biz_id: %s, resp_len: %d", app, len(response))

	dumperSwitchResp := &DumperSwitchResponse{}
	if err := json.Unmarshal(response, dumperSwitchResp); err != nil {
		return gerrors.Newf(gerrors.InvalidJson, "failed to unmarshal dumper switch response, errmsg: %s", err.Error())
	}

	if !dumperSwitchResp.Result {
		return gerrors.Newf(gerrors.Failure,
			"failed to switch binlogdumper, bk_biz_id: %s, errmsg: %s", app, dumperSwitchResp.Message)
	}

	return nil
}

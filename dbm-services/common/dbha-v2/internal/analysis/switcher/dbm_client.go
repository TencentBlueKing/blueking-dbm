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
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
)

// DbmClient provides HTTP client for communicating with DBM API services
// Handles database instance management operations including status updates, domain management, and role switching
type DbmClient struct {
	httpClient *hanet.HttpClient
}

// SendRequest sends HTTP request to DBM API with specified method and timeout
func (dbm *DbmClient) SendRequest(url string, method hanet.HttpMethod, req any,
	timeout time.Duration) ([]byte, error) {
	if dbm.httpClient == nil {
		dbm.httpClient = hanet.NewHttpClientWithHeaders(map[string]string{
			"Content-Type": "application/json",
		})
	}

	dbm.httpClient.SetTimeout(timeout)

	data, err := json.Marshal(&req)
	if err != nil {
		logger.Warn("failed to marshal the dbm request data, errmsg: %v", err)
		return nil, gerrors.NewE(gerrors.InvalidParameter, err)
	}

	code, resp, err := dbm.httpClient.Request(context.TODO(), url, method, data)
	if err != nil {
		logger.Warn("failed to send http %s request to dbm, errmsg: %v", method, err)
		return nil, err
	}
	if http.StatusOK != code {
		logger.Warn("http %s request failed, status code: %d, errmsg: %v", method, code, err)
		return nil, err
	}

	return resp, nil
}

// GetAddressNumberOfDomain retrieves the number of addresses in a specific domain
func (dbm *DbmClient) GetAddressNumberOfDomain(domainName string) (int, error) {
	req := DomainGetRequest{
		DbCloudToken: config.Cfg.Workflow.DbmApiDomainGet.Token,
		DomainName:   domainName,
	}

	resp, err := dbm.SendRequest(config.Cfg.Workflow.DbmApiDomainGet.Api, hanet.HttpMethodPost,
		req, config.Cfg.Workflow.DbmApiDomainGet.Timeout)
	if err != nil {
		return 0, err
	}

	domainGetRes := &DomainGetRespond{}
	if err := json.Unmarshal(resp, domainGetRes); err != nil {
		return 0, err
	}

	return domainGetRes.RowsNum, nil
}

// UpdateInstanceStatus updates the status of a database instance
func (dbm *DbmClient) UpdateInstanceStatus(ip string, port int, status hamodel.DbmMetadataStatus) error {
	req := UpdateInstanceStatusRequest{
		DbCloudToken: config.Cfg.Workflow.DbmApiUpdateStatus.Token,
		Payloads: []UpdateInstanceStatusPayload{
			{
				IP:     ip,
				Port:   port,
				Status: string(status),
			},
		},
	}

	logger.Debug("UpdateInstanceStatus req:%v", req)

	response, err := dbm.SendRequest(config.Cfg.Workflow.DbmApiUpdateStatus.Api, hanet.HttpMethodPost,
		req, config.Cfg.Workflow.DbmApiUpdateStatus.Timeout)
	if err != nil {
		logger.Error("UpdateInstanceStatus failed, %s", err.Error())
		return err
	}

	logger.Debug("UpdateInstanceStatus response: %v", string(response))
	return nil
}

// DeleteFromDomain removes an instance from the specified domain
func (dbm *DbmClient) DeleteFromDomain(domainName string, instance string, app string) error {
	req := DomainDeleteRequest{
		DbCloudToken: config.Cfg.Workflow.DbmApiDomainDelete.Token,
		App:          app,
		InstancesToDelete: []InstancesOfDomain{
			{
				DomainName: domainName,
				Instances:  []string{instance},
			},
		},
	}

	logger.Debug("DeleteFromDomain req:%v", req)

	resp, err := dbm.SendRequest(config.Cfg.Workflow.DbmApiDomainDelete.Api, hanet.HttpMethodDelete,
		req, config.Cfg.Workflow.DbmApiDomainDelete.Timeout)
	if err != nil {
		return err
	}

	domainDeleteRes := &DomainDeleteRespond{}
	if err := json.Unmarshal(resp, domainDeleteRes); err != nil {
		return err
	}

	if domainDeleteRes.RowsNum != 1 {
		errMsg := fmt.Sprintf("rowsAffected = %d, delete instance [%s] (app=%s) from domain [%s] failed",
			domainDeleteRes.RowsNum, instance, app, domainName)
		return gerrors.New(gerrors.Failure, errMsg)
	}
	return nil
}

// DeregisterFromCLB deregisters an instance from Cloud Load Balancer
func (dbm *DbmClient) DeregisterFromCLB(region string, lbid string, lnid string, ins string) error {
	req := CLBDeRegisterRequest{
		DbCloudToken:   config.Cfg.Workflow.DbmApiCLBDeregister.Token,
		Region:         region,
		LoadBalancerID: lbid,
		ListenerID:     lnid,
		IPs:            []string{ins},
	}

	logger.Debug("DeregisterFromCLB req: %v", req)

	response, err := dbm.SendRequest(config.Cfg.Workflow.DbmApiCLBDeregister.Api, hanet.HttpMethodPost,
		req, config.Cfg.Workflow.DbmApiCLBDeregister.Timeout)
	if err != nil {
		logger.Error("DeregisterFromCLB failed, %s", err.Error())
		return err
	}

	logger.Debug("DeregisterFromCLB response: %v", response)
	return nil
}

// UnbindFromPolaris unbinds an instance from Polaris service discovery
func (dbm *DbmClient) UnbindFromPolaris(servname string, servtoken string, ins string) error {
	req := PolarisUnbindRequest{
		DbCloudToken: config.Cfg.Workflow.DbmApiPolarisUnbind.Token,
		ServiceName:  servname,
		ServiceToken: servtoken,
		IPs:          []string{ins},
	}

	logger.Debug("UnbindFromPolaris req:%v", req)

	response, err := dbm.SendRequest(config.Cfg.Workflow.DbmApiPolarisUnbind.Api, hanet.HttpMethodPost,
		req, config.Cfg.Workflow.DbmApiPolarisUnbind.Timeout)
	if err != nil {
		logger.Error("UnbindFromPolaris failed, %s", err.Error())
		return err
	}

	logger.Debug("UnbindFromPolaris response: %v", response)
	return nil
}

// SwapMySQLRole swaps master-slave roles between two MySQL instances
func (dbm *DbmClient) SwapMySQLRole(masterIp string, masterPort int, slaveIp string, slavePort int) error {
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
		DbCloudToken: config.Cfg.Workflow.DbmApiSwapMysqlRole.Token,
		Payloads:     []SwapMySQLRolePayload{payload},
	}

	logger.Debug("SwapMySQLRole param:%v", req)

	response, err := dbm.SendRequest(config.Cfg.Workflow.DbmApiSwapMysqlRole.Api, hanet.HttpMethodPost,
		req, config.Cfg.Workflow.DbmApiSwapMysqlRole.Timeout)
	if err != nil {
		logger.Error("SwapMySQLRole failed, %s", err.Error())
		return err
	}

	logger.Debug("SwapMySQLRole response: %v", response)
	return nil
}

// SwitchBinlogDumper switches binlog dumper configuration for an application
func (dbm *DbmClient) SwitchBinlogDumper(app string, switchInfos []DumperSwitchInfo) error {
	req := DumperSwitchRequest{
		DbCloudToken: config.Cfg.Workflow.DbmApiDumperSwitch.Token,
		SafeSwitch:   true,
		BKBizID:      app,
		SwitchInfos:  switchInfos,
	}

	logger.Debug("SwitchBinlogDumper param:%v", req)

	response, err := dbm.SendRequest(config.Cfg.Workflow.DbmApiDumperSwitch.Api, hanet.HttpMethodPost,
		req, config.Cfg.Workflow.DbmApiDumperSwitch.Timeout)
	if err != nil {
		logger.Error("SwitchBinlogDumper failed, %s", err.Error())
		return err
	}

	logger.Debug("SwitchBinlogDumper response: %v", response)
	return nil
}

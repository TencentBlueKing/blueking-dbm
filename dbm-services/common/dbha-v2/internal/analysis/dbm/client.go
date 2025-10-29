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

package dbm

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

// Client provides HTTP client for communicating with DBM API services
// Handles database instance management operations including status updates, domain management, and role switching
type Client struct {
	cli *hanet.HttpClient
}

// SendRequest sends HTTP request to DBM API with specified method and timeout
func (c *Client) SendRequest(url string, method hanet.HttpMethod, req any,
	timeout time.Duration) ([]byte, error) {
	if c.cli == nil {
		c.cli = hanet.NewHttpClientWithHeaders(map[string]string{
			"Content-Type": "application/json",
		})
	}

	c.cli.SetTimeout(timeout)

	data, err := json.Marshal(&req)
	if err != nil {
		logger.Warn("failed to marshal the dbm request data, errmsg: %s", err)
		return nil, gerrors.NewE(gerrors.InvalidParameter, err)
	}

	code, resp, err := c.cli.Request(context.Background(), url, method, data)
	if err != nil {
		logger.Warn("failed to send http %s request to dbm, errmsg: %s", method, err)
		return nil, err
	}
	if http.StatusOK != code {
		logger.Warn("http %s request failed, status code: %d, errmsg: %s", method, code, err)
		return nil, err
	}

	return resp, nil
}

func (c *Client) RequestMetadata(ctx context.Context, req *Request) (*Response, error) {
	data, err := json.Marshal(&req)
	if err != nil {
		return nil, err
	}

	if c.cli == nil {
		c.cli = hanet.NewHttpClientWithHeaders(map[string]string{
			"Content-Type": "application/json",
		})
	}

	code, resp, err := c.cli.Post(ctx, config.Cfg.Workflow.DbmApiMetadata.Api, data)
	if err != nil {
		return nil, err
	}

	if http.StatusOK != code {
		return nil, gerrors.Newf(gerrors.HttpRequestFailure, "HTTP responded with a bad code: %d", code)
	}

	if len(resp) == 0 {
		return nil, gerrors.New(gerrors.Failure, "DBM responded with nothing")
	}

	metaRsp := &Response{}
	if err := json.Unmarshal(resp, metaRsp); err != nil {
		return nil, gerrors.Newf(gerrors.InvalidJson, "failed to unmarshal metadata response, %s", err)
	}

	if len(metaRsp.Data) == 0 {
		return nil, gerrors.New(gerrors.Failure, "DBM responded with nothing")
	}

	return metaRsp, nil
}

func (c *Client) QueryMetadataFromDbm(ctx context.Context,
	bkCloudId int, ips []string) ([]*hamodel.DbmMetadata, error) {

	req := DefaultRequest
	req.BkCloudId = bkCloudId
	req.Addresses = append(req.Addresses, ips...)
	req.DbCloudToken = config.Cfg.Workflow.DbmApiMetadata.Token

	metaRsp, err := c.RequestMetadata(ctx, &req)
	if err != nil {
		return nil, err
	}

	datas := []*hamodel.DbmMetadata{}
	for _, rsp := range metaRsp.Data {
		meta := &hamodel.DbmMetadata{
			BkIdcCityID:     rsp.BkIdcCityID,
			BkBizID:         rsp.BkBizID,
			BkCloudID:       rsp.BkCloudID,
			LogicalCityID:   rsp.LogicalCityID,
			LogicalCityName: rsp.LogicalCityName,
			Port:            rsp.Port,
			IP:              rsp.IP,
			Cluster:         rsp.Cluster,
			ClusterID:       rsp.ClusterID,
			ClusterType:     rsp.ClusterType,
			MachineType:     rsp.MachineType,
			Status:          rsp.Status,
		}

		if rsp.BindEntry != nil {
			bindEndtry, err := json.Marshal(rsp.BindEntry)
			if err != nil {
				return nil, err
			}

			meta.BindEntry = string(bindEndtry)
		}

		if rsp.Receiver != nil {
			receiver, err := json.Marshal(rsp.Receiver)
			if err != nil {
				return nil, err
			}

			meta.Receiver = string(receiver)
		}

		if rsp.ProxyInstanceSet != nil {
			proxyInsts, err := json.Marshal(rsp.ProxyInstanceSet)
			if err != nil {
				return nil, err
			}

			meta.ProxyInstanceSet = string(proxyInsts)
		}

		if rsp.TBinlogDumpers != nil {
			binlogDumpers, err := json.Marshal(rsp.TBinlogDumpers)
			if err != nil {
				return nil, err
			}

			meta.BinlogDumperSet = string(binlogDumpers)
		}

		datas = append(datas, meta)
	}

	return datas, nil
}

// GetAddressNumberOfDomain retrieves the number of addresses in a specific domain
func (c *Client) GetAddressNumberOfDomain(domainName string) (int, error) {
	req := DomainGetRequest{
		DbCloudToken: config.Cfg.Workflow.DbmApiDomainGet.Token,
		DomainName:   domainName,
	}

	resp, err := c.SendRequest(config.Cfg.Workflow.DbmApiDomainGet.Api, hanet.HttpMethodPost,
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
func (c *Client) UpdateInstanceStatus(ip string, port int, status DbmMetadataStatus) error {
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

	response, err := c.SendRequest(config.Cfg.Workflow.DbmApiUpdateStatus.Api, hanet.HttpMethodPost,
		req, config.Cfg.Workflow.DbmApiUpdateStatus.Timeout)
	if err != nil {
		logger.Error("failed to update instance (%s:%d) status, errmsg:%s", ip, port, err.Error())
		return err
	}

	logger.Debug("UpdateInstanceStatus response: %v", string(response))
	return nil
}

// DeleteFromDomain removes an instance from the specified domain
func (c *Client) DeleteFromDomain(domainName string, instance string, app string) error {
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

	resp, err := c.SendRequest(config.Cfg.Workflow.DbmApiDomainDelete.Api, hanet.HttpMethodDelete,
		req, config.Cfg.Workflow.DbmApiDomainDelete.Timeout)
	if err != nil {
		return err
	}

	domainDeleteRes := &DomainDeleteRespond{}
	if err := json.Unmarshal(resp, domainDeleteRes); err != nil {
		return err
	}

	if domainDeleteRes.RowsNum != 1 {
		errMsg := fmt.Sprintf("rowsAffected = %d, delete instance (%s) (app=%s) from domain (%s) failed",
			domainDeleteRes.RowsNum, instance, app, domainName)
		return gerrors.New(gerrors.Failure, errMsg)
	}
	return nil
}

// DeleteFromCLB deregisters an instance from Cloud Load Balancer
func (c *Client) DeleteFromCLB(region string, lbid string, lnid string, ins string) error {
	req := ClbDeleteRequest{
		DbCloudToken:   config.Cfg.Workflow.DbmApiCLBDeregister.Token,
		Region:         region,
		LoadBalancerID: lbid,
		ListenerID:     lnid,
		IPs:            []string{ins},
	}

	logger.Debug("DeleteFromCLB req: %v", req)

	response, err := c.SendRequest(config.Cfg.Workflow.DbmApiCLBDeregister.Api, hanet.HttpMethodPost,
		req, config.Cfg.Workflow.DbmApiCLBDeregister.Timeout)
	if err != nil {
		logger.Error("failed to deregister instance (%s) from CLB, errmsg: %s", ins, err.Error())
		return err
	}

	logger.Debug("DeleteFromCLB response: %v", response)
	return nil
}

// DeleteFromPolaris unbinds an instance from Polaris service discovery
func (c *Client) DeleteFromPolaris(servname string, servtoken string, ins string) error {
	req := PolarisDeleteRequest{
		DbCloudToken: config.Cfg.Workflow.DbmApiPolarisUnbind.Token,
		ServiceName:  servname,
		ServiceToken: servtoken,
		IPs:          []string{ins},
	}

	logger.Debug("DeleteFromPolaris req: %v", req)

	response, err := c.SendRequest(config.Cfg.Workflow.DbmApiPolarisUnbind.Api, hanet.HttpMethodPost,
		req, config.Cfg.Workflow.DbmApiPolarisUnbind.Timeout)
	if err != nil {
		logger.Error("failed to unbind instance (%s) from Polaris, %s", ins, err.Error())
		return err
	}

	logger.Debug("DeleteFromPolaris response: %v", response)
	return nil
}

// SwapMySQLRole swaps master-slave roles between two MySQL instances
func (c *Client) SwapMySQLRole(masterIp string, masterPort int, slaveIp string, slavePort int) error {
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

	logger.Debug("SwapMySQLRole req: %v", req)

	response, err := c.SendRequest(config.Cfg.Workflow.DbmApiSwapMysqlRole.Api, hanet.HttpMethodPost,
		req, config.Cfg.Workflow.DbmApiSwapMysqlRole.Timeout)
	if err != nil {
		logger.Error("failed to swap role of master(%s:%d) and slave(%s:%d), errmsg: %s",
			masterIp, masterPort, slaveIp, slavePort, err.Error())
		return err
	}

	logger.Debug("SwapMySQLRole response: %v", response)
	return nil
}

// SwitchBinlogDumper switches binlog dumper configuration for an application
func (c *Client) SwitchBinlogDumper(app string, switchInfos []DumperSwitchInfo) error {
	req := DumperSwitchRequest{
		DbCloudToken: config.Cfg.Workflow.DbmApiDumperSwitch.Token,
		IsSafe:       true,
		BKBizID:      app,
		SwitchInfos:  switchInfos,
	}

	logger.Debug("SwitchBinlogDumper req: %v", req)

	response, err := c.SendRequest(config.Cfg.Workflow.DbmApiDumperSwitch.Api, hanet.HttpMethodPost,
		req, config.Cfg.Workflow.DbmApiDumperSwitch.Timeout)
	if err != nil {
		logger.Error("failed to switch binlogdumper, errmsg: %s", err.Error())
		return err
	}

	logger.Debug("SwitchBinlogDumper response: %v", response)
	return nil
}

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

package dbm

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/tools/internal/cluster/config"
)

// Client provides an HTTP client for communicating with the DBM
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
		return nil, gerrors.NewE(gerrors.InvalidParameter, err)
	}

	code, resp, err := c.cli.Request(context.Background(), url, method, data)
	if err != nil {
		return nil, err
	}

	if http.StatusOK != code {
		errMsg := fmt.Sprintf("HTTP %s request responded with a bad code: %d, errmsg: %s", method, code, err)
		return nil, gerrors.Newf(gerrors.HttpRequestFailure, "%s", errMsg)
	}

	return resp, nil
}

// UpdateInstanceStatus updates the status of a database instance
func (c *Client) UpdateInstanceStatus(ip string, port int, status DbmMetadataStatus) error {
	req := UpdateInstanceStatusRequest{
		DbCloudToken: config.ClusterConfig.DbmServices.DbmApiUpdateStatus.Token,
		Payloads: []UpdateInstanceStatusPayload{
			{
				IP:     ip,
				Port:   port,
				Status: string(status),
			},
		},
	}

	respond, err := c.SendRequest(config.ClusterConfig.DbmServices.DbmApiUpdateStatus.Api, hanet.HttpMethodPost,
		req, config.ClusterConfig.DbmServices.DbmApiUpdateStatus.Timeout)
	if err != nil {
		return err
	}

	updateStatusResp := &UpdateInstanceStatusResponse{}
	if err := json.Unmarshal(respond, updateStatusResp); err != nil {
		return err
	}

	if !updateStatusResp.Result {
		return gerrors.Newf(gerrors.Failure, "request failed, errmsg: %s", updateStatusResp.Message)
	}

	return nil
}

// UpdateAllInstancesStatus updates the status of all database instances
func (c *Client) UpdateAllInstancesStatus(instanceList []config.InstanceAddress, status DbmMetadataStatus) error {
	for _, instance := range instanceList {
		err := c.UpdateInstanceStatus(instance.Host, instance.Port, status)
		if err != nil {
			return err
		}
	}
	return nil
}

// requestMetadata sends HTTP request to DBM to get metadata of instances
func (c *Client) requestMetadata(ctx context.Context, req *MetadataRequest) (*MetadataResponse, error) {
	data, err := json.Marshal(req)
	if err != nil {
		return nil, err
	}

	if c.cli == nil {
		c.cli = hanet.NewHttpClientWithHeaders(map[string]string{
			"Content-Type": "application/json",
		})
	}

	code, resp, err := c.cli.Post(ctx, config.ClusterConfig.DbmServices.DbmApiMetadata.Api, data)
	if err != nil {
		return nil, err
	}

	if http.StatusOK != code {
		return nil, gerrors.Newf(gerrors.HttpRequestFailure, "HTTP responded with a bad code: %d", code)
	}

	if len(resp) == 0 {
		return nil, gerrors.New(gerrors.Failure, "DBM responded with nothing")
	}

	metaRsp := &MetadataResponse{}
	if err := json.Unmarshal(resp, metaRsp); err != nil {
		return nil, gerrors.Newf(gerrors.InvalidJson, "failed to unmarshal metadata response, "+
			"errmsg: %s, resp: %s", err, string(resp))
	}

	if len(metaRsp.Data) == 0 {
		return nil, gerrors.New(gerrors.Failure, "DBM responded with nothing")
	}

	return metaRsp, nil
}

// QueryMetadataFromDbm queries metadata from DBM
func (c *Client) QueryMetadataFromDbm(bkCloudId int, ips []string) ([]*DbInstMetadata, error) {

	req := DefaultMetadataRequest
	req.BkCloudId = bkCloudId
	req.Addresses = append(req.Addresses, ips...)
	req.DbCloudToken = config.ClusterConfig.DbmServices.DbmApiMetadata.Token

	metaRsp, err := c.requestMetadata(context.Background(), &req)
	if err != nil {
		return nil, err
	}

	return metaRsp.Data, nil
}

// QueryInstanceRole queries instance role from DBM
func (c *Client) QueryInstanceRole(ip string, port int) (DbmMetadataInstanceRole, error) {
	metadataList, err := c.QueryMetadataFromDbm(0, []string{ip})
	if err != nil {
		return EmptyInstanceRole, err
	}

	for _, metadata := range metadataList {
		if metadata.IP == ip && metadata.Port == port {
			return DbmMetadataInstanceRole(metadata.InstanceRole), nil
		}
	}

	return EmptyInstanceRole, gerrors.Newf(gerrors.Failure, "failed to find instance (%s:%d)", ip, port)
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
		DbCloudToken: config.ClusterConfig.DbmServices.DbmApiSwapMysqlRole.Token,
		Payloads:     []SwapMySQLRolePayload{payload},
	}

	respond, err := c.SendRequest(config.ClusterConfig.DbmServices.DbmApiSwapMysqlRole.Api, hanet.HttpMethodPost,
		req, config.ClusterConfig.DbmServices.DbmApiSwapMysqlRole.Timeout)
	if err != nil {
		return err
	}

	swapResp := &SwapRoleResponse{}
	if err := json.Unmarshal(respond, swapResp); err != nil {
		return err
	}

	if !swapResp.Result {
		return gerrors.Newf(gerrors.Failure, "request failed: %s", swapResp.Message)
	}

	return nil
}

// GetAllInstancesOfDomain retrieves all instances of a specific domain
func (c *Client) GetAllInstancesOfDomain(domain string) ([]InstanceInfoInDomain, error) {
	req := DomainGetRequest{
		DbCloudToken: config.ClusterConfig.DbmServices.DbmApiDomainGet.Token,
		DomainName:   []string{domain},
	}

	resp, err := c.SendRequest(config.ClusterConfig.DbmServices.DbmApiDomainGet.Api, hanet.HttpMethodPost,
		req, config.ClusterConfig.DbmServices.DbmApiDomainGet.Timeout)
	if err != nil {
		return nil, err
	}

	domainGetRes := &DomainGetResponse{}
	if err := json.Unmarshal(resp, domainGetRes); err != nil {
		return nil, gerrors.Newf(gerrors.Failure, "failed to unmarshal response: %s", err.Error())
	}

	if !domainGetRes.Result {
		return nil, gerrors.Newf(gerrors.Failure, "request failed: %s", domainGetRes.Message)
	}

	return domainGetRes.Data.Detail, nil
}

// AddInstanceToDomain adds an instance to a specific domain
func (c *Client) AddInstanceToDomain(ip string, port int, domain string, bkBizId int) error {
	req := DomainPutRequest{
		App:          strconv.Itoa(bkBizId),
		DbCloudToken: config.ClusterConfig.DbmServices.DbmApiDomainPut.Token,
		InstancesToAdd: []InstancesOfDomain{
			{
				DomainName: domain,
				Instances:  []string{fmt.Sprintf("%s#%d", ip, port)},
			},
		},
	}

	resp, err := c.SendRequest(config.ClusterConfig.DbmServices.DbmApiDomainPut.Api, hanet.HttpMethodPut,
		req, config.ClusterConfig.DbmServices.DbmApiDomainPut.Timeout)
	if err != nil {
		return err
	}

	domainPutRes := &DomainPutResponse{}
	if err := json.Unmarshal(resp, domainPutRes); err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to unmarshal response: %s", err.Error())
	}

	if !domainPutRes.Result {
		return gerrors.Newf(gerrors.Failure, "request failed: %s", domainPutRes.Message)
	}

	if domainPutRes.Data.RowsNum != 1 {
		errMsg := fmt.Sprintf("rowsAffected = %d, failed to add instance (%s:%d) (app=%s) to domain (%s) ",
			domainPutRes.Data.RowsNum, ip, port, strconv.Itoa(bkBizId), domain)
		return gerrors.New(gerrors.Failure, errMsg)
	}
	return nil
}

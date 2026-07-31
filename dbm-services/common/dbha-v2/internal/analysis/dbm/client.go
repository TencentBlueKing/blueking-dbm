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
	"errors"
	"fmt"
	"net/http"
	"strconv"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/apm"
	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/haapm"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
)

var (
	ErrNoResponse = gerrors.New(gerrors.Failure, "no response from DBM")
)

// Client provides HTTP client for communicating with DBM API services
// Handles database instance management operations including status updates, domain management, and role switching
type Client struct {
	cli     *hanet.HttpClient
	cliOnce sync.Once
}

func (c *Client) getHttpClient() *hanet.HttpClient {
	c.cliOnce.Do(func() {
		if c.cli == nil {
			c.cli = hanet.NewHttpClientWithHeaders(map[string]string{
				"Content-Type": "application/json",
			})
		}
	})

	return c.cli
}

func (c *Client) getRequestClientWithTimeout(timeout time.Duration) *hanet.HttpClient {
	return c.getHttpClient().Clone().SetTimeout(timeout)
}

// SendRequest sends HTTP request to DBM API with specified method and timeout
func (c *Client) SendRequest(url string, method hanet.HttpMethod, req any,
	timeout time.Duration) ([]byte, error) {
	cli := c.getRequestClientWithTimeout(timeout)

	data, err := json.Marshal(&req)
	if err != nil {
		logger.Warn("failed to marshal the dbm request data, errmsg: %s", err)
		return nil, gerrors.NewE(gerrors.InvalidParameter, err)
	}

	start := time.Now()
	code, resp, err := cli.Request(context.Background(), url, method, data)
	c.ReportAPIMetric(start, url, method, code, err)
	if err != nil {
		logger.Warn("failed to send http %s request to dbm, errmsg: %s", method, err)
		return nil, err
	}

	if http.StatusOK != code {
		errMsg := fmt.Sprintf("HTTP %s request responded with a bad code: %d, errmsg: %s", method, code, err)
		logger.Warn("%s", errMsg)
		return nil, gerrors.Newf(gerrors.HttpRequestFailure, "%s", errMsg)
	}

	return resp, nil
}

// RequestMetadata sends HTTP request to DBM to get metadata of instances
func (c *Client) RequestMetadata(ctx context.Context, req *Request) (int, *Response, error) {
	data, err := json.Marshal(&req)
	if err != nil {
		return 0, nil, gerrors.Newf(gerrors.InvalidJson, "failed to marshal metadata request, %s", err)
	}

	cli := c.getRequestClientWithTimeout(config.Cfg.Workflow.DbmApiMetadata.Timeout)

	start := time.Now()
	code, resp, err := cli.Post(ctx, config.Cfg.Workflow.DbmApiMetadata.Api, data)
	c.ReportAPIMetric(start, config.Cfg.Workflow.DbmApiMetadata.Api, hanet.HttpMethodPost, code, err)
	if err != nil {
		return code, nil, err
	}

	if http.StatusOK != code {
		return code, nil, gerrors.Newf(gerrors.HttpRequestFailure, "HTTP responded with a bad code: %d", code)
	}

	if len(resp) == 0 {
		return code, nil, ErrNoResponse
	}

	metaRsp := &Response{}
	if err := json.Unmarshal(resp, metaRsp); err != nil {
		return code, nil, gerrors.Newf(gerrors.InvalidJson, "failed to unmarshal metadata response, %s", err)
	}

	if len(metaRsp.Data) == 0 {
		return code, nil, ErrNoResponse
	}

	return code, metaRsp, nil
}

// QueryMetadataFromDbm queries metadata from DBM
func (c *Client) QueryMetadataFromDbm(ctx context.Context, bkCloudId int, ips []string) (int, []*DbInstMetadata, error) {

	req := DefaultRequest
	req.BkCloudId = bkCloudId
	req.Addresses = append(req.Addresses, ips...)
	req.DbCloudToken = config.Cfg.Workflow.DbmApiMetadata.Token

	code, metaRsp, err := c.RequestMetadata(ctx, &req)
	if err != nil {
		return code, nil, err
	}

	return code, metaRsp.Data, nil
}

// QueryInstanceInfoByDomain queries instance info from DBM by domain
func (c *Client) QueryInstanceInfoByDomain(bkCloudId int, clusterDomainName string) ([]*DbInstMetadata, error) {

	req := Request{
		BkCloudId:    bkCloudId,
		DbCloudToken: config.Cfg.Workflow.DbmApiMetadata.Token,
		Addresses:    []string{clusterDomainName},
	}

	_, metaRsp, err := c.RequestMetadata(context.Background(), &req)
	if err != nil {
		return nil, err
	}

	return metaRsp.Data, nil
}

// GetAddressNumberOfDomain retrieves the number of addresses in a specific domain
func (c *Client) GetAddressNumberOfDomain(bkCloudId int, domainName string) (int, error) {
	req := DomainGetRequest{
		BkCloudID:    bkCloudId,
		DbCloudToken: config.Cfg.Workflow.DbmApiDomainGet.Token,
		DomainName:   []string{domainName},
	}
	logger.Debug("query domain address count request, bk_cloud_id: %d, domain: %s", bkCloudId, domainName)

	resp, err := c.SendRequest(config.Cfg.Workflow.DbmApiDomainGet.Api, hanet.HttpMethodPost,
		req, config.Cfg.Workflow.DbmApiDomainGet.Timeout)
	if err != nil {
		return 0, err
	}
	logger.Debug("query domain address count response, domain: %s, resp_len: %d", domainName, len(resp))

	domainGetRes := &DomainGetResponse{}
	if err := json.Unmarshal(resp, domainGetRes); err != nil {
		return 0, gerrors.Newf(gerrors.Failure, "failed to unmarshal response: %s", err.Error())
	}

	if !domainGetRes.Result {
		return 0, gerrors.Newf(gerrors.Failure, "request failed: %s", domainGetRes.Message)
	}

	return domainGetRes.Data.RowsNum, nil
}

// UpdateBatchInstancesStatus updates status for multiple database instances in one request.
func (c *Client) UpdateBatchInstancesStatus(bkCloudId int, insts []InstWithinCloud, status DbmMetadataStatus) error {
	if len(insts) == 0 {
		return nil
	}

	payloads := make([]UpdateInstanceStatusPayload, 0, len(insts))
	for _, inst := range insts {
		payloads = append(payloads, UpdateInstanceStatusPayload{
			IP:     inst.IP,
			Port:   inst.Port,
			Status: string(status),
		})
	}

	req := UpdateInstanceStatusRequest{
		BkCloudID:    bkCloudId,
		DbCloudToken: config.Cfg.Workflow.DbmApiUpdateStatus.Token,
		Payloads:     payloads,
	}

	logger.Debug(
		"update batch instances status request, bk_cloud_id: %d, instance_count: %d, status: %s",
		bkCloudId,
		len(payloads),
		status,
	)

	response, err := c.SendRequest(config.Cfg.Workflow.DbmApiUpdateStatus.Api, hanet.HttpMethodPost,
		req, config.Cfg.Workflow.DbmApiUpdateStatus.Timeout)
	if err != nil {
		logger.Error("failed to update batch instances status, errmsg: %s", err.Error())
		return err
	}

	logger.Debug(
		"update batch instances status response, bk_cloud_id: %d, instance_count: %d, resp_len: %d",
		bkCloudId,
		len(payloads),
		len(response),
	)

	updateStatusResp := &UpdateInstanceStatusResponse{}
	if err := json.Unmarshal(response, updateStatusResp); err != nil {
		return gerrors.Newf(gerrors.InvalidJson, "failed to unmarshal status update response, errmsg: %s", err.Error())
	}

	if !updateStatusResp.Result {
		return gerrors.Newf(gerrors.Failure,
			"failed to update batch instances status, instance_count: %d, errmsg: %s",
			len(payloads),
			updateStatusResp.Message,
		)
	}

	return nil
}

// UpdateInstanceStatus updates the status of a single database instance.
func (c *Client) UpdateInstanceStatus(bkCloudId int, ip string, port int, status DbmMetadataStatus) error {
	return c.UpdateBatchInstancesStatus(bkCloudId, []InstWithinCloud{{IP: ip, Port: port}}, status)
}

// DeleteFromDomain removes an instance from the specified domain
func (c *Client) DeleteFromDomain(bkCloudId int, domainName string, instance string, app string) error {
	req := DomainDeleteRequest{
		BkCloudID:    bkCloudId,
		DbCloudToken: config.Cfg.Workflow.DbmApiDomainDelete.Token,
		App:          app,
		InstancesToDelete: []InstancesOfDomain{
			{
				DomainName: domainName,
				Instances:  []string{instance},
			},
		},
	}
	logger.Debug(
		"delete from domain request, bk_cloud_id: %d, domain: %s, instance: %s, app: %s",
		bkCloudId,
		domainName,
		instance,
		app,
	)

	resp, err := c.SendRequest(config.Cfg.Workflow.DbmApiDomainDelete.Api, hanet.HttpMethodDelete,
		req, config.Cfg.Workflow.DbmApiDomainDelete.Timeout)
	if err != nil {
		return err
	}
	logger.Debug("delete from domain response, domain: %s, instance: %s, resp_len: %d", domainName, instance, len(resp))

	domainDeleteRes := &DomainDeleteResponse{}
	if err := json.Unmarshal(resp, domainDeleteRes); err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to unmarshal response: %s", err.Error())
	}

	if !domainDeleteRes.Result {
		return gerrors.Newf(gerrors.Failure, "request failed: %s", domainDeleteRes.Message)
	}

	if domainDeleteRes.Data.RowsNum != 1 {
		errMsg := fmt.Sprintf("rowsAffected = %d, failed to delete instance (%s) (app=%s) from domain (%s)",
			domainDeleteRes.Data.RowsNum, instance, app, domainName)
		return gerrors.New(gerrors.Failure, errMsg)
	}
	return nil
}

// DeleteFromCLB deregisters an instance from Cloud Load Balancer
func (c *Client) DeleteFromCLB(bkCloudId int, region string, lbid string, lnid string, ins string) error {
	req := ClbDeleteRequest{
		BkCloudID:      bkCloudId,
		DbCloudToken:   config.Cfg.Workflow.DbmApiCLBDeregister.Token,
		Region:         region,
		LoadBalancerID: lbid,
		ListenerID:     lnid,
		IPs:            []string{ins},
	}

	logger.Debug(
		"delete from clb request, bk_cloud_id: %d, region: %s, lb_id: %s, listener_id: %s, instance: %s",
		bkCloudId,
		region,
		lbid,
		lnid,
		ins,
	)

	response, err := c.SendRequest(config.Cfg.Workflow.DbmApiCLBDeregister.Api, hanet.HttpMethodPost,
		req, config.Cfg.Workflow.DbmApiCLBDeregister.Timeout)
	if err != nil {
		logger.Error("failed to deregister instance (%s) from CLB, errmsg: %s", ins, err.Error())
		return err
	}

	logger.Debug("delete from clb response, instance: %s, resp_len: %d", ins, len(response))

	clbDeleteResp := &ClbDeleteResponse{}
	if err := json.Unmarshal(response, clbDeleteResp); err != nil {
		return gerrors.Newf(gerrors.InvalidJson, "failed to unmarshal clb delete response, errmsg: %s", err.Error())
	}

	if !clbDeleteResp.Result {
		return gerrors.Newf(gerrors.Failure,
			"failed to deregister instance (%s) from CLB, errmsg: %s", ins, clbDeleteResp.Message)
	}

	return nil
}

// DeleteFromPolaris unbinds an instance from Polaris service discovery
func (c *Client) DeleteFromPolaris(bkCloudId int, servname string, servtoken string, ins string) error {
	req := PolarisDeleteRequest{
		BkCloudID:    bkCloudId,
		DbCloudToken: config.Cfg.Workflow.DbmApiPolarisUnbind.Token,
		ServiceName:  servname,
		ServiceToken: servtoken,
		IPs:          []string{ins},
	}

	logger.Debug(
		"delete from polaris request, bk_cloud_id: %d, service_name: %s, instance: %s",
		bkCloudId,
		servname,
		ins,
	)

	response, err := c.SendRequest(config.Cfg.Workflow.DbmApiPolarisUnbind.Api, hanet.HttpMethodPost,
		req, config.Cfg.Workflow.DbmApiPolarisUnbind.Timeout)
	if err != nil {
		logger.Error("failed to unbind instance from polaris, instance: %s, errmsg: %s", ins, err)
		return err
	}

	logger.Debug("delete from polaris response, instance: %s, resp_len: %d", ins, len(response))

	// TODO: parse response and check if result is success

	return nil
}

// ReportAPIMetric reports API metric
func (c *Client) ReportAPIMetric(start time.Time, url string, method hanet.HttpMethod, code int, err error) {
	if err != nil {
		var gerr *gerrors.Error
		if errors.As(err, &gerr) {
			code = gerr.Code()
		}

		// Report third-party API request error
		if err := apm.ThirdPartyApiRequestErrorTotal.IncWithLabels(map[string]string{
			apm.MetricLabelURL:           url,
			apm.MetricLabelMethod:        method.String(),
			apm.MetricLabelStatusCode:    strconv.Itoa(code),
			haapm.MetricLabelServiceName: apm.MetricServerName,
		}); err != nil {
			logger.Warn("failed to report third-party api request error metric, errmsg: %s", err)
		}
	}

	// Report third-party API request time consuming
	if err := apm.ThirdPartyApiRequestTimeConsumingMs.ObserveWithLabels(map[string]string{
		apm.MetricLabelURL:           url,
		apm.MetricLabelMethod:        method.String(),
		apm.MetricLabelStatusCode:    strconv.Itoa(code),
		haapm.MetricLabelServiceName: apm.MetricServerName,
	}, float64(time.Since(start).Milliseconds())); err != nil {
		logger.Warn("failed to report third-party api request time consuming metric, errmsg: %s", err)
	}
}

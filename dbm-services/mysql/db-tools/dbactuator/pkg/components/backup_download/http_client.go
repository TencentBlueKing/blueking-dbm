package backup_download

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"math/rand"
	"net/http"
	"net/url"
	"strings"
	"time"

	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util/auth"
)

const (
	// apiserver response code
	statusSuccess int = 0

	// job executer user
	// jobExecuterUser = "pub"
	jobExecuterUser = "scr-system"
)

// APIServerResponse TODO
type APIServerResponse struct {
	Code    int             `json:"code"`
	Message string          `json:"message"`
	Data    json.RawMessage `json:"data"`
}

// Client TODO
type Client struct {
	apiservers []string

	// JWT token
	token     string
	secretId  string
	secretKey string

	// client for apiservers
	client *http.Client
}

// NewClientByHosts TODO
func NewClientByHosts(hosts []string) (*Client, error) {
	cli := &Client{}

	for _, host := range hosts {
		cli.apiservers = append(cli.apiservers, host)
	}

	cli.client = &http.Client{
		Transport: &http.Transport{},
	}

	return cli, nil
}

// New TODO
func New(apiServers string) (*Client, error) {
	cli := &Client{}
	if apiServers == "" {
		return nil, fmt.Errorf("apiservers is null")
	}
	for _, host := range strings.Split(apiServers, ",") {
		cli.apiservers = append(cli.apiservers, host)
	}

	tr := &http.Transport{}

	cli.client = &http.Client{
		Transport: tr,
	}

	return cli, nil
}

// DoNew TODO
// others: other parameters maybe used
//
//	other->{"user"}  : for gateway
//
// 支持根据返回内容包含特征串自动重试
func (c *Client) DoNew(method, url string, params interface{}, headers map[string]string) (*APIServerResponse, error) {
	var response *APIServerResponse
	var err error
	for retryIdx := 0; retryIdx < 5; retryIdx++ {
		response, err = c.doNewInner(method, url, params, headers)
		if err == nil {
			break
		}
		if strings.Contains(err.Error(), "cse.flowcontrol.Consumer.qps.limit") {
			logger.Warn("DoNew failed, retryIdx:%d, err:%s", retryIdx, err.Error())
			wait := retryIdx*retryIdx*1000 + rand.Intn(1000)
			time.Sleep(time.Duration(wait) * time.Millisecond)
			continue
		}
		break
	}
	return response, err
}

func (c *Client) doNewInner(method, url string, params interface{}, headers map[string]string) (
	*APIServerResponse,
	error,
) {
	host, err := c.nextTarget()
	if err != nil {
		logger.Error("nextTarget get an error:%s", err)
		return nil, fmt.Errorf("get target host failed, err: %+v", err)
	}
	body, err := json.Marshal(params)
	if err != nil {
		logger.Error("marshal %+v get an error:%w", params, err)
		return nil, fmt.Errorf("json marshal param failed, err: %+v", err)
	}
	req, err := http.NewRequest(method, host+url, bytes.NewReader(body))
	if err != nil {
		logger.Error("create a new request(%s,%s,%+v) get an error:%w", method, host+url, params, err)
		return nil, fmt.Errorf("new request failed, err: %+v", err)
	}

	// set auth...
	c.setHeader(req, headers)

	resp, err := c.client.Do(req)
	if err != nil {
		logger.Error("invoking http request failed, url: %s, error:%w", req.URL.String(), err)
		return nil, fmt.Errorf("do http request failed, err: %+v", err)
	}
	defer resp.Body.Close()

	// 目前出现偶现网关超时问题，重试一次看是否时间段内必现
	for i := 1; i <= 5; i++ {
		// 500 可能正在发布
		// 429 可能大并发量偶现超频
		// 504 具体原因未知，先重试
		if !cmutil.HasElem(
			resp.StatusCode, []int{
				http.StatusInternalServerError, http.StatusTooManyRequests,
				http.StatusGatewayTimeout,
			},
		) {
			break
		}

		wait := i*i*1000 + rand.Intn(1000)
		time.Sleep(time.Duration(wait) * time.Millisecond)
		logger.Warn(
			"client.Do result with %s, wait %d milliSeconds and retry, url: %s",
			resp.Status,
			wait,
			req.URL.String(),
		)
		resp, err = c.client.Do(req)
		if err != nil {
			logger.Error("an error occur while invoking client.Do, url: %s, error:%s", req.URL.String(), err.Error())
			return nil, fmt.Errorf("do http request failed, err: %+v", err)
		}
	}

	b, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		err = fmt.Errorf("read resp.body error:%s", err.Error())
		logger.Error(err.Error())
		return nil, err
	}
	result := &APIServerResponse{}
	err = json.Unmarshal(b, result)
	if err != nil {
		logger.Error("unmarshall %s to %+v get an error:%s", string(b), *result, err.Error())
		return nil, fmt.Errorf("json unmarshal failed, err: %+v", err)
	}

	// check response and data is nil
	if result.Code != statusSuccess {
		logger.Warn(
			"result.Code is %d not equal to %d,message:%s,data:%s,param:%+v", result.Code, statusSuccess,
			result.Message, string(result.Data), params,
		)
		if len(result.Data) != 0 {
			return nil, fmt.Errorf("[%v - %v - %s]", result.Code, result.Message, string(result.Data))
		}
		return nil, fmt.Errorf("%v - %v", result.Code, result.Message)
	}
	return result, nil
}

// Do TODO
func (c *Client) Do(method, url string, params interface{}) (*APIServerResponse, error) {
	return c.DoNew(method, url, params, map[string]string{})
}

func (c *Client) nextTarget() (string, error) {
	rand.Seed(time.Now().UnixNano())
	startPos := rand.Intn(len(c.apiservers))
	pos := startPos
	for {
		gotHost := c.apiservers[pos]
		u, err := url.Parse(gotHost)
		if err != nil {
			if pos = (pos + 1) % len(c.apiservers); pos == startPos {
				return "", fmt.Errorf("all hosts are down, uptime tests are failing")
			}
			continue
		}
		if util.HostCheck(u.Host) {
			return gotHost, nil
		}
		logger.Error("host %s is down", gotHost)
		if pos = (pos + 1) % len(c.apiservers); pos == startPos {
			return "", fmt.Errorf("all hosts are down, uptime tests are failing")
		}
	}
}

func (c *Client) setHeader(req *http.Request, others map[string]string) {
	user := jobExecuterUser
	if _, ok := others["user"]; ok {
		user = strings.TrimSpace(others["user"])
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("user", user)
	// Set JWT token
	if token, err := auth.Sign(user, c.secretId, c.secretKey); err == nil {
		req.Header.Set("Authorization", "Bearer "+token)
	}
}

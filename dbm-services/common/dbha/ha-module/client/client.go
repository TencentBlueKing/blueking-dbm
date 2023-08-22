// Package client TODO
package client

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"math/rand"
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"
	"time"

	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/log"
	"dbm-services/common/dbha/ha-module/util"
)

const (
	// apiServer response code
	statusSuccess int = 0

	// job execute user
	jobExecuteUser = "mysql"
)

// HttpBodyParseCB TODO
type HttpBodyParseCB func([]byte) (interface{}, error)

// APIServerResponse response info from remote api server
type APIServerResponse struct {
	Code int             `json:"code"`
	Msg  string          `json:"msg"`
	Data json.RawMessage `json:"data"`
}

// Client use to request api server
type Client struct {
	Type       string
	CloudId    int
	Conf       *config.APIConfig
	apiServers []string

	// client for apiServers
	client *http.Client
}

// SetHttpClient set http client info
func (c *Client) SetHttpClient(h *http.Client) {
	c.client = h
}

// SetApiServers set one or multi api server address
func (c *Client) SetApiServers(s []string) {
	for _, host := range s {
		c.apiServers = append(c.apiServers, host)
	}
}

// NewClientByAddrs init an new client to request api server
func NewClientByAddrs(addrs []string, apiType string) (*Client, error) {
	cli := &Client{}

	cli.Type = apiType
	for _, host := range addrs {
		cli.apiServers = append(cli.apiServers, host)
	}

	cli.client = &http.Client{
		Transport: &http.Transport{},
	}

	return cli, nil
}

// DoNew send http request and receive response
func (c *Client) DoNew(method, url string, params interface{}, headers map[string]string) (*APIServerResponse, error) {
	resp, err := c.DoNewForCB(method, url, params, headers, APIBodyParseCB)
	if err != nil {
		return nil, err
	} else if resp == nil {
		return nil, fmt.Errorf("url %s return nil response", url)
	} else {
		return resp.(*APIServerResponse), nil
	}
}

// DoNewForCB process http body by callback, and support retry
func (c *Client) DoNewForCB(
	method, url string, params interface{}, headers map[string]string, bodyCB HttpBodyParseCB,
) (interface{}, error) {
	if headers == nil {
		headers = map[string]string{}
	}

	var retryErr error
	for retryIdx := 0; retryIdx < 5; retryIdx++ {
		response, retryErr := c.doNewInner(method, url, params, headers, bodyCB)
		if retryErr == nil {
			return response, nil
		}
	}
	return nil, retryErr
}

// APIBodyParseCB callback to parse api response body
func APIBodyParseCB(b []byte) (interface{}, error) {
	result := &APIServerResponse{}
	err := json.Unmarshal(b, result)
	if err != nil {
		log.Logger.Errorf("unmarshall %s to %+v get an error:%s", string(b), *result, err.Error())
		return nil, fmt.Errorf("json unmarshal failed, err: %+v", err)
	}

	// check response and data is nil
	if result.Code != statusSuccess {
		log.Logger.Errorf("result.Code is %d not equal to %d,message:%s,data:%s",
			result.Code, statusSuccess, result.Msg, string(result.Data))
		if len(result.Data) != 0 {
			return nil, fmt.Errorf("[%v - %v - %s]", result.Code, result.Msg, string(result.Data))
		}
		return nil, fmt.Errorf("%v - %v", result.Code, result.Msg)
	}
	return result, nil
}

// doNewInner TODO
// execute request and handle response
func (c *Client) doNewInner(method, url string, params interface{},
	headers map[string]string, bodyCB HttpBodyParseCB) (interface{}, error) {
	host, err := c.nextTarget()
	if err != nil {
		log.Logger.Errorf("nextTarget get an error:%s", err.Error())
		return nil, fmt.Errorf("get target host failed, err: %+v", err)
	}
	log.Logger.Debugf("host:%s\n", host)

	body, err := json.Marshal(params)
	if err != nil {
		log.Logger.Errorf("marshal %+v get an error:%s", params, err.Error())
		return nil, fmt.Errorf("json marshal param failed, err: %+v", err)
	}
	req, err := http.NewRequest(method, host+url, bytes.NewReader(body))

	if err != nil {
		log.Logger.Errorf("create a new request(%s,%s,%+v) get an error:%s", method, host+url, params, err.Error())
		return nil, fmt.Errorf("new request failed, err: %+v", err)
	}

	// TODO set auth...
	c.setHeader(req, headers)

	dump, _ := httputil.DumpRequest(req, true)
	log.Logger.Debugf("begin http request: %s", dump)

	resp, err := c.client.Do(req)
	if err != nil {
		log.Logger.Errorf("invoking http request failed, url: %s, error:%s", req.URL.String(), err.Error())
		return nil, fmt.Errorf("do http request failed, err: %+v", err)
	}
	defer func() {
		if resp == nil {
			return
		}
		if err := resp.Body.Close(); err != nil {
			log.Logger.Errorf("close response body failed, err:%s", err.Error())
		}
	}()

	// 目前出现偶现网关超时问题，重试一次看是否时间段内必现
	for i := 1; i <= 5; i++ {
		// 500 可能正在发布
		// 429 可能大并发量偶现超频
		// 504 具体原因未知，先重试
		if !util.HasElem(resp.StatusCode, []int{http.StatusInternalServerError, http.StatusTooManyRequests,
			http.StatusGatewayTimeout}) {
			break
		}

		wait := i*i*1000 + rand.Intn(1000)
		time.Sleep(time.Duration(wait) * time.Millisecond)
		log.Logger.Warnf("client.Do result with %s, wait %d milliSeconds and retry, url: %s",
			resp.Status, wait, req.URL.String())
		resp, err = c.client.Do(req)
		if err != nil {
			log.Logger.Errorf("an error occur while invoking client.Do, url: %s, error:%s",
				req.URL.String(), err.Error())
			return nil, fmt.Errorf("do http request failed, err: %+v", err)
		}
	}

	if resp.StatusCode != http.StatusOK {
		bodyBytes, err := httputil.DumpResponse(resp, true)
		if err != nil {
			log.Logger.Errorf("read resp.body failed, err: %s", err.Error())
			return nil, fmt.Errorf("http response: %s, status code: %d", string(bodyBytes), resp.StatusCode)
		}
		log.Logger.Debugf("http response: %s", string(bodyBytes))
		return nil, fmt.Errorf("http response: %s, status code: %d", string(bodyBytes), resp.StatusCode)
	}

	b, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		err = fmt.Errorf("read resp.body error:%s", err.Error())
		log.Logger.Error(err.Error())
		return nil, err
	}

	result, err := bodyCB(b)
	if err != nil {
		log.Logger.Errorf(err.Error())
		return nil, err
	}
	return result, nil
}

// Do request main enter
func (c *Client) Do(method, url string, params interface{}) (*APIServerResponse, error) {
	return c.DoNew(method, url, params, map[string]string{})
}

// nextTarget TODO
// random get an api server to request
func (c *Client) nextTarget() (string, error) {
	rand.Seed(time.Now().UnixNano())
	startPos := rand.Intn(len(c.apiServers))
	pos := startPos
	for {
		gotHost := c.apiServers[pos]
		u, err := url.Parse(gotHost)
		if err != nil {
			if pos = (pos + 1) % len(c.apiServers); pos == startPos {
				return "", fmt.Errorf("all hosts are down, uptime tests are failing. err:%s", err.Error())
			}
			continue
		}
		if util.HostCheck(u.Host) {
			return gotHost, nil
		}
		log.Logger.Errorf("host %s is down", gotHost)
		if pos = (pos + 1) % len(c.apiServers); pos == startPos {
			return "", fmt.Errorf("all hosts are down, uptime tests are failing")
		}
	}
}

func (c *Client) setHeader(req *http.Request, others map[string]string) {
	user := jobExecuteUser
	if _, ok := others["user"]; ok {
		user = strings.TrimSpace(others["user"])
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("user", user)

	if auth, ok := others[constvar.BkApiAuthorization]; ok {
		req.Header.Set(constvar.BkApiAuthorization, auth)
	}
	// // Set JWT token
	// if token, err := auth.Sign(user); err == nil {
	//  req.Header.Set("Authorization", "Bearer "+token)
	// }
}

// ConvertParamForGetRequest convert param for GET request
// Encode encodes the values into “URL encoded” form
// ("bar=baz&foo=qux") sorted by key.
func (c *Client) ConvertParamForGetRequest(rawParam map[string]string) string {
	values := url.Values{}
	for k, v := range rawParam {
		values.Add(k, v)
	}
	param := values.Encode()

	return param
}

// SpliceUrlByPrefix assemble url
func (c *Client) SpliceUrlByPrefix(prefix string, name string, param string) string {
	var prefixUrl string
	pu, err := url.Parse(prefix)
	if err != nil {
		log.Logger.Errorf("parse prefix url is invalid, err:%s", err.Error())
		return "/"
	}
	prefixUrl = pu.String()

	nu, err := url.Parse(name)
	if err != nil {
		log.Logger.Errorf("parse name url is invalid, err:%s", err.Error())
		return "/"
	}
	nameUrl := nu.String()

	if param == "" {
		return prefixUrl + "/" + nameUrl
	} else {
		return prefixUrl + "/" + nameUrl + "?" + param
	}
}

// SpliceUrl assemble url by param
func (c *Client) SpliceUrl(name string, param string) string {
	nu, err := url.Parse(name)
	if err != nil {
		log.Logger.Errorf("parse name url is invalid, err:%s", err.Error())
		return ""
	}
	nameUrl := nu.String()
	if param == "" {
		return "/" + nameUrl
	} else {
		return "/" + nameUrl + "?" + param
	}
}

// NewAPIClient create new api http client
func NewAPIClient(c *config.APIConfig, apiType string, cloudId int) Client {
	cli := Client{
		Type:    apiType,
		CloudId: cloudId,
		Conf:    c,
	}

	cli.SetHttpClient(&http.Client{
		Transport: &http.Transport{},
		Timeout:   time.Second * time.Duration(c.Timeout),
	})

	// use http request at present
	cli.SetApiServers([]string{
		fmt.Sprintf("http://%s:%d", c.Host, c.Port),
	})

	return cli
}

package util

import (
	"bytes"
	"crypto/tls"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log/slog"
	"math/rand"
	"net/http"
	"net/http/httputil"
	"strings"
	"time"

	"github.com/google/go-querystring/query"
	"github.com/spf13/viper"
)

const (
	// apiserver response code
	statusSuccess int = 0
)

// APIServerResponse TODO
type APIServerResponse struct {
	Code    int             `json:"code"`
	Message string          `json:"message"`
	Data    json.RawMessage `json:"data"`
}

// APIServerResponseCompatible TODO
type APIServerResponseCompatible struct {
	Code    int             `json:"code"`
	Message string          `json:"msg"`
	Data    json.RawMessage `json:"data"`
}

// Client TODO
type Client struct {
	apiserver string

	// JWT token
	token string

	// client for apiservers
	client *http.Client
}

// NewClientByHosts TODO
func NewClientByHosts(host string) *Client {
	http.DefaultTransport.(*http.Transport).TLSClientConfig = &tls.Config{InsecureSkipVerify: true}
	cli := &Client{}
	cli.apiserver = host
	cli.client = &http.Client{
		Transport: &http.Transport{},
	}
	return cli
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
			slog.Error(fmt.Sprintf("DoNew failed, retryIdx:%d", retryIdx), err)
			wait := retryIdx*retryIdx*1000 + rand.Intn(1000)
			time.Sleep(time.Duration(wait) * time.Millisecond)
			continue
		}
		break
	}
	return response, err
}

func (c *Client) doNewInner(method, url string, params interface{}, headers map[string]string) (*APIServerResponse,
	error) {
	host := c.apiserver
	body, err := json.Marshal(params)
	if err != nil {
		slog.Error("marshal get an error", err)
		return nil, fmt.Errorf("json marshal param failed, err: %+v", err)
	}

	if method == "GET" && !strings.Contains(url, "cc3") {
		body = nil
		// 有些 GET 参数拼接在 URL 中,比如/thirdpartyapi/cc3/query-from-shell；有些 GET 参数在结构体中
		vals, err := query.Values(params)
		if err != nil {
			return nil, fmt.Errorf("get querystring param failed, err: %+v", err)
		}
		url = url + "?" + vals.Encode()
	}

	req, err := http.NewRequest(method, host+url, bytes.NewBuffer(body))

	if err != nil {
		slog.Error(fmt.Sprintf("create a new request(%s,%s,%+v) get an error", method, host+url, params), err)
		return nil, fmt.Errorf("new request failed, err: %+v", err)
	}
	req.Header.Set("Content-Type", "application/json")
	bkAuth := fmt.Sprintf(`{"bk_app_code": %s, "bk_app_secret": %s}`, viper.GetString("bk_app_code"),
		viper.GetString("bk_app_secret"))
	req.Header.Set("x-bkapi-authorization", bkAuth)

	cookieAppCode := http.Cookie{Name: "bk_app_code", Path: "/", Value: viper.GetString("bk_app_code"), MaxAge: 86400}
	cookieAppSecret := http.Cookie{Name: "bk_app_secret", Path: "/", Value: viper.GetString("bk_app_secret"),
		MaxAge: 86400}
	req.AddCookie(&cookieAppCode)
	req.AddCookie(&cookieAppSecret)

	resp, err := c.client.Do(req)
	// slog.Info(fmt.Sprintf("req:%v", req))
	if err != nil {
		slog.Error(fmt.Sprintf("invoking http request failed, url: %s", req.URL.String()), err)
		return nil, fmt.Errorf("do http request failed, err: %+v", err)
	}
	defer func() {
		if resp == nil {
			return
		}
		if err := resp.Body.Close(); err != nil {
			slog.Warn("close response body failed", "err", err.Error())
		}
	}()

	// 目前出现偶现网关超时问题，重试一次看是否时间段内必现
	for i := 1; i <= 5; i++ {
		// 500 可能正在发布
		// 429 可能大并发量偶现超频
		// 504 具体原因未知，先重试
		if !HasElem(resp.StatusCode, []int{http.StatusInternalServerError, http.StatusTooManyRequests,
			http.StatusGatewayTimeout}) {
			break
		}

		wait := i*i*1000 + rand.Intn(1000)
		time.Sleep(time.Duration(wait) * time.Millisecond)
		slog.Warn(fmt.Sprintf("client.Do result with %s, wait %d milliSeconds and retry, url: %s", resp.Status, wait,
			req.URL.String()))
		resp, err = c.client.Do(req)
		if err != nil {
			slog.Error(fmt.Sprintf("an error occur while invoking client.Do, url: %s", req.URL.String()), err)
			return nil, fmt.Errorf("do http request failed, err: %+v", err)
		}
	}

	if resp.StatusCode != http.StatusOK {
		bodyBytes, err := httputil.DumpResponse(resp, true)
		if err != nil {
			slog.Error("read resp.body failed, err: %+v", err)
			fmt.Errorf("http response: %s, status code: %d", string(bodyBytes), resp.StatusCode)
			return nil, fmt.Errorf("http response: %s, status code: %d", string(bodyBytes), resp.StatusCode)
		}
		if resp.StatusCode != http.StatusOK {
			fmt.Errorf("http response: %s, status code: %d", string(bodyBytes), resp.StatusCode)
			return nil, fmt.Errorf("http response: %s, status code: %d", string(bodyBytes), resp.StatusCode)
		}
		slog.Info(fmt.Sprintf("http response: \n\n%s\n", string(bodyBytes)))
	}

	b, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		err = fmt.Errorf("read resp.body error:%s", err.Error())
		slog.Error("msg", err)
		return nil, err
	}
	result := &APIServerResponse{}
	if strings.Contains(url, "priv_manager") {
		temp := &APIServerResponseCompatible{}
		err = json.Unmarshal(b, temp)
		if err != nil {
			slog.Error(fmt.Sprintf("unmarshall %s to %+v get an error", string(b), *result), err)
			return nil, fmt.Errorf("json unmarshal failed, err: %+v", err)
		}
		result = &APIServerResponse{temp.Code, temp.Message, temp.Data}
	} else {
		err = json.Unmarshal(b, result)
		if err != nil {
			slog.Error(fmt.Sprintf("unmarshall %s to %+v get an error", string(b), *result), err)
			return nil, fmt.Errorf("json unmarshal failed, err: %+v", err)
		}
	}

	// check response and data is nil
	if result.Code != statusSuccess {
		slog.Warn(fmt.Sprintf("result.Code is %d not equal to %d,message:%s,data:%s,param:%+v", result.Code, statusSuccess,
			result.Message, string(result.Data), params))
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

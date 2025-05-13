package util

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"net/http/httputil"
	"time"
)

const statusSuccess int = 0

// APIServerResponse ..
type APIServerResponse struct {
	Code    int             `json:"code"`
	Message string          `json:"message"`
	Data    json.RawMessage `json:"data"`
}

// Client http request client
type Client struct {
	apiserver string
	cloudId   int
	// db cloud token
	token string

	// client for apiservers
	client *http.Client
}

// NewClient ..
func NewClient(apiserver, token string, cloudId int) (cli *Client, err error) {
	cli = &Client{}
	tr := &http.Transport{}
	cli.client = &http.Client{
		Transport: tr,
	}
	if apiserver == "" || token == "" {
		err = fmt.Errorf("client new client error. apiserver[%s] or token[%s] is empty", apiserver, token)
		return nil, err
	}
	cli.apiserver = apiserver
	cli.cloudId = cloudId
	cli.token = token
	return cli, nil
}

// DoNew 发起请求
func (c *Client) DoNew(method, url string, params interface{}, others map[string]string) (*APIServerResponse, error) {
	var resp *http.Response
	var maxRetryTimes int = 5
	var req *http.Request
	body, err := c.getReqBody(method, url, params)
	if err != nil {
		return nil, err
	}
	for maxRetryTimes >= 0 {
		maxRetryTimes--
		err = nil

		req, err = http.NewRequest(method, c.apiserver+url, bytes.NewReader(body))
		if err != nil {
			err = fmt.Errorf("client http.NewRequest(%s,%s,%s) get an error:%s",
				method, c.apiserver+url, string(body), err.Error())
			return nil, err
		}
		c.setHeader(req)

		resp, err = c.client.Do(req)
		if err != nil {
			err = fmt.Errorf(
				"an error occur while invoking client.Do, error:%v,url:%s,params:%s,resp:%s,retry",
				err, req.URL.String(), ToString(params), ToString(resp))
			time.Sleep(3 * time.Second)
			continue
		}
		if resp.StatusCode != http.StatusOK {
			bodyBytes, _ := httputil.DumpResponse(resp, true)
			err = fmt.Errorf("http response: %s, status code: %d,methods:%s,url: %s,params:%s,retry",
				string(bodyBytes), resp.StatusCode, method, req.URL.String(), string(body))
			resp.Body.Close()
			time.Sleep(3 * time.Second)
			continue
		}
		break
	}
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	b, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		err = fmt.Errorf("client DoNew read resp.body error:%s,methods:%s,url: %s,params:%s",
			err.Error(), method, req.URL.String(), string(body))
		return nil, err
	}
	result := &APIServerResponse{}
	err = json.Unmarshal(b, result)
	if err != nil {
		err = fmt.Errorf("client DoNew unmarshal %s to %+v get an error:%s,methods:%s,url: %s,params:%s",
			string(b), *result, err.Error(),
			method, req.URL.String(), string(body))
		return nil, err
	}

	// check response and data is nil
	if result.Code != statusSuccess {
		err = fmt.Errorf("client DoNew fail,code:%d,message:%s,methods:%s,url: %s,params:%s",
			result.Code, result.Message, method, req.URL.String(), string(body))
		return nil, err
	}
	return result, nil
}

// Do ..
func (c *Client) Do(method, url string, params interface{}) (*APIServerResponse, error) {
	return c.DoNew(method, url, params, map[string]string{})
}

func (c *Client) setHeader(req *http.Request) {
	req.Header.Set("Content-Type", "application/json")
}

func (c *Client) getReqBody(method, url string, params interface{}) (body []byte, err error) {
	if params == nil {
		return
	}

	// 将 params 转换为 JSON 字符串
	jsonParams, err := json.Marshal(params)
	if err != nil {
		err = fmt.Errorf("getReqBody json.Marshal %+v get an error: %v", params, err)
		return
	}

	// 反序列化 JSON 字符串为 map[string]interface{}
	var mapParams map[string]interface{}
	err = json.Unmarshal(jsonParams, &mapParams)
	if err != nil {
		err = fmt.Errorf("getReqBody json.Unmarshal %+v get an error: %v", params, err)
		return
	}

	mapParams["db_cloud_token"] = c.token
	mapParams["bk_cloud_id"] = c.cloudId
	body, err = json.Marshal(mapParams)
	if err != nil {
		err = fmt.Errorf("getReqBody json.Marshal %+v get an error: %v", mapParams, err)
		return
	}
	return
}

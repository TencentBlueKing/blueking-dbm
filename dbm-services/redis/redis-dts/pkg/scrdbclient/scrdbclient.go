// Package scrdbclient 向scr/dbm发起http请求
package scrdbclient

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"net/http/httputil"
	"strings"
	"time"

	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/util"

	"github.com/dgrijalva/jwt-go/v4"
	"github.com/spf13/viper"
	"go.uber.org/zap"
)

const (
	// apiserver response code
	statusSuccess int = 0

	// job executer user
	// jobExecuterUser = "pub"
	jobExecuterUser = "scr-system"
)

// APIServerResponse ..
type APIServerResponse struct {
	Code    int             `json:"code"`
	Message string          `json:"message"`
	Data    json.RawMessage `json:"data"`
}

// Client http request client
type Client struct {
	servicename string
	apiserver   string

	// JWT token
	token string

	// client for apiservers
	client *http.Client
	// logger
	logger *zap.Logger
}

// NewClient ..
func NewClient(serviceName string, logger *zap.Logger) (*Client, error) {
	if logger == nil {
		return nil, fmt.Errorf("logger cann't be nil")
	}
	var err error
	cli := &Client{}
	cli.servicename = serviceName
	err = cli.getapiserver()
	if err != nil {
		return nil, err
	}
	tr := &http.Transport{}
	cli.client = &http.Client{
		Transport: tr,
	}
	cli.logger = logger
	return cli, nil
}

// GetServiceName get servicename
func (c *Client) GetServiceName() string {
	return c.servicename
}
func (c *Client) getapiserver() (err error) {
	switch c.servicename {
	case constvar.DtsRemoteTendisxk8s:
		c.apiserver = viper.GetString("dtsRemoteTendisxk8s.rootUrl")
	case constvar.BkDbm:
		c.apiserver = viper.GetString("bkDbm.rootUrl")
	default:
		c.apiserver = ""
	}
	if c.apiserver == "" {
		err := fmt.Errorf("%s rootUrl(%s) cann't be empty", c.servicename, c.apiserver)
		c.logger.Error(err.Error())
		return err
	}
	return nil
}

func (c *Client) getSecretKey() (secretKey string, err error) {
	switch c.servicename {
	case constvar.DtsRemoteTendisxk8s:
		secretKey = viper.GetString("dtsRemoteTendisxk8s.secret_key")
	default:
		secretKey = ""
	}
	if secretKey == "" {
		err = fmt.Errorf("%s secret_key(%s) cann't be empty", c.servicename, secretKey)
		c.logger.Error(err.Error())
		return
	}
	return
}

func (c *Client) getSecretID() (secretID string, err error) {
	switch c.servicename {
	case constvar.DtsRemoteTendisxk8s:
		secretID = viper.GetString("dtsRemoteTendisxk8s.secret_id")
	default:
		secretID = ""
	}
	if secretID == "" {
		err = fmt.Errorf("%s secret_id(%s) cann't be empty", c.servicename, secretID)
		c.logger.Error(err.Error())
		return
	}
	return
}

func (c *Client) getReqBody(method, url string, params interface{}) (body []byte, err error) {
	if params == nil {
		return
	}

	// 将 params 转换为 JSON 字符串
	jsonParams, err := json.Marshal(params)
	if err != nil {
		err = fmt.Errorf("getReqBody json.Marshal %+v get an error: %v", params, err)
		c.logger.Error(err.Error())
		return
	}
	if method != http.MethodPost || c.GetServiceName() != constvar.BkDbm {
		return
	}

	// 反序列化 JSON 字符串为 map[string]interface{}
	var mapParams map[string]interface{}
	err = json.Unmarshal(jsonParams, &mapParams)
	if err != nil {
		err = fmt.Errorf("getReqBody json.Unmarshal %+v get an error: %v", params, err)
		c.logger.Error(err.Error())
		return
	}

	mapParams["db_cloud_token"] = viper.GetString("bkDbm.db_cloud_token")
	mapParams["bk_cloud_id"] = viper.GetInt("bkDbm.db_cloud_id")
	body, err = json.Marshal(mapParams)
	if err != nil {
		err = fmt.Errorf("getReqBody json.Marshal %+v get an error: %v", mapParams, err)
		c.logger.Error(err.Error())
		return
	}
	return
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
			err = fmt.Errorf("scrDbClient http.NewRequest(%s,%s,%s) get an error:%s",
				method, c.apiserver+url, string(body), err.Error())
			c.logger.Error(err.Error())
			return nil, err
		}
		c.setHeader(req, others)

		resp, err = c.client.Do(req)
		if err != nil {
			err = fmt.Errorf(
				"an error occur while invoking client.Do, error:%v,url:%s,params:%s,resp:%s,retry...",
				err, req.URL.String(), util.ToString(params), util.ToString(resp))
			c.logger.Error(err.Error())
			time.Sleep(5 * time.Second)
			continue
		}
		if resp.StatusCode != http.StatusOK {
			bodyBytes, _ := httputil.DumpResponse(resp, true)
			err = fmt.Errorf("http response: %s, status code: %d,methods:%s,url: %s,params:%s,retry...",
				string(bodyBytes), resp.StatusCode, method, req.URL.String(), string(body))
			c.logger.Error(err.Error(), zap.String("Authorization", req.Header.Get("Authorization")))
			resp.Body.Close()
			time.Sleep(5 * time.Second)
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
		err = fmt.Errorf("scrDbClient DoNew read resp.body error:%s,methods:%s,url: %s,params:%s",
			err.Error(), method, req.URL.String(), string(body))
		c.logger.Error(err.Error(), zap.String("Authorization", req.Header.Get("Authorization")))
		return nil, err
	}
	result := &APIServerResponse{}
	err = json.Unmarshal(b, result)
	if err != nil {
		err = fmt.Errorf("scrDbClient DoNew unmarshal %s to %+v get an error:%s,methods:%s,url: %s,params:%s",
			string(b), *result, err.Error(),
			method, req.URL.String(), string(body))
		c.logger.Error(err.Error(), zap.String("Authorization", req.Header.Get("Authorization")))
		return nil, err
	}

	// check response and data is nil
	if result.Code != statusSuccess {
		err = fmt.Errorf("scrDbClient DoNew fail,code:%d,message:%s,methods:%s,url: %s,params:%s",
			result.Code, result.Message, method, req.URL.String(), string(body))
		c.logger.Error(err.Error(), zap.String("Authorization", req.Header.Get("Authorization")))
		return nil, err
	}
	return result, nil
}

// Do ..
func (c *Client) Do(method, url string, params interface{}) (*APIServerResponse, error) {
	return c.DoNew(method, url, params, map[string]string{})
}

// Sign 获取token
func (c *Client) Sign(rtx string) (tokenStr string, err error) {
	var secretID, secretKey string
	secretID, err = c.getSecretID()
	if err != nil {
		return
	}
	secretKey, err = c.getSecretKey()
	if err != nil {
		return
	}
	// The token content.
	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"sub":  secretID,
		"user": rtx,
		"iat":  time.Now().Unix(),
	})
	// Sign the token with the specified secret.
	tokenStr, err = token.SignedString([]byte(secretKey))
	return
}
func (c *Client) setHeader(req *http.Request, others map[string]string) {
	req.Header.Set("Content-Type", "application/json")
	if c.GetServiceName() == constvar.BkDbm {
		return
	}
	user := jobExecuterUser
	if _, ok := others["user"]; ok {
		user = strings.TrimSpace(others["user"])
	}
	req.Header.Set("user", user)
	req.Header.Set("x-cse-src-microservice", "tendisk8s")
	// Set JWT token
	if token, err := c.Sign(user); err == nil {
		req.Header.Set("Authorization", "Bearer "+token)
	}
}

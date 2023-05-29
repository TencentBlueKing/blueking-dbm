// Package httpclient TODO
package httpclient

import (
	"bytes"
	"encoding/json"
	"io/ioutil"
	"net/http"
	"time"

	"github.com/pkg/errors"
)

// New TODO
func New() *http.Client {
	client := &http.Client{Timeout: 10 * time.Second}
	return client
}

// HttpClient TODO
type HttpClient struct {
	Url     string
	Params  interface{}
	Headers map[string]string
	Client  *http.Client
}

// Get TODO
func Get(client *http.Client, url string, params map[string]string, headers map[string]string) ([]byte, error) {
	req, err := http.NewRequest(http.MethodGet, url, nil)
	if err != nil {
		return nil, errors.Wrap(err, "make request")
	}
	q := req.URL.Query()
	for pk, pv := range params {
		q.Add(pk, pv)
	}
	req.URL.RawQuery = q.Encode()
	if headers != nil {
		for hk, hv := range headers {
			req.Header.Add(hk, hv)
		}
	}

	resp, err := client.Do(req)
	if err != nil {
		return nil, errors.Wrap(err, "do request")
	}
	defer resp.Body.Close()
	respBody, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return nil, errors.Wrap(err, "read resp body")
	}
	return respBody, nil
}

// Post TODO
func Post(client *http.Client, url string, params interface{}, contentType string, headers map[string]string) ([]byte,
	error) {
	jsonData, err := json.Marshal(params)
	if err != nil {
		return nil, errors.Wrap(err, "param marshal to json")
	}
	req, err := http.NewRequest(http.MethodPost, url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, errors.Wrap(err, "make request")
	}

	if headers != nil {
		for hk, hv := range headers {
			req.Header.Add(hk, hv)
		}
	}
	if contentType != "" {
		req.Header.Add("Content-Type", contentType)
	}
	resp, err := client.Do(req)
	if err != nil {
		return nil, errors.Wrap(err, "do request")
	}
	defer resp.Body.Close()
	respBody, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return nil, errors.Wrap(err, "read resp body")
	}
	if !(resp.StatusCode >= 200 && resp.StatusCode < 300) {
		return nil, errors.Errorf("response code %d. body: %s", resp.StatusCode, respBody)
	}
	return respBody, nil
}

// IBSHttpApiResp TODO
type IBSHttpApiResp struct {
	Code    string          `json:"code"`
	Message string          `json:"message"`
	Data    json.RawMessage `json:"data"`
}

// BaseHttpApiResp TODO
type BaseHttpApiResp struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data"`
}

// PostJson TODO
func (c *HttpClient) PostJson(url string, params interface{}, headers map[string]string) (json.RawMessage, error) {
	respBytes, err := Post(c.Client, url, params, "application/json", headers)
	if err != nil {
		return nil, err
	}
	return respBytes, nil
}

// PostJsonWithServers TODO
func (c *HttpClient) PostJsonWithServers(client *http.Client, servers []string, params interface{},
	headers map[string]string) (*IBSHttpApiResp, error) {

	return nil, nil
}

// PostForm TODO
func PostForm(client *http.Client, url string, params interface{}, headers map[string]string) ([]byte, error) {
	return Post(client, url, params, "application/x-www-form-urlencoded", headers)
}

// PostFile TODO
func PostFile(client *http.Client, url string, params interface{}, headers map[string]string) ([]byte, error) {
	return Post(client, url, params, "multipart/form-data", headers)
}

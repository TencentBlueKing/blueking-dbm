package cc

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"

	"github.com/google/go-querystring/query"
)

const (
	// apiserver response code
	statusSuccess int = 0
)

// Response TODO
type Response struct {
	Code       int             `json:"code"`
	Permission json.RawMessage `json:"permission"`
	Result     bool            `json:"result"`
	RequestId  string          `json:"request_id"`
	Message    string          `json:"message"`
	Data       json.RawMessage `json:"data"`
	Error      json.RawMessage `json:"error"`
}

// Client TODO
type Client struct {
	apiserver string
	// client for apiservers
	client *http.Client
	// Blueking secret
	secret Secret

	timeout time.Duration
}

// Secret TODO
type Secret struct {
	BKAppCode   string
	BKAppSecret string
	BKUsername  string
}

// NewClient return new client
func NewClient(apiserver string, secret Secret) (*Client, error) {
	cli := &Client{
		apiserver: apiserver,
		secret:    secret,
	}
	tr := &http.Transport{}
	cli.client = &http.Client{
		Transport: tr,
	}
	return cli, nil
}

// Timeout TODO
func (c *Client) Timeout(duration time.Duration) {
	c.timeout = duration
}

// Do main handler
func (c *Client) Do(method, url string, params interface{}) (*Response, error) {
	object, err := Accessor(params)
	if err != nil {
		return nil, err
	}
	// set auth...
	object.SetSecret(c.secret)

	body, err := json.Marshal(object)
	if err != nil {
		return nil, fmt.Errorf("RequestErr - %v", err)
	}
	fullURL := c.apiserver + url
	log.Println(fullURL, string(body))
	req, err := http.NewRequest(method, fullURL, bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("RequestErr - new request failed: %v", err)
	}
	if c.timeout != 0 {
		ctx, cancel := context.WithTimeout(req.Context(), c.timeout)
		defer cancel()

		req = req.WithContext(ctx)
	}
	// Set Header
	req.Header.Set("X-Bkapi-Accept-Code-Type", "int")

	if method == "GET" {
		q, _ := query.Values(object)
		log.Println("encode: ", q.Encode())
		req.URL.RawQuery = q.Encode()
	}

	resp, err := c.client.Do(req)
	if err != nil {
		return nil, err
	}

	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("HttpCodeErr - Code: %v, Response: %+v", resp.StatusCode, resp)
	}
	b, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("HttpCodeErr - Code: %v, io read all failed %s", resp.StatusCode, err.Error())
	}
	result := &Response{}
	err = json.Unmarshal(b, result)
	if err != nil {
		return nil, err
	}
	// check response and data is nil
	if result.Code != statusSuccess {
		return nil, fmt.Errorf("RequestErr - RequestId: %s, Code: %v,  Messag: %v, Error: %v",
			result.RequestId,
			result.Code,
			result.Message,
			string(result.Error))
	}
	return result, nil
}

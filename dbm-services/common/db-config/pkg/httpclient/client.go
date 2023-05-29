package httpclient

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"math/rand"
	"net/http"
	"strings"
	"time"
)

// Client TODO
type Client struct {
	api    string
	token  string
	client *http.Client
}

// NewHTTPClient TODO
func NewHTTPClient() *Client {
	cli := &Client{}
	cli.client = &http.Client{Transport: &http.Transport{}}
	return cli
}

// Do TODO
func (c *Client) Do(method, url string, params []byte, headers map[string]string) (result *Response, err error) {
	for idx := 0; idx < 5; idx++ {
		result, err = c.do(method, url, params, headers)
		if err == nil {
			break
		}
		wait := idx*idx*1000 + rand.Intn(1000)
		time.Sleep(time.Duration(wait) * time.Millisecond)
		continue
	}
	return result, err
}

func (c *Client) do(method, url string, body []byte, headers map[string]string) (result *Response, err error) {
	req, err := http.NewRequest(method, url, bytes.NewReader(body))
	if err != nil {
		log.Printf("[error] NewRequest failed %v", err)
		return
	}
	// set headers
	c.setHeader(req, headers)
	resp, err := c.client.Do(req)
	if err != nil {
		log.Printf("[error] invoke http request failed %v", err)
		return
	}
	defer resp.Body.Close()
	if resp.StatusCode >= 400 {
		return nil, fmt.Errorf("http response failed %v", resp)
	}
	b, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		log.Printf("[error] http response body read failed %v", err)
		return nil, err
	}
	err = json.Unmarshal(b, &result)
	if err != nil {
		log.Printf("[error] response unmarshal failed %v", err)
		return nil, err
	}
	return result, nil
}

func (c *Client) setHeader(req *http.Request, others map[string]string) {
	user := "scr-system"
	if _, ok := others["user"]; ok {
		user = strings.TrimSpace(others["user"])
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("user", user)
	// Set JWT token
	if token, err := Sign(user); err == nil {
		req.Header.Set("Authorization", "Bearer "+token)
	}
}

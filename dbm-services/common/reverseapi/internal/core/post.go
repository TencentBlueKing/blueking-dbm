package core

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/url"
	"strconv"
)

func (c *Core) Post(endPoint string, payLoad json.RawMessage, ports ...int) (data []byte, err error) {
	apiPath, _ := url.JoinPath(reverseApiBase, endPoint)
	var errs []error
	for _, addr := range c.nginxAddrs {
		data, err := c.post(apiPath, addr, payLoad, ports...)
		if err == nil {
			return data, nil
		}

		// err != nil, data == nil, 是http的错误
		if data == nil {
			errs = append(errs, err)
		}

		// event 校验失败之类的协议错误
		return data, err
	}
	return nil, errors.Join(errs...)
}

func (c *Core) post(apiPath string, addr string, payLoad json.RawMessage, ports ...int) (data []byte, err error) {
	ep := url.URL{
		Scheme: "http",
		Host:   addr,
		Path:   apiPath,
	}

	req, err := http.NewRequest(http.MethodPost, ep.String(), bytes.NewBuffer(payLoad))
	if err != nil {
		return nil, err
	}
	q := req.URL.Query()
	if c.debug && c.ip != "" {
		q.Add("ip", c.ip)
	}
	q.Add("bk_cloud_id", fmt.Sprintf("%d", c.bkCloudId))
	for _, port := range ports {
		q.Add("port", strconv.Itoa(port))
	}
	req.URL.RawQuery = q.Encode()

	req.Header.Set("Content-Type", "application/json")

	return do(c.client, req)
}

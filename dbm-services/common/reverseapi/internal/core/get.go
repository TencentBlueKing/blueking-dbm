package core

import (
	"errors"
	"fmt"
	"net/http"
	"net/url"
	"strconv"
)

func (c *Core) Get(endPoint string, ports ...int) (data []byte, err error) {
	apiPath, _ := url.JoinPath(reverseApiBase, endPoint)
	var errs []error
	for _, addr := range c.nginxAddrs {
		data, err := c.get(apiPath, addr, ports...)
		if err == nil {
			return data, nil
		}
		errs = append(errs, err)
	}
	return nil, errors.Join(errs...)
}

func (c *Core) get(apiPath string, addr string, ports ...int) (data []byte, err error) {
	ep := url.URL{
		Scheme: "http",
		Path:   apiPath,
		Host:   addr,
	}

	req, err := http.NewRequest(http.MethodGet, ep.String(), nil)
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

	data, err = do(c.client, req)
	return
}

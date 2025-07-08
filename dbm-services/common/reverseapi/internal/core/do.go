package core

import (
	"bytes"
	"encoding/json"
	err2 "errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"time"

	"github.com/avast/retry-go/v4"
	"github.com/pkg/errors"
)

func (c *Core) do(method string, api string, payLoad json.RawMessage, ports ...int) (data []byte, err error) {
	apiPath, _ := url.JoinPath("/", reverseApiBase, api, "/")

	var errs []error
	for _, addr := range c.nginxAddrs {
		data, err = c.doOneAddrWithRetry(method, apiPath, addr, payLoad, ports...)
		if err == nil {
			return data, nil
		}
		errs = append(errs, errors.Wrapf(err, "failed to do http request for %s on %s", apiPath, addr))
		time.Sleep(1 * time.Second)
	}

	if len(errs) > 0 {
		return nil, err2.Join(errs...)
	}

	return
}

func (c *Core) doOneAddrWithRetry(method string, apiPath string, addr string, payLoad json.RawMessage, ports ...int) (data []byte, err error) {
	var allErrors []error
	var ar apiResponse
	err = retry.Do(
		func() error {
			ep := url.URL{
				Scheme: "http",
				Host:   addr,
				Path:   apiPath,
			}
			req, err := http.NewRequest(method, ep.String(), bytes.NewBuffer(payLoad))
			if err != nil {
				return err
			}

			q := req.URL.Query()
			if c.debug && c.ip != "" {
				q.Add("ip", c.ip)
			}
			q.Add("bk_cloud_id", fmt.Sprintf("%d", c.bkCloudId))
			for _, port := range ports {
				q.Add("port", fmt.Sprintf("%d", port))
			}
			req.URL.RawQuery = q.Encode()
			req.Header.Set("Content-Type", "application/json")

			resp, err := c.client.Do(req)
			if err != nil {
				return err
			}
			defer func() {
				_, _ = io.Copy(io.Discard, resp.Body)
				_ = resp.Body.Close()
			}()

			data, err = io.ReadAll(resp.Body)
			if err != nil {
				return err
			}

			if resp.StatusCode != http.StatusOK {
				return errors.Errorf("unexpected status code %d (%s)", resp.StatusCode, resp.Status)
			}

			if err := json.Unmarshal(data, &ar); err != nil {
				return err
			}

			if !ar.Result {
				return errors.Errorf(
					"unexpected status code %d, msg: %s, err: %s", ar.Code, ar.Message, ar.Errors)
			}

			return nil
		},
		retry.Attempts(5),
		retry.DelayType(retry.FixedDelay),
		retry.Delay(1*time.Second),
		retry.OnRetry(func(n uint, err error) {
			allErrors = append(allErrors, errors.Wrapf(err, "backoff %d", n))
		}),
	)

	if err != nil {
		return nil, err2.Join(allErrors...)
	}

	return ar.Data, nil
}

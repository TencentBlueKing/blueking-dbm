/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package hanet

import (
	"bytes"
	"io"
	"net/http"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"

	"golang.org/x/net/context"
)

type HttpMethod string

const (
	HttpMethodPost   HttpMethod = "POST"
	HttpMethodGet    HttpMethod = "GET"
	HttpMethodPut    HttpMethod = "PUT"
	HttpMethodDelete HttpMethod = "DELETE"
)

var supportedHttpMethods map[HttpMethod]struct{} = map[HttpMethod]struct{}{
	HttpMethodPost:   {},
	HttpMethodGet:    {},
	HttpMethodPut:    {},
	HttpMethodDelete: {},
}

type HttpClient struct {
	headers map[string]string
	cli     *http.Client
}

func NewHttpClient() *HttpClient {
	return &HttpClient{
		headers: map[string]string{},
		cli:     &http.Client{},
	}
}

func (h HttpMethod) String() string {
	return string(h)
}

func (c HttpClient) verifyMethod(method HttpMethod) error {
	if _, exists := supportedHttpMethods[method]; exists {
		return nil
	}

	return gerrors.Newf(gerrors.InvalidHttpMethod, "invalid http method: %s, errmsg: unsupported", method)
}

// Request post the request with URL
//
// url: the requet address, eg: http://127.0.0.1/request
// method: POST,GET,DELETE,PUT
// headers: http request header
// timeout: the http request timeout(seconds)
// data: the http request data
func (c HttpClient) Request(url string, method HttpMethod, headers map[string]string,
	timeout time.Duration, data []byte) (code int, resp []byte, err error) {

	if err = c.verifyMethod(method); err != nil {
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	var req *http.Request
	var errReq error

	if data != nil {
		req, errReq = http.NewRequestWithContext(ctx, method.String(), url, bytes.NewReader(data))
	} else {
		req, errReq = http.NewRequestWithContext(ctx, method.String(), url, nil)
	}

	if errReq != nil {
		err = gerrors.NewE(gerrors.HttpRequestFailed, err)
		return
	}

	// set the default headers
	for key, val := range c.headers {
		req.Header.Set(key, val)
	}

	// set the headers of this request
	for key, val := range headers {
		req.Header.Set(key, val)
	}

	rsp, errDo := c.cli.Do(req)
	if errDo != nil {
		err = gerrors.NewE(gerrors.HttpRequestFailed, errDo)
		return
	}

	defer func() {
		if errClose := rsp.Body.Close(); errClose != nil {
			logger.Warn("failed to close the http respond body, errmsg: %v", errClose)
		}
	}()

	resp, errRead := io.ReadAll(rsp.Body)
	if errRead != nil {
		err = gerrors.NewE(gerrors.HttpRequestFailed, errRead)
		return
	}

	return
}

package api

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/url"
	"strings"

	"github.com/pkg/errors"
)

func (m *Manager) do(endpoint string, method string, payLoad interface{}) ([]byte, error) {
	apiUrl, err := url.JoinPath(m.apiUrl, endpoint)
	if err != nil {
		return nil, errors.Wrap(err, "join api url")
	}

	body, err := json.Marshal(payLoad)
	if err != nil {
		return nil, errors.Wrap(err, "marshal payload")
	}

	var req *http.Request
	if method == http.MethodGet {
		req, err = http.NewRequest(method, apiUrl, nil)
		if payLoad != nil {
			if queryParam, ok := payLoad.(url.Values); ok {
				req.URL.RawQuery = queryParam.Encode()
			}
		}
	} else {
		req, err = http.NewRequest(
			strings.ToUpper(method),
			apiUrl,
			bytes.NewReader(body),
		)
	}

	if err != nil {
		return nil, errors.Wrap(err, "new request")
	}

	resp, err := m.client.Do(req)
	if err != nil {
		return nil, errors.Wrap(err, "call http api")
	}
	defer func() {
		_ = resp.Body.Close()
	}()
	var respBody []byte
	if resp.Body != nil {
		respBody, err = io.ReadAll(resp.Body)
		if err != nil {
			return nil, errors.Wrap(err, "read resp body")
		}
	}
	if resp.StatusCode != http.StatusOK {
		return respBody, errors.Errorf("http code: %d, status: %s, resp body: %s",
			resp.StatusCode, resp.Status, string(respBody))
	}
	return respBody, nil
}

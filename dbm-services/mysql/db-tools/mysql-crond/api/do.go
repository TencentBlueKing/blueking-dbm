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

func (m *Manager) do(action string, method string, payLoad interface{}) ([]byte, error) {
	apiUrl, err := url.JoinPath(m.apiUrl, action)
	if err != nil {
		return nil, errors.Wrap(err, "join api url")
	}

	body, err := json.Marshal(payLoad)
	if err != nil {
		return nil, errors.Wrap(err, "marshal payload")
	}

	req, err := http.NewRequest(
		strings.ToUpper(method),
		apiUrl,
		bytes.NewReader(body),
	)
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

	if resp.StatusCode != http.StatusOK {
		respBody, _ := io.ReadAll(resp.Body)
		return nil, errors.Errorf("http code: %d, status: %s, resp body: %s",
			resp.StatusCode, resp.Status, string(respBody))
	}

	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, errors.Wrap(err, "read resp body")
	}
	return respBody, nil
}

package internal

import (
	"bufio"
	"dbm-services/common/reverse-api/config"
	"encoding/json"
	errs "errors"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strconv"

	"github.com/pkg/errors"
)

func ReverseCall(api config.ReverseApiName, bkCloudId int, ports ...int) (data []byte, err error) {
	addrs, err := readNginxProxyAddrs()
	if err != nil {
		return nil, errors.Wrap(err, "failed to read nginx proxy addresses")
	}

	var errCollect []error
	for _, addr := range addrs {
		apiPath, _ := url.JoinPath(config.ReverseApiBase, api.String(), "/")
		ep := url.URL{
			Scheme: "http",
			Host:   addr,
			Path:   apiPath,
		}

		req, err := http.NewRequest(http.MethodGet, ep.String(), nil)
		if err != nil {
			return nil, errors.Wrap(err, "failed to create request")
		}

		q := req.URL.Query()
		q.Add("bk_cloud_id", strconv.Itoa(bkCloudId))
		for _, port := range ports {
			q.Add("port", strconv.Itoa(port))
		}
		req.URL.RawQuery = q.Encode()

		data, err = do(req)
		if err == nil {
			return data, nil
		}
		errCollect = append(errCollect, err)
	}

	return nil, errs.Join(errCollect...)
}

func do(request *http.Request) (data []byte, err error) {
	resp, err := http.DefaultClient.Do(request)
	if err != nil {
		return nil, errors.Wrap(err, "failed to send request")
	}
	defer func() {
		_ = resp.Body.Close()
	}()

	b, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, errors.Wrap(err, "failed to read response body")
	}

	if resp.StatusCode != http.StatusOK {
		return nil, errors.Errorf("unexpected status code: %d, body: %s", resp.StatusCode, string(b))
	}

	var r apiResponse
	err = json.Unmarshal(b, &r)
	if err != nil {
		return nil, errors.Wrap(err, "failed to unmarshal response body")
	}

	if !r.Result {
		return nil, errors.Errorf("unexpected status code: %d, body: %s", resp.StatusCode, r.Errors)
	}

	return r.Data, nil
}

func readNginxProxyAddrs() (addrs []string, err error) {
	f, err := os.Open(filepath.Join(config.CommonConfigDir, config.NginxProxyAddrsFileName))
	if err != nil {
		return nil, errors.Wrap(err, "failed to open nginx proxy addrs")
	}
	defer func() {
		_ = f.Close()
	}()

	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		addrs = append(addrs, scanner.Text())
	}
	if err := scanner.Err(); err != nil {
		return nil, errors.Wrap(err, "failed to read nginx proxy addrs")
	}
	return addrs, nil
}

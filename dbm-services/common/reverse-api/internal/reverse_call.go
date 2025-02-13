package internal

import (
	"bufio"
	"dbm-services/common/reverse-api/config"
	"encoding/json"
	errs "errors"
	"io"
	"log/slog"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/pkg/errors"
)

func ReverseCall(api config.ReverseApiName, bkCloudId int, ports ...int) (data []byte, err error) {
	addrs, err := readNginxProxyAddrs()
	if err != nil {
		return nil, errors.Wrap(err, "failed to read nginx proxy addresses")
	}
	slog.Info("reserve call", slog.String("nginx addrs", strings.Join(addrs, ",")))

	var errCollect []error
	for _, addr := range addrs {
		slog.Info("reserve call", slog.String("on addr", addr))
		apiPath, _ := url.JoinPath(config.ReverseApiBase, api.String(), "/")
		ep := url.URL{
			Scheme: "http",
			Host:   addr,
			Path:   apiPath,
		}
		slog.Info("reserve call", slog.String("endpoint", ep.String()))

		req, err := http.NewRequest(http.MethodGet, ep.String(), nil)
		if err != nil {
			slog.Error("reserve call create request", slog.String("error", err.Error()))
			errCollect = append(errCollect, err)
			continue
		}

		q := req.URL.Query()
		q.Add("bk_cloud_id", strconv.Itoa(bkCloudId))
		for _, port := range ports {
			q.Add("port", strconv.Itoa(port))
		}
		req.URL.RawQuery = q.Encode()

		data, err = do(req)
		if err == nil {
			slog.Info("reserve call", slog.String("data len", strconv.Itoa(len(data))))
			return data, nil
		}
		slog.Error("reserve call do request", slog.String("error", err.Error()))
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
		return nil, errors.Errorf("unexpected status code: %d, msg: %s, error: %s", r.Code, r.Message,
			r.Errors)
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

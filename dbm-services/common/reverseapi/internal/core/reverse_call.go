package core

import (
	"fmt"

	"encoding/json"
	errs "errors"
	"io"
	"log/slog"
	"net/http"
	"net/url"
	"strconv"

	"github.com/pkg/errors"
	"github.com/spf13/viper"
)

const reverseApiBase = "apis/proxypass/reverse_api"

func (c *Core) ReverseCall(apiEndPoint string, ports ...int) (data []byte, err error) {
	var errCollect []error
	for _, addr := range c.nginxAddrs {
		slog.Info("reserve call", slog.String("on addr", addr))
		apiPath, _ := url.JoinPath(reverseApiBase, apiEndPoint, "/")
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
		// 调试代码
		if viper.GetString("debug-ip") != "" {
			q.Add("ip", viper.GetString("debug-ip"))
		}
		q.Add("bk_cloud_id", fmt.Sprintf("%d", c.bkCloudId))
		for _, port := range ports {
			q.Add("port", strconv.Itoa(port))
		}
		req.URL.RawQuery = q.Encode()
		slog.Info("reserve call", slog.String("req", req.URL.String()))

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
	slog.Info("reserve call", slog.String("response body", string(b)))

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

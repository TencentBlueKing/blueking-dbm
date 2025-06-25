package core

import (
	"encoding/json"
	"io"
	"net/http"

	"github.com/pkg/errors"
)

func do(client *http.Client, request *http.Request) (data []byte, err error) {
	resp, err := client.Do(request)
	//resp, err := http.DefaultClient.Do(request)
	if err != nil {
		return nil, errors.Wrap(err, "failed to send request")
	}
	defer func() {
		_, _ = io.ReadAll(resp.Body) //io.CopyN(io.Discard, resp.Body, 1024*1024)
		_ = resp.Body.Close()
	}()

	b, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, errors.Wrap(err, "failed to read response body")
	}
	//slog.Info("reserve call", slog.String("response body", string(b)))

	if resp.StatusCode != http.StatusOK {
		return nil, errors.Errorf("unexpected status code: %d, body: %s", resp.StatusCode, string(b))
	}

	var r apiResponse
	err = json.Unmarshal(b, &r)
	if err != nil {
		return nil, errors.Wrap(err, "failed to unmarshal response body")
	}

	if !r.Result {
		return r.Errors, errors.Errorf("unexpected status code: %d, msg: %s, error: %s", r.Code, r.Message,
			r.Errors)
	}

	return r.Data, nil
}

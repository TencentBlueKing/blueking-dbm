package backend

import (
	"bytes"
	"dbm-services/common/db-mcp-server/internal/config"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
)

func Call(name string, body []byte) ([]byte, error) {
	name = strings.TrimRight(name, "/")
	ep, err := url.JoinPath(config.Config.MCPBackendBaseURL, name, "/")
	if err != nil {
		return nil, err
	}

	req, err := http.NewRequest("POST", ep, bytes.NewBuffer(body))
	if err != nil {
		return nil, err
	}

	req.Header.Set("Content-Type", "application/json")

	//if config.Config.WithAuthCheck != nil && *config.Config.WithAuthCheck {
	//	req.Header.Set("X-Bk-Username", username)
	//}

	//if config.Config.WithAuthCheck != nil && *config.Config.WithAuthCheck {
	//	logger.Info("set username into header: %s", username)
	//	req.Header.Set(
	//		"x-bkapi-authorization",
	//		fmt.Sprintf(
	//			`{"bk_username": "%s"}`,
	//			username,
	//		),
	//	)

	//req.Header.Set(
	//	"x-bkapi-authorization",
	//	fmt.Sprintf(
	//		`{"bk_app_code": %s, "bk_app_secret": %s}`,
	//		config.Config.BKAppCode, config.Config.BKAppSecret,
	//	),
	//)

	//req.AddCookie(
	//	&http.Cookie{
	//		Name:   "bk_app_code",
	//		Path:   "/",
	//		Value:  config.Config.BKAppCode,
	//		MaxAge: 86400,
	//	},
	//)
	//req.AddCookie(
	//	&http.Cookie{
	//		Name:   "bk_app_secret",
	//		Path:   "/",
	//		Value:  config.Config.BKAppSecret,
	//		MaxAge: 86400,
	//	},
	//)
	//}

	resp, err := httpClient.Do(req)
	if err != nil {
		return nil, err
	}

	defer func() {
		_ = resp.Body.Close()
	}()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("call failed with code %d", resp.StatusCode)
	}

	b, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	br := backendResponse{}
	err = json.Unmarshal(b, &br)
	if err != nil {
		if resp.Request.Method == http.MethodGet {
			return nil, fmt.Errorf("用户鉴权失败")
		}
		return nil, err
	}

	if br.Code != 0 {
		return nil, fmt.Errorf("call failed with code %d, message %s", br.Code, br.Message)
	}

	return br.Data, nil
}

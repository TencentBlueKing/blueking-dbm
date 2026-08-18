package consumer

import (
	"encoding/json"
	"io"
	"net/http"
	"net/url"
	"os"
	"strconv"
	"strings"

	"dbm-services/common/dbm-backup-server/backup-consumer/pkg/config"

	"github.com/pkg/errors"
	"golang.org/x/exp/slog"
)

// queryMeta query data_id from bklog api metadata_get_data_id
func queryMeta() error {
	params := url.Values{}
	params.Add("bk_data_id", strconv.Itoa(config.RuntimeConfig.BkDataId))
	metaApiPath := "app/metadata/get_data_id" // bkmonitorv3:metadata_get_data_id
	urlPath, err := url.JoinPath(config.RuntimeConfig.BkmonitorApiUrl, metaApiPath)
	if err != nil {
		slog.Error("join api path", err)
		return err
	}

	endpoint, err := url.Parse(urlPath)
	if err != nil {
		slog.Error("parse url", err, slog.String("url", urlPath))
		return err
	}

	endpoint.RawQuery = params.Encode()

	req, err := http.NewRequest(http.MethodGet, endpoint.String(), nil)
	if err != nil {
		slog.Error("new request", err)
		return err
	}

	content, err := json.Marshal(struct {
		BkAppCode   string `json:"bk_app_code"`
		BkAppSecret string `json:"bk_app_secret"`
		BkUsername  string `json:"bk_username"`
	}{
		BkAppCode:   config.RuntimeConfig.BkAppCode,
		BkAppSecret: config.RuntimeConfig.BkAppSecret,
		BkUsername:  "admin",
	})
	if err != nil {
		slog.Error("pack header", err.Error())
		return err
	}
	slog.Info("pack header", slog.String("header", string(content)))

	req.Header.Set("X-Bkapi-Authorization", string(content))
	if bkTenantId := os.Getenv("BK_TENANT_ID"); bkTenantId != "" {
		req.Header.Set("X-Bk-Tenant-Id", bkTenantId)
	}
	//req.Header.Set("Content-Type", "application/json")
	slog.Info("request", slog.Any("request", req))

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		slog.Error("call http api", err)
		return err
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 400 {
		err := errors.Errorf("code: %d, msg: %s", resp.StatusCode, resp.Status)
		slog.Error("call http api", err)
		return err
	}

	defer func() {
		_ = resp.Body.Close()
	}()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		slog.Error("read body", err)
		return err
	}

	var res struct {
		Result  bool   `json:"result"`
		Code    int    `json:"code"`
		Message string `json:"message"`
		Data    struct {
			MqConfig config.KafkaMeta `json:"mq_config"`
		} `json:"data"`
	}

	err = json.Unmarshal(body, &res)
	if err != nil {
		slog.Error("unmarshal response", err)
		return err
	}
	if !res.Result {
		err := errors.Errorf("api failed code: %d, message: %s", res.Code, res.Message)
		slog.Error("check api response", err)
		return err
	}

	config.MetaInfo = &res.Data.MqConfig

	if config.RuntimeConfig.AltBroker != nil {
		splitBroker := strings.Split(*config.RuntimeConfig.AltBroker, ":")
		config.MetaInfo.ClusterConfig.DomainName = splitBroker[0]

		altPort, err := strconv.Atoi(splitBroker[1])
		if err != nil {
			slog.Error("parse alt broker port", err)
			return err
		}
		config.MetaInfo.ClusterConfig.Port = altPort
	}

	return nil
}

// ListBkDataId 调用 bklog databus_collectors 接口获取 collectors 列表
// 按 collector_config_name_en 匹配提取 bk_data_id，返回 map[collector_config_name_en]*BkDataConfig
func ListBkDataId(bkdata *config.BkmApiInfo) (map[string]*config.BkDataConfig, error) {
	if bkdata == nil {
		return nil, errors.New("bkm_api_info config for bklog is nil")
	}
	listCollectorsPath := "databus_collectors"
	urlPath, err := url.JoinPath(bkdata.BklogApiUrl, listCollectorsPath)
	if err != nil {
		slog.Error("join api path", err)
		return nil, err
	}

	params := url.Values{}
	params.Add("bk_biz_id", strconv.Itoa(bkdata.BkBizId))
	params.Add("pagesize", "100")
	params.Add("page", "1")

	endpoint, err := url.Parse(urlPath)
	if err != nil {
		slog.Error("parse url", err, slog.String("url", urlPath))
		return nil, err
	}
	endpoint.RawQuery = params.Encode()

	req, err := http.NewRequest(http.MethodGet, endpoint.String(), nil)
	if err != nil {
		slog.Error("new request", err)
		return nil, err
	}

	content, err := json.Marshal(struct {
		BkAppCode   string `json:"bk_app_code"`
		BkAppSecret string `json:"bk_app_secret"`
		BkUsername  string `json:"bk_username"`
	}{
		BkAppCode:   bkdata.BkAppCode,
		BkAppSecret: bkdata.BkAppSecret,
		BkUsername:  "admin",
	})
	if err != nil {
		slog.Error("pack header", err.Error())
		return nil, err
	}

	req.Header.Set("X-Bkapi-Authorization", string(content))
	if bkTenantId := os.Getenv("BK_TENANT_ID"); bkTenantId != "" {
		req.Header.Set("X-Bk-Tenant-Id", bkTenantId)
	}
	slog.Info("ListBkDataId request", slog.String("url", endpoint.String()))

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		slog.Error("call http api", err)
		return nil, err
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 400 {
		err := errors.Errorf("code: %d, msg: %s", resp.StatusCode, resp.Status)
		slog.Error("call http api", err)
		return nil, err
	}

	defer func() {
		_ = resp.Body.Close()
	}()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		slog.Error("read body", err)
		return nil, err
	}

	var res struct {
		Result  bool   `json:"result"`
		Code    int    `json:"code"`
		Message string `json:"message"`
		Data    struct {
			Total int                   `json:"total"`
			List  []config.BkDataConfig `json:"list"`
		} `json:"data"`
	}
	err = json.Unmarshal(body, &res)
	if err != nil {
		slog.Error("unmarshal response", err)
		return nil, err
	}
	if !res.Result {
		err := errors.Errorf("api failed code: %d, message: %s", res.Code, res.Message)
		slog.Error("check api response", err)
		return nil, err
	}

	// 按 collector_config_name_en 构建 map
	collectorsMap := make(map[string]*config.BkDataConfig, len(res.Data.List))
	for i := range res.Data.List {
		c := &res.Data.List[i]
		if c.CollectorConfigNameEn != "" {
			collectorsMap[c.CollectorConfigNameEn] = c
		}
	}
	slog.Info("ListBkDataId result",
		slog.Int("total", res.Data.Total),
		slog.Int("matched", len(collectorsMap)))

	return collectorsMap, nil
}

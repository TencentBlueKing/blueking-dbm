// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package sinker

import (
	"bytes"
	"fmt"
	"io"
	"log/slog"
	"math/rand"
	"net"
	"net/http"
	"strings"
	"time"

	json "github.com/goccy/go-json"
	"github.com/pkg/errors"
	"gorm.io/gorm"
	"gorm.io/gorm/schema"
)

// DorisHttpDsn Doris HTTP Stream Load 连接配置
type DorisHttpDsn struct {
	User     string `yaml:"user" mapstructure:"user"`
	Password string `yaml:"password" mapstructure:"password"`
	// Address mysql, 用于 AutoMigrate（DDL），格式为 host:port（默认端口 9030）
	Address  string `yaml:"address" mapstructure:"address"`
	Database string `yaml:"database" mapstructure:"database"`
	// FeHttpAddress 为 Doris FE 的 HTTP 地址，支持逗号分隔的多个 ip:port（默认端口 8030）。
	// 如果为空，则取 Address 的 host:8030
	FeHttpAddress string `yaml:"fe_http_address" mapstructure:"fe_http_address"`
}

// DorisHttpWriter 使用 Doris HTTP Stream Load 接口写入数据
type DorisHttpWriter struct {
	dsn             *DorisHttpDsn
	dbGorm          *gorm.DB // 用于 AutoMigrate
	httpClient      *http.Client
	writeMode       string
	feHttpAddresses []string // 解析后的 FE HTTP 地址列表
}

func NewDorisHttpWriter(dsn *DorisHttpDsn) (*DorisHttpWriter, error) {
	if dsn == nil {
		return nil, errors.New("dsn is nil")
	}
	if dsn.Database == "" {
		return nil, errors.New("doris database is required")
	}

	// 解析 FE HTTP 地址列表
	feAddresses, err := parseFeHttpAddresses(dsn.FeHttpAddress, dsn.Address)
	if err != nil {
		return nil, err
	}

	// 初始化 gorm 连接用于 AutoMigrate（DDL 操作仍需 MySQL 协议）
	var dbGorm *gorm.DB
	if dsn.Address != "" {
		mysqlDsn := &InstanceDsn{
			User:     dsn.User,
			Password: dsn.Password,
			Address:  dsn.Address,
			Database: dsn.Database,
		}
		var err error
		dbGorm, err = GetGormDB(mysqlDsn)
		if err != nil {
			return nil, errors.WithMessage(err, "init gorm db for doris http writer")
		}
	}

	// 禁止自动重定向，因为 FE 会返回 307 重定向到 BE 节点，
	// Go 默认的重定向处理会丢失 PUT body，需要手动处理
	httpClient := &http.Client{
		Timeout: 60 * time.Second,
		CheckRedirect: func(req *http.Request, via []*http.Request) error {
			return http.ErrUseLastResponse
		},
	}

	return &DorisHttpWriter{
		dsn:             dsn,
		dbGorm:          dbGorm,
		httpClient:      httpClient,
		feHttpAddresses: feAddresses,
	}, nil
}

// parseFeHttpAddresses 解析 FE HTTP 地址列表。
// 支持逗号分隔的多个 ip:port，如果为空则取 address 的 host:8030
func parseFeHttpAddresses(feHttpAddress, address string) ([]string, error) {
	if feHttpAddress != "" {
		parts := strings.Split(feHttpAddress, ",")
		var addresses []string
		for _, p := range parts {
			p = strings.TrimSpace(p)
			if p != "" {
				addresses = append(addresses, p)
			}
		}
		if len(addresses) > 0 {
			return addresses, nil
		}
	}
	// FeHttpAddress 为空，从 Address 中提取 host，拼接默认端口 8030
	if address == "" {
		return nil, errors.New("both fe_http_address and address are empty, cannot determine FE HTTP address")
	}
	host, _, err := net.SplitHostPort(address)
	if err != nil {
		// address 可能没有端口，直接当作 host
		host = address
	}
	return []string{fmt.Sprintf("%s:8030", host)}, nil
}

// pickFeAddress 从 FE 地址列表中随机选择一个
func (w *DorisHttpWriter) pickFeAddress() string {
	if len(w.feHttpAddresses) == 1 {
		return w.feHttpAddresses[0]
	}
	return w.feHttpAddresses[rand.Intn(len(w.feHttpAddresses))]
}

func (w *DorisHttpWriter) Type() string {
	return "doris_http"
}

func (w *DorisHttpWriter) AutoMigrate(m interface{}) error {
	if w.dbGorm == nil {
		slog.Warn("DorisHttpWriter: mysql_address not configured, skip AutoMigrate")
		return nil
	}
	slog.Info("DorisHttpWriter run common migrate for", slog.Any("model", m))
	return w.dbGorm.Migrator().AutoMigrate(m)
}

// WriteBatch 使用 Doris HTTP Stream Load 写入一批数据。
// 直接将 models 序列化为 JSON，避免 struct -> map -> json 的多层转换。
func (w *DorisHttpWriter) WriteBatch(table interface{}, models interface{}) error {
	tableName, err := w.getTableName(table)
	if err != nil {
		return err
	}

	return w.writeBatchJSON(tableName, models)
}

// WriteBatchJSON 使用 Doris HTTP Stream Load 接口写入一批数据（快路径）。
func (w *DorisHttpWriter) WriteBatchJSON(table interface{}, models interface{}) error {
	tableName, err := w.getTableName(table)
	if err != nil {
		return err
	}

	return w.writeBatchJSON(tableName, models)
}

func (w *DorisHttpWriter) writeBatchJSON(tableName string, models interface{}) error {
	jsonData, err := json.Marshal(models)
	if err != nil {
		return errors.WithMessage(err, "marshal models to json")
	}
	if len(jsonData) == 0 || string(jsonData) == "null" || string(jsonData) == "[]" {
		return nil
	}

	return w.streamLoadRaw(tableName, jsonData)
}

func (w *DorisHttpWriter) OnDuplicate(objs interface{}) error {
	return nil
}

func (w *DorisHttpWriter) SetWriteMode(mode string) {
	w.writeMode = mode
}

func (w *DorisHttpWriter) GetWriteMode() string {
	return w.writeMode
}

func (w *DorisHttpWriter) GormDB() *gorm.DB {
	return w.dbGorm
}

func (w *DorisHttpWriter) CloseGormDB() error {
	if w.dbGorm == nil {
		return nil
	}
	db, _ := w.dbGorm.DB()
	return db.Close()
}

// streamLoadRaw 执行 Doris Stream Load HTTP 请求（接收已序列化的 JSON 字节）。
// FE 收到请求后会返回 307 重定向到 BE 节点，需要手动跟随重定向并重新发送数据。
func (w *DorisHttpWriter) streamLoadRaw(tableName string, jsonData []byte) error {
	// 构建 Stream Load URL: http://<fe_host>:<fe_http_port>/api/<db>/<table>/_stream_load
	feAddr := w.pickFeAddress()
	feURL := fmt.Sprintf("http://%s/api/%s/%s/_stream_load", feAddr, w.dsn.Database, tableName)

	// 第一步：发送请求到 FE，获取 BE 重定向地址
	req, err := http.NewRequest(http.MethodPut, feURL, bytes.NewReader(jsonData))
	if err != nil {
		return errors.WithMessage(err, "create stream load request")
	}
	w.setStreamLoadHeaders(req)

	resp, err := w.httpClient.Do(req)
	if err != nil {
		return errors.WithMessagef(err, "stream load request to FE %s", feURL)
	}
	defer resp.Body.Close()

	// 第二步：处理 FE 的 307 重定向，将数据发送到 BE 节点
	if resp.StatusCode == http.StatusTemporaryRedirect {
		beURL := resp.Header.Get("Location")
		if beURL == "" {
			return errors.Errorf("FE returned 307 but no Location header, url=%s", feURL)
		}
		// 关闭 FE 响应体
		io.Copy(io.Discard, resp.Body)
		resp.Body.Close()
		// slog.Debug("stream load redirected to BE", slog.String("be_url", beURL))

		// 重新构建请求发送到 BE
		beReq, err := http.NewRequest(http.MethodPut, beURL, bytes.NewReader(jsonData))
		if err != nil {
			return errors.WithMessagef(err, "create stream load request to BE %s", beURL)
		}
		w.setStreamLoadHeaders(beReq)

		beResp, err := w.httpClient.Do(beReq)
		if err != nil {
			return errors.WithMessagef(err, "stream load request to BE %s. data:%s", beURL, string(jsonData))
		}
		defer beResp.Body.Close()

		err = w.parseStreamLoadResponse(beResp, tableName)
		if err != nil {
			return errors.WithMessagef(err, "stream load response from BE %s. data:%s", beURL, string(jsonData))
		}
		return nil
	}

	// 如果 FE 没有重定向（比如直接连 BE 或者某些版本直接返回结果），直接解析响应
	return w.parseStreamLoadResponse(resp, tableName)
}

// setStreamLoadHeaders 设置 Stream Load 请求的公共 Header
func (w *DorisHttpWriter) setStreamLoadHeaders(req *http.Request) {
	req.SetBasicAuth(w.dsn.User, w.dsn.Password)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("format", "json")
	req.Header.Set("strip_outer_array", "true")
	req.Header.Set("Expect", "100-continue")
}

// parseStreamLoadResponse 解析 Stream Load 响应
func (w *DorisHttpWriter) parseStreamLoadResponse(resp *http.Response, tableName string) error {
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return errors.WithMessage(err, "read stream load response")
	}

	var result streamLoadResponse
	if err = json.Unmarshal(body, &result); err != nil {
		return errors.WithMessagef(err, "unmarshal stream load response: %s", string(body))
	}

	// 检查结果状态
	if result.Status != "Success" && result.Status != "Publish Timeout" {
		return errors.Errorf("stream load failed for table %s: status=%s, message=%s, errorURL=%s",
			tableName, result.Status, result.Message, result.ErrorURL)
	}
	/*
		slog.Debug("stream load success",
			slog.String("table", tableName),
			slog.Int64("loaded_rows", result.NumberLoadedRows),
			slog.Int64("filtered_rows", result.NumberFilteredRows)
	*/
	return nil
}

// streamLoadResponse Doris Stream Load 响应结构
type streamLoadResponse struct {
	TxnID              int64  `json:"TxnId"`
	Label              string `json:"Label"`
	Status             string `json:"Status"`
	Message            string `json:"Message"`
	NumberTotalRows    int64  `json:"NumberTotalRows"`
	NumberLoadedRows   int64  `json:"NumberLoadedRows"`
	NumberFilteredRows int64  `json:"NumberFilteredRows"`
	NumberUnselRows    int64  `json:"NumberUnselectedRows"`
	LoadBytes          int64  `json:"LoadBytes"`
	LoadTimeMs         int64  `json:"LoadTimeMs"`
	ErrorURL           string `json:"ErrorURL"`
}

// getTableName 从 table 对象获取表名
func (w *DorisHttpWriter) getTableName(table interface{}) (string, error) {
	if t, ok := table.(schema.Tabler); ok {
		return t.TableName(), nil
	}
	return "", errors.Errorf("cannot find TableName() for table %v", table)
}

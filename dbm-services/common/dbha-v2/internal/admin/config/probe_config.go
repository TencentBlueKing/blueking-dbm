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

package config

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net/http"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/pkg/constant"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/probeconfig"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"

	"gorm.io/gorm"
)

var (
	ErrDbNil  = gerrors.New(gerrors.InvalidParameter, "db is nil")
	ErrNoData = gerrors.New(gerrors.NotExist, "no data")
)

// GenProbeConfig returns probe metadata as JSON by cloudid + ip: first from DBHA DB, then from DBM API if not found.
// The probe uses this metadata to generate the final probe config YAML locally.
func GenProbeConfig(ctx context.Context, db *hamysql.GormDB, bkCloudID int, ip string) (string, error) {
	if db == nil {
		return "", ErrDbNil
	}

	// 1. Query DBHA own database for metadata (bk_cloud_id + ip)
	list, err := getMetadataFromDBHA(db, bkCloudID, ip)
	if err != nil {
		return "", err
	}

	if len(list) > 0 {
		items := convertFromDBHA(list)
		data, err := json.Marshal(items)
		if err != nil {
			return "", gerrors.NewE(gerrors.InvalidJson, err)
		}
		return string(data), nil
	}

	// 2. Not found in DBHA: fetch from DBM API
	dmList, err := getMetadataFromDBM(ctx, bkCloudID, ip)
	if err != nil {
		return "", err
	}
	if len(dmList) == 0 {
		logger.Warnf("no metadata for bk_cloud_id: %d, ip: %s", bkCloudID, ip)
		return "", ErrNoData
	}

	items := convertFromDBM(dmList)
	data, err := json.Marshal(items)
	if err != nil {
		return "", gerrors.NewE(gerrors.InvalidParameter, err)
	}
	return string(data), nil
}

// convertFromDBHA converts DBHA metadata to probe metadata items.
func convertFromDBHA(list []*hamodel.DbmMetadata) []probeconfig.ProbeMetadataItem {
	out := make([]probeconfig.ProbeMetadataItem, 0, len(list))
	for _, m := range list {
		out = append(out, probeconfig.ProbeMetadataItem{
			IP:          m.IP,
			Port:        m.Port,
			AdminPort:   m.AdminPort,
			ClusterType: string(m.ClusterType),
			MachineType: string(m.MachineType),
			AccessLayer: string(m.AccessLayer),
		})
	}
	return out
}

// convertFromDBM converts DBM API metadata to probe metadata items.
func convertFromDBM(list []*dbm.DbInstMetadata) []probeconfig.ProbeMetadataItem {
	out := make([]probeconfig.ProbeMetadataItem, 0, len(list))
	for _, m := range list {
		out = append(out, probeconfig.ProbeMetadataItem{
			IP:          m.IP,
			Port:        m.Port,
			AdminPort:   m.AdminPort,
			ClusterType: string(m.ClusterType),
			MachineType: string(m.MachineType),
			AccessLayer: string(m.AccessLayer),
		})
	}
	return out
}

// getMetadataFromDBHA queries t_dbm_metadata by bk_cloud_id and ip.
func getMetadataFromDBHA(db *hamysql.GormDB, bkCloudID int, ip string) ([]*hamodel.DbmMetadata, error) {
	var list []*hamodel.DbmMetadata
	err := db.DB().Model(&hamodel.DbmMetadata{}).
		Where(hamodel.DbmMetadataFieldBkCloudID+" = ?", bkCloudID).
		Where(hamodel.DbmMetadataFieldListenIP+" = ?", ip).
		Find(&list).Error

	if err != nil {
		if err == gorm.ErrRecordNotFound {
			return nil, nil
		}
		return nil, gerrors.NewE(gerrors.MysqlFailure, err)
	}
	return list, nil
}

// getMetadataFromDBM calls DBM metadata API (admin config DbmApis name=metadata).
func getMetadataFromDBM(ctx context.Context, bkCloudID int, ip string) ([]*dbm.DbInstMetadata, error) {
	var api *DbmApi
	for i := range Cfg.DbmApis {
		if Cfg.DbmApis[i].Name == constant.DbmApiNameMetadata {
			api = &Cfg.DbmApis[i]
			break
		}
	}
	if api == nil {
		return nil, gerrors.Newf(gerrors.InvalidParameter, "dbm api %q not found", constant.DbmApiNameMetadata)
	}

	req := dbm.Request{
		BkCloudId:    bkCloudID,
		Addresses:    []string{ip},
		DbCloudToken: api.Token,
		MachineOnly:  true,
	}
	data, err := json.Marshal(&req)
	if err != nil {
		return nil, gerrors.NewE(gerrors.InvalidParameter, err)
	}

	// POST to admin-configured DBM metadata API
	// Client.RequestMetadata uses config.Cfg.Workflow - we cannot use it from admin.
	// So we do HTTP POST here with admin's api.Api and api.Token (already in req).
	code, resp, err := postJSON(ctx, api.Api, data, api.Timeout)
	if err != nil {
		return nil, err
	}
	if code != http.StatusOK {
		return nil, gerrors.Newf(gerrors.HttpRequestFailure, "DBM metadata api returned status %d", code)
	}

	var metaResp dbm.Response
	if err := json.Unmarshal(resp, &metaResp); err != nil {
		return nil, gerrors.NewE(gerrors.InvalidJson, err)
	}
	if !metaResp.Result || len(metaResp.Data) == 0 {
		return nil, nil
	}
	return metaResp.Data, nil
}

// postJSON sends POST request with JSON body. Returns status code, body, error.
func postJSON(ctx context.Context, url string, body []byte, timeout time.Duration) (int, []byte, error) {
	// Use hanet HttpClient for consistency with analysis/dbm
	// We need to avoid importing analysis/config, so we use a minimal HTTP post.
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(body))
	if err != nil {
		return 0, nil, gerrors.NewE(gerrors.HttpRequestFailure, err)
	}

	req.Header.Set("Content-Type", "application/json")
	client := &http.Client{Timeout: timeout}
	resp, err := client.Do(req)
	if err != nil {
		return 0, nil, gerrors.NewE(gerrors.HttpRequestFailure, err)
	}
	defer resp.Body.Close()

	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return resp.StatusCode, nil, gerrors.NewE(gerrors.HttpRequestFailure, err)
	}
	return resp.StatusCode, data, nil
}

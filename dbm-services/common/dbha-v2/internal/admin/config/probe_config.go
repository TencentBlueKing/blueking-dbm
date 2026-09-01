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
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	"gorm.io/gorm"
)

var (
	ErrDbNil  = gerrors.New(gerrors.InvalidParameter, "db is nil")
	ErrNoData = gerrors.New(gerrors.NotExist, "no data")
)

// GenProbeConfig returns ProbeConfigPayload (gse defaults + metadata) as JSON by cloudid + ip:
// metadata is taken from DBHA DB first, then DBM API fallback; gse defaults come from admin config.
// The probe uses this payload to generate the final probe config YAML locally.
func GenProbeConfig(ctx context.Context, db *hamysql.GormDB, bkCloudID int, ip string) (string, error) {
	if db == nil {
		return "", ErrDbNil
	}

	items, err := loadProbeMetadata(ctx, db, bkCloudID, ip)
	if err != nil {
		return "", err
	}
	if len(items) == 0 {
		logger.Warnf("no metadata for bk_cloud_id: %d, ip: %s", bkCloudID, ip)
		return "", ErrNoData
	}

	payload := probeconfig.ProbeConfigPayload{
		Gse: probeconfig.GseConfig{
			Endpoint:        Cfg.ProbeGse.Endpoint,
			DataID:          Cfg.ProbeGse.DataID,
			ConnTimeout:     Cfg.ProbeGse.ConnTimeout,
			LocalSocketPort: Cfg.ProbeGse.LocalSocketPort,
		},
		Metadata: items,
	}

	applyAllHarvesterPayload(&payload)
	return marshalProbeConfigPayload(payload)
}

func applyAllHarvesterPayload(payload *probeconfig.ProbeConfigPayload) {
	payload.MySQL = &probeconfig.ProbeMySQLConfig{
		User:              Cfg.ProbeMysql.User,
		Password:          Cfg.ProbeMysql.Password,
		Interval:          durationToYAMLString(Cfg.ProbeMysql.Interval),
		HeartbeatInterval: durationToYAMLString(Cfg.ProbeMysql.HeartbeatInterval),
		ReplDelayInterval: durationToYAMLString(Cfg.ProbeMysql.ReplDelayInterval),
		Timeout:           durationToYAMLString(Cfg.ProbeMysql.Timeout),
	}
	payload.Redis = &probeconfig.ProbeRedisConfig{
		User:     Cfg.ProbeRedis.User,
		Password: Cfg.ProbeRedis.Password,
		Interval: durationToYAMLString(Cfg.ProbeRedis.Interval),
		Timeout:  durationToYAMLString(Cfg.ProbeRedis.Timeout),
	}
	payload.ProxyAdmin = &probeconfig.ProbeProxyAdminConfig{
		User:              Cfg.ProbeProxyAdmin.User,
		Password:          Cfg.ProbeProxyAdmin.Password,
		Interval:          durationToYAMLString(Cfg.ProbeProxyAdmin.Interval),
		HeartbeatInterval: durationToYAMLString(Cfg.ProbeProxyAdmin.HeartbeatInterval),
		ReplDelayInterval: durationToYAMLString(Cfg.ProbeProxyAdmin.ReplDelayInterval),
		Timeout:           durationToYAMLString(Cfg.ProbeProxyAdmin.Timeout),
	}
}

func marshalProbeConfigPayload(payload probeconfig.ProbeConfigPayload) (string, error) {
	data, err := json.Marshal(payload)
	if err != nil {
		return "", gerrors.NewE(gerrors.InvalidJson, err)
	}
	return string(data), nil
}

// durationToYAMLString formats a time.Duration as the YAML string consumed by probe (e.g. "20s").
// Zero duration returns "" so the rendered probe YAML keeps an empty value rather than "0s".
func durationToYAMLString(d time.Duration) string {
	if d == 0 {
		return ""
	}
	return d.String()
}

// loadProbeMetadata returns probe metadata items from DBHA DB; falls back to DBM API when empty.
func loadProbeMetadata(
	ctx context.Context, db *hamysql.GormDB, bkCloudID int, ip string,
) ([]probeconfig.ProbeMetadataItem, error) {
	list, err := getMetadataFromDBHA(db, bkCloudID, ip)
	if err != nil {
		return nil, err
	}
	if len(list) > 0 {
		return convertFromDBHA(list), nil
	}

	dmList, err := getMetadataFromDBM(ctx, bkCloudID, ip)
	if err != nil {
		return nil, err
	}
	if len(dmList) == 0 {
		return nil, nil
	}
	return convertFromDBM(dmList), nil
}

// convertFromDBHA converts DBHA metadata to probe metadata items.
func convertFromDBHA(list []*hamodel.DbmMetadata) []probeconfig.ProbeMetadataItem {
	out := make([]probeconfig.ProbeMetadataItem, 0, len(list))
	for _, m := range list {
		out = append(out, probeconfig.ProbeMetadataItem{
			IP:           m.IP,
			Port:         m.Port,
			AdminPort:    resolveAdminPort(m.AdminPort, m.InstanceRole),
			ClusterType:  string(m.ClusterType),
			MachineType:  string(m.MachineType),
			InstanceRole: string(m.InstanceRole),
			AccessLayer:  string(m.AccessLayer),
		})
	}
	return out
}

// convertFromDBM converts DBM API metadata to probe metadata items.
func convertFromDBM(list []*dbm.DbInstMetadata) []probeconfig.ProbeMetadataItem {
	out := make([]probeconfig.ProbeMetadataItem, 0, len(list))
	for _, m := range list {
		out = append(out, probeconfig.ProbeMetadataItem{
			IP:           m.IP,
			Port:         m.Port,
			AdminPort:    resolveAdminPort(m.AdminPort, m.InstanceRole),
			ClusterType:  string(m.ClusterType),
			MachineType:  string(m.MachineType),
			InstanceRole: string(m.InstanceRole),
			AccessLayer:  string(m.AccessLayer),
		})
	}
	return out
}

// resolveAdminPort drops admin port for spider_slave nodes so probe skips
// admin-port rendering for them.
func resolveAdminPort(adminPort int, instanceRole haprobe.DbmMetadataInstanceRole) int {
	if instanceRole == haprobe.TenDBClusterProxySlave {
		return 0
	}
	return adminPort
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
		MachineOnly:  false,
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

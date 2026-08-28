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
	"fmt"
	"io"
	"net/http"
	"time"

	"dbm-services/common/dbha-v2/internal/admin/apm"
	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/pkg/constant"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/probeconfig"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"

	"golang.org/x/sync/singleflight"
	"gorm.io/gorm"
)

var (
	ErrDbNil  = gerrors.New(gerrors.InvalidParameter, "db is nil")
	ErrNoData = gerrors.New(gerrors.NotExist, "no data")
)

// Reasons a request could not be answered from the local cache. They are used as a metric
// label, so the set stays small and fixed; anything derived from the request (ip, cloud id)
// would blow up the metric's cardinality.
const (
	fallbackReasonMiss  = "miss"
	fallbackReasonStale = "stale"
)

// dbmFallbackTimeout bounds a DBM lookup when the api entry carries no timeout of its own.
// Some deadline is mandatory here: singleflight holds every caller waiting on the same key
// behind the in-flight call, so one request that never returns would pin them all, and each new
// probe round would add more.
const dbmFallbackTimeout = 30 * time.Second

// metadataGroup collapses concurrent DBM lookups for the same machine into one call.
//
// Probes now poll on a schedule, so a machine whose cache went stale produces one request per
// probe interval, and a fleet-wide sync lag makes every probe fall back at once. Without this,
// admin would forward that burst to DBM one request at a time.
var metadataGroup singleflight.Group

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

// loadProbeMetadata returns probe metadata for one machine, preferring admin's local cache and
// falling back to the DBM API.
//
// The cache is only used when every row for the IP is fresh. Serving a mix of fresh and stale
// rows would hand the probe a half-updated view of the machine — it would keep probing an
// instance that moved away, or miss one that arrived — and that is worse than the added latency
// of asking DBM. This is why the fallback re-reads the whole machine rather than the stale rows.
func loadProbeMetadata(
	ctx context.Context, db *hamysql.GormDB, bkCloudID int, ip string,
) ([]probeconfig.ProbeMetadataItem, error) {
	metadataCfg := Cfg.ProbeMetadata

	list, err := getMetadataFromDBHA(db, bkCloudID, ip, metadataCfg.TombstoneAge)
	if err != nil {
		return nil, err
	}

	reason := cacheFallbackReason(list, metadataCfg.CacheMaxAge, time.Now())
	if reason == "" {
		return convertFromDBHA(list), nil
	}

	logger.Info("probe metadata cache not usable, falling back to dbm, bk_cloud_id: %d, ip: %s, reason: %s",
		bkCloudID, ip, reason)
	observeMetadataFallback(reason)

	dmList, err := getMetadataFromDBM(ctx, bkCloudID, ip)
	if err != nil {
		return nil, err
	}
	if len(dmList) == 0 {
		return nil, nil
	}
	return convertFromDBM(dmList), nil
}

// cacheFallbackReason reports why the cached rows cannot answer the request, or an empty string
// when they can. A single expired row disqualifies the whole set, per the all-or-nothing rule
// described on loadProbeMetadata.
func cacheFallbackReason(list []*hamodel.DbmMetadata, maxAge time.Duration, now time.Time) string {
	if len(list) == 0 {
		return fallbackReasonMiss
	}

	oldestAllowed := now.Add(-maxAge)
	for _, m := range list {
		if m.UpdatedAt.Before(oldestAllowed) {
			return fallbackReasonStale
		}
	}

	return ""
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

// getMetadataFromDBHA queries t_dbm_metadata by bk_cloud_id and ip, ignoring rows older than
// tombstoneAge.
//
// The filter matters because metadata sync only upserts, it never deletes: rows for instances
// that were decommissioned stay in the table forever. Without the cut-off, one such row would
// be permanently stale and would push every request for that IP to the DBM API, turning the
// cache off for that machine for good.
func getMetadataFromDBHA(
	db *hamysql.GormDB, bkCloudID int, ip string, tombstoneAge time.Duration,
) ([]*hamodel.DbmMetadata, error) {
	var list []*hamodel.DbmMetadata
	query := db.DB().Model(&hamodel.DbmMetadata{}).
		Where(hamodel.DbmMetadataFieldBkCloudID+" = ?", bkCloudID).
		Where(hamodel.DbmMetadataFieldListenIP+" = ?", ip)

	if tombstoneAge > 0 {
		query = query.Where(hamodel.DbmMetadataFieldUpdatedAt+" >= ?", time.Now().Add(-tombstoneAge))
	}

	err := query.Find(&list).Error

	if err != nil {
		if err == gorm.ErrRecordNotFound {
			return nil, nil
		}
		return nil, gerrors.NewE(gerrors.MysqlFailure, err)
	}
	return list, nil
}

// observeMetadataFallback records a cache fallback. Metric failures are logged rather than
// propagated: an unusable counter must not turn a serviceable config request into an error.
func observeMetadataFallback(reason string) {
	if apm.ProbeMetadataFallbackTotal == nil {
		return
	}
	if err := apm.ProbeMetadataFallbackTotal.IncWithLabels(
		map[string]string{apm.MetricLabelReason: reason},
	); err != nil {
		logger.Warn("record probe metadata fallback metric failed, errmsg: %s", err)
	}
}

// getMetadataFromDBM calls DBM metadata API (admin config DbmApis name=metadata).
//
// Concurrent calls for the same (bk_cloud_id, ip) share one round-trip. The returned slice is
// therefore shared between callers and must be treated as read-only; convertFromDBM only reads
// from it.
func getMetadataFromDBM(ctx context.Context, bkCloudID int, ip string) ([]*dbm.DbInstMetadata, error) {
	key := fmt.Sprintf("%d/%s", bkCloudID, ip)
	result, err, _ := metadataGroup.Do(key, func() (any, error) {
		return fetchMetadataFromDBM(ctx, bkCloudID, ip)
	})
	if err != nil {
		return nil, err
	}

	list, _ := result.([]*dbm.DbInstMetadata)
	return list, nil
}

func fetchMetadataFromDBM(ctx context.Context, bkCloudID int, ip string) ([]*dbm.DbInstMetadata, error) {
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

	// A configured timeout of zero means "no timeout" to http.Client, which is exactly the case
	// singleflight cannot survive, so fall back to a bounded deadline.
	timeout := api.Timeout
	if timeout <= 0 {
		timeout = dbmFallbackTimeout
	}
	// Detach from the first caller's cancellation. singleflight runs this function once and
	// every waiter shares the result: if the leader's context is already done, using it here
	// would fail the whole group, including callers that still have time left.
	reqCtx, cancel := context.WithTimeout(context.WithoutCancel(ctx), timeout)
	defer cancel()

	// POST to admin-configured DBM metadata API
	// Client.RequestMetadata uses config.Cfg.Workflow - we cannot use it from admin.
	// So we do HTTP POST here with admin's api.Api and api.Token (already in req).
	code, resp, err := postJSON(reqCtx, api.Api, data, timeout)
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

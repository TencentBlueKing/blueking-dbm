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

package workflow

import (
	"context"
	"fmt"
	"strings"
	"time"

	"dbm-services/common/dbha-v2/internal/analysis/config"
	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/storage"
	"dbm-services/common/dbha-v2/internal/analysis/switcher"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/snapshotlogger"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
)

type whitelistCluster struct {
	BkBizID   int
	BkCloudID int
	ClusterID int
}

func (c whitelistCluster) String() string {
	return fmt.Sprintf("%d:%d:%d", c.BkBizID, c.BkCloudID, c.ClusterID)
}

// queryBlackWhiteListFromDbhaV1 queries black white list from dbha-v1.
func (s *Synchronizer) queryBlackWhiteListFromDbhaV1(ctx context.Context, bkBizId int, bkCloudId int) ([]*dbm.Dbhav1BlackWhiteListItem, error) {
	if s.cli == nil {
		return nil, gerrors.Newf(gerrors.Failure, "dbm client is not initialized")
	}

	var lastErr error
	for attempt := 1; attempt <= blackWhiteListQueryMaxAttempts; attempt++ {
		items, err := s.cli.GetBlackWhiteListFromDbhaV1(ctx, bkCloudId, bkBizId)
		if err == nil {
			return items, nil
		}

		lastErr = err
		if attempt >= blackWhiteListQueryMaxAttempts {
			logger.Warn(
				"failed to query black white list from dbha-v1 after %d attempts, bk_biz_id: %d, bk_cloud_id: %d, errmsg: %s",
				blackWhiteListQueryMaxAttempts, bkBizId, bkCloudId, err,
			)
			continue
		}

		logger.Warn(
			"failed to query black white list from dbha-v1, will retry after %s, bk_biz_id: %d, bk_cloud_id: %d, errmsg: %s",
			blackWhiteListQueryRetryInterval, bkBizId, bkCloudId, err,
		)

		select {
		case <-ctx.Done():
			return nil, gerrors.Newf(gerrors.Failure,
				"query black white list from dbha-v1 cancelled during retry, bk_biz_id: %d, bk_cloud_id: %d, errmsg: %s",
				bkBizId, bkCloudId, ctx.Err())
		case <-time.After(blackWhiteListQueryRetryInterval):
		}
	}

	return nil, lastErr
}

// queryWhitelistClusters queries whitelist clusters from dbha-v1.
func (w *Workflow) queryWhitelistClusters(
	ctx context.Context, bizID int, bizMeta *BusinessMetadata,
) (map[string]struct{}, error) {
	cloudSet := make(map[int]struct{}, len(bizMeta.MetaInsts))
	for _, meta := range bizMeta.MetaInsts {
		cloudSet[meta.BkCloudID] = struct{}{}
	}

	whitelistSet := make(map[string]struct{})
	for cloudID := range cloudSet {
		items, err := w.dbmSync.queryBlackWhiteListFromDbhaV1(ctx, bizID, cloudID)
		if err != nil {
			return nil, err
		}

		for _, item := range items {
			key := whitelistCluster{
				BkBizID: bizID, BkCloudID: cloudID, ClusterID: item.ClusterID,
			}.String()
			whitelistSet[key] = struct{}{}
		}
	}
	return whitelistSet, nil
}

// filterByWhitelistForScan filters business metadata before probe scan,
// keeping only instances whose clusters are on the whitelist.
// Whitelist query failure skips the entire business scan.
func (w *Workflow) filterByWhitelistForScan(ctx context.Context, bizID int, bizMeta *BusinessMetadata) error {
	if !config.Cfg.Workflow.EnableWhiteList {
		logger.Warn("whitelist is disabled, skip filtering instances for scan, bizId: %d", bizID)
		return nil
	}
	if len(bizMeta.MetaInsts) == 0 {
		return nil
	}

	whitelistSet, err := w.queryWhitelistClusters(ctx, bizID, bizMeta)
	if err != nil {
		msg := fmt.Sprintf(
			"business scan skipped because whitelist query failed, bkBizId: %d, instanceCount: %d, errmsg: %s",
			bizID, len(bizMeta.MetaInsts), err,
		)
		logger.Warn("%s", msg)

		*bizMeta = BusinessMetadata{}
		return gerrors.Newf(gerrors.InternalServerFailure, "%s", msg)
	}

	filteredConds := make([]*storage.DbInstance, 0, len(bizMeta.Conds))
	filteredMetaInsts := make(map[string]*hamodel.DbmMetadata, len(bizMeta.MetaInsts))
	totalCount := len(bizMeta.MetaInsts)
	skippedCount := 0
	skippedClusters := make(map[string]struct{})

	for key, meta := range bizMeta.MetaInsts {
		clusterKey := whitelistCluster{
			BkBizID: meta.BkBizID, BkCloudID: meta.BkCloudID, ClusterID: meta.ClusterID,
		}.String()
		if _, whitelisted := whitelistSet[clusterKey]; !whitelisted {
			skippedCount++
			skippedClusters[meta.Cluster] = struct{}{}
			continue
		}

		filteredMetaInsts[key] = meta
		filteredConds = append(filteredConds, &storage.DbInstance{
			BkCloudID: meta.BkCloudID,
			IP:        meta.IP,
			Port:      meta.Port,
		})
	}

	if skippedCount > 0 {
		clusterNames := make([]string, 0, len(skippedClusters))
		for name := range skippedClusters {
			clusterNames = append(clusterNames, name)
		}
		logger.Info(
			"filtered non-whitelisted instances for scan, bkBizId: %d, total: %d, kept: %d, skipped: %d, filteredClusters: [%s]",
			bizID, totalCount, len(filteredMetaInsts), skippedCount, strings.Join(clusterNames, ", "),
		)
	}

	*bizMeta = BusinessMetadata{
		MetaInsts: filteredMetaInsts,
		Conds:     filteredConds,
	}
	return nil
}

// filterByWhitelistForSwitch filters switch requests by whitelist:
// whitelisted instances proceed to switching, others are removed and notified only.
func (w *Workflow) filterByWhitelistForSwitch(ctx context.Context, snapshotLoggers []snapshotlogger.SnapshotLogger,
	group *FailureGroup, req *switcher.Request, strategies []*hamodel.DbSwitchingStrategy) error {
	if !config.Cfg.Workflow.EnableWhiteList {
		logger.Warn("whitelist is disabled, skip filtering whitelisted instances")
		return nil
	}
	if !config.Cfg.Workflow.EnableSwitching {
		logger.Warn("switching operation is disabled, skip filtering whitelisted instances")
		return nil
	}

	if len(group.Instances) == 0 {
		return nil
	}

	bkBizID := group.BkBizID

	whiteList, err := w.dbmSync.queryBlackWhiteListFromDbhaV1(ctx, bkBizID, group.BkCloudID)
	if err != nil {
		instanceAddrs := make([]string, 0, len(req.MySqlInstData))
		for _, meta := range req.MySqlInstData {
			instanceAddrs = append(instanceAddrs, instanceKey(meta.BkCloudID, meta.IP, meta.Port))
		}

		msg := fmt.Sprintf(
			"fault instances filtered because whitelist query failed, instances: [%s], bkBizId: %d, bkCloudId: %d, errmsg: %s",
			strings.Join(instanceAddrs, ", "), bkBizID, group.BkCloudID, err,
		)
		logger.Warn("%s", msg)
		w.alarm.TriggerWithBizId(bkBizID, msg)

		req.MySqlInstData = make([]*dbm.DbInstMetadata, 0)
		return gerrors.Newf(gerrors.InternalServerFailure, "%s", msg)
	}

	whitelistSet := make(map[string]struct{}, len(whiteList))
	for _, item := range whiteList {
		key := whitelistCluster{
			BkBizID: bkBizID, BkCloudID: group.BkCloudID, ClusterID: item.ClusterID,
		}.String()
		whitelistSet[key] = struct{}{}
	}

	whitelistedMetas := make([]*dbm.DbInstMetadata, 0)
	remaining := make([]*dbm.DbInstMetadata, 0)

	for _, meta := range req.MySqlInstData {
		clusterKey := whitelistCluster{
			BkBizID: meta.BkBizID, BkCloudID: meta.BkCloudID, ClusterID: meta.ClusterID,
		}.String()
		if _, exists := whitelistSet[clusterKey]; exists {
			whitelistedMetas = append(whitelistedMetas, meta)
			continue
		}
		logger.Info("instance is not in the whitelist, notify only, clusterId: %d, clusterName: %s, ip: %s, port: %d",
			meta.ClusterID, meta.Cluster, meta.IP, meta.Port)
		remaining = append(remaining, meta)
	}

	// only whitelisted instances proceed to switching
	req.MySqlInstData = whitelistedMetas

	if len(remaining) == 0 {
		return nil
	}

	// write a notify snapshot for the non-whitelisted instances before raising the alarm,
	// so that they still leave a traceable record even when no switch is executed.
	w.reportWhitelistNotifySnapshot(snapshotLoggers, group, remaining, req.SwitchID, strategies)

	// send a notification alarm for non-whitelisted instances
	instanceInfos := make([]string, 0, len(remaining))
	for _, meta := range remaining {
		instanceInfos = append(instanceInfos,
			fmt.Sprintf("%s(%d):%s:%d", meta.Cluster, meta.ClusterID, meta.IP, meta.Port))
	}
	log := fmt.Sprintf(
		"found %d not whitelisted instance(s), execute notification only, bkBizId: %d, bkCloudId: %d, dbType: %s, instances: [%s]",
		len(remaining), bkBizID, group.BkCloudID, group.DbType, strings.Join(instanceInfos, ", "))
	logger.Info("%s", log)
	w.alarm.TriggerWithBizId(bkBizID, log)
	return nil
}

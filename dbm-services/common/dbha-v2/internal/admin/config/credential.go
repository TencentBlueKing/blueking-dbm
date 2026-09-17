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
	"context"

	"dbm-services/common/dbha-v2/pkg/dbcred"
	"dbm-services/common/dbha-v2/pkg/dbtype"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/probeconfig"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// credGroup groups the items of one DbType together with the resolver that
// resolves their credentials and the indexes back into the original slice.
type credGroup struct {
	resolver dbcred.Resolver
	idxs     []int          // indexes into items
	batch    []*dbcred.Item // one-to-one with idxs
}

// fillInstanceCredentials resolves per-instance credentials for one machine and
// writes them back into items. It groups by DbType, looks up each registered
// resolver, and lets it fill the batch. A DB type without a registered resolver
// keeps its block-level static credentials silently.
func fillInstanceCredentials(ctx context.Context, bkCloudID int,
	items []probeconfig.ProbeMetadataItem) {

	groups := map[haprobe.DbType]*credGroup{}

	for i := range items {
		dt := dbtype.DbTypeOf(haprobe.DbmMetadataClusterType(items[i].ClusterType))
		if dt == haprobe.DbTypeNone {
			continue
		}
		g, ok := groups[dt]
		if !ok {
			p, registered := dbcred.Lookup(dt)
			if !registered {
				// No dynamic credential resolver for this DB: keep the
				// block-level static credentials, silently.
				continue
			}
			g = &credGroup{resolver: p}
			groups[dt] = g
		}
		g.idxs = append(g.idxs, i)
		g.batch = append(g.batch, &dbcred.Item{Instance: toInstance(items[i])})
	}

	for dt, g := range groups {
		if err := g.resolver.Fill(ctx, bkCloudID, g.batch); err != nil {
			logger.Warnf("fill %s credential failed, bk_cloud_id: %d, errmsg: %s",
				dt, bkCloudID, err)
			// Do not return: part of the instances may already be filled.
		}
		for k, it := range g.batch {
			items[g.idxs[k]].User = it.User
			items[g.idxs[k]].Password = it.Password
			if it.Password == "" {
				logger.Warnf("%s credential unresolved, keep empty password, "+
					"cluster_id: %d, ip: %s, port: %d",
					dt, items[g.idxs[k]].ClusterID, items[g.idxs[k]].IP, items[g.idxs[k]].Port)
			}
		}
	}
}

// toInstance converts a probe metadata item into the generic credential
// instance shape consumed by dbcred resolvers.
func toInstance(m probeconfig.ProbeMetadataItem) dbcred.Instance {
	return dbcred.Instance{
		ClusterID:    m.ClusterID,
		ClusterType:  haprobe.DbmMetadataClusterType(m.ClusterType),
		MachineType:  haprobe.DbmMetadataMachineType(m.MachineType),
		InstanceRole: haprobe.DbmMetadataInstanceRole(m.InstanceRole),
		AccessLayer:  haprobe.DbmMetadataAccessLayerType(m.AccessLayer),
		IP:           m.IP,
		Port:         m.Port,
	}
}

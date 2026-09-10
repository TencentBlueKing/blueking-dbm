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

// Package harvest implements the Redis harvester plugin that collects status from
// Redis-family backends (RedisCluster, TendisCache, TendisSSD, TendisPlus, Predixy, Twemproxy).
package harvest

import (
	"context"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/internal/probe/harvester/base"
	"dbm-services/common/dbha-v2/internal/probe/harvester/plugin"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/machine"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

const (
	Name = "redis"
)

// Redis redis harvester
type Redis struct {
	// NOTE: Must include UnimplementedMethod
	plugin.UnimplementedMethod

	bkCloudID int
	machineID string
	serviceID string
	wg        sync.WaitGroup
	cfg       *config.RawHarvesterConfig
	// key: the redis endpoint
	collectors map[string]*collector
}

// NewRedis constructor
func NewRedis(cfg *config.RawHarvesterConfig) (*Redis, error) {
	r := &Redis{
		cfg: cfg,
	}

	return r, nil
}

// Name returns the name of the plugin.
func (r *Redis) Name() (string, error) {
	return Name, nil
}

// Close closes the plugin.
func (r *Redis) Close() error {
	logger.Info("Redis harvester plugin closed successfully")
	return nil
}

// Harvest harvests data from the target instance.
func (r *Redis) Harvest(ctx context.Context, machineID, serviceID string) (<-chan *plugin.HarvestData, error) {
	logger.Info("start redis harvest, interval time is: %v", r.cfg.Interval)

	r.machineID = machineID
	r.serviceID = serviceID

	dataC := make(chan *plugin.HarvestData, 1024)

	// Load all collectors.
	r.loadCollectors()

	r.wg.Add(1)
	go func(ctx context.Context) {
		defer r.wg.Done()
		defer close(dataC)

		collectRound := func() {
			wg := &sync.WaitGroup{}
			r.beginCollecting(ctx, wg, dataC)
			wg.Wait()
		}

		if ctx.Err() != nil {
			logger.Info("exit harvester(redis)")
			return
		}
		collectRound()

		timer := time.NewTimer(r.cfg.Interval)
		defer timer.Stop()

		for {
			select {
			case <-ctx.Done():
				logger.Info("exit harvester(redis)")
				return

			case <-timer.C:
				collectRound()
				timer.Reset(r.cfg.Interval)
			}
		}
	}(ctx)

	return dataC, nil
}

func (r *Redis) makeCollector(epoint config.DbEndpointConfig, eport int) *collector {
	c := &collector{}

	c.accessLayer = epoint.AccessLayer
	c.machineType = epoint.MachineType
	c.clusterType = epoint.ClusterType
	c.instanceRole = epoint.InstanceRole

	c.user = r.cfg.User
	c.password = r.cfg.Password
	c.timeout = r.cfg.Timeout

	c.endpoint = &hanet.Endpoint{}
	c.endpoint.Proto = epoint.Proto
	c.endpoint.Host = epoint.Ip
	c.endpoint.Port = eport

	return c
}

func (r *Redis) loadStorageCollector(epoint config.DbEndpointConfig) {
	for _, ports := range epoint.Ports {
		eports, err := base.ParsePorts(ports)
		if err != nil {
			continue
		}

		for _, eport := range eports {
			c := r.makeCollector(epoint, eport)
			r.collectors[c.endpoint.String()] = c
		}
	}
}

func (r *Redis) loadCollectors() {
	if r.collectors == nil {
		r.collectors = map[string]*collector{}
	}

	for _, epoint := range r.cfg.Endpoints {
		if len(epoint.Ports) != 0 {
			r.loadStorageCollector(epoint)
		}
	}
}

func (r *Redis) collecting(ctx context.Context, c *collector, dataC chan<- *plugin.HarvestData) {
	status := &haprobe.RedisStatus{}

	data := &plugin.HarvestData{
		HarvestBaseData: haprobe.HarvestBaseData{
			HarvestType:  haprobe.HarvestTypeDefault,
			SequenceID:   machine.NewSequenceID(),
			MessageID:    machine.NewMessageID(),
			MachineID:    r.machineID,
			ServiceID:    r.serviceID,
			BkCloudID:    r.bkCloudID,
			DbIp:         c.endpoint.Host,
			DbPort:       c.endpoint.Port,
			AccessLayer:  c.accessLayer,
			ClusterType:  c.clusterType,
			MachineType:  c.machineType,
			InstanceRole: c.instanceRole,
		},
	}

	defer func() {
		c.close()

		data.Value = status
		data.ReportTimestamp = uint64(time.Now().Unix())

		dataC <- data
	}()

	if hostStatus, err := c.obtainHostStatus(); err != nil {
		logger.Warn("failed to obtain the host status, errmsg: %s", err)
	} else {
		data.Host = hostStatus
	}

	// Skip the storage layer of clusters that only probe their proxy layer.
	if c.shouldSkipStorage() {
		logger.Debug("skip storage detection, cluster: %s, machine: %s", c.clusterType, c.machineType)
		return
	}

	dbEvent, err := c.open(ctx)
	if err != nil {
		dbEvent.BkCloudID = r.bkCloudID
		data.Events = []*haprobe.DbEvent{dbEvent}
		logger.Error("failed to open the collector for the db: %s, errmsg: %s", c.endpoint, err)
		return
	}

	r.populateOpenedDbStatus(ctx, c, status, data)
}

func (r *Redis) populateOpenedDbStatus(ctx context.Context, c *collector, status *haprobe.RedisStatus, data *plugin.HarvestData) {
	switch {
	case c.isProxyInstance():
		r.populateReadCheck(ctx, c, status, data)
	case c.isStorageInstance():
		r.populateStorage(ctx, c, status, data)
	default:
		logger.Warn("unsupported redis instance, skip detection, cluster: %s, machine: %s, access_layer: %s",
			c.clusterType, c.machineType, c.accessLayer)
	}
}

// populateReadCheck probes proxy instances (twemproxy / predixy) with the
// TYPE twemproxy_mon read-only command.
func (r *Redis) populateReadCheck(ctx context.Context, c *collector, status *haprobe.RedisStatus, data *plugin.HarvestData) {
	readCheck := &haprobe.RedisReadCheckStatus{}
	if err := c.obtainReadCheck(ctx); err != nil {
		if event := c.classifyCommandError(err); event != nil {
			event.BkCloudID = r.bkCloudID
			data.Events = []*haprobe.DbEvent{event}
			return
		}
		readCheck.State = haprobe.RedisStateFailed
		readCheck.FailureReason = err.Error()
		status.ReadCheckStatus = readCheck
		return
	}
	readCheck.State = haprobe.RedisStateOk
	status.ReadCheckStatus = readCheck
}

// populateStorage probes storage instances (tendiscache / tendisssd / tendisplus)
// with INFO Replication to read the role, then runs the SELECT + SET write probe
// on masters.
func (r *Redis) populateStorage(ctx context.Context, c *collector, status *haprobe.RedisStatus, data *plugin.HarvestData) {
	replication := &haprobe.RedisReplicationStatus{}
	replicationInfo, err := c.obtainReplicationInfo(ctx)
	if err != nil {
		if event := c.classifyCommandError(err); event != nil {
			event.BkCloudID = r.bkCloudID
			data.Events = []*haprobe.DbEvent{event}
			return
		}
		replication.State = haprobe.RedisStateFailed
		replication.FailureReason = err.Error()
		status.ReplicationStatus = replication
		return
	}

	role, ok := replicationInfo["role"]
	if !ok {
		replication.State = haprobe.RedisStateFailed
		replication.FailureReason = "response un-find role"
		status.ReplicationStatus = replication
		return
	}

	replication.State = haprobe.RedisStateOk
	replication.Role = role
	status.ReplicationStatus = replication

	// Only masters run the write probe.
	if role != "master" {
		return
	}

	heartbeat := &haprobe.RedisHeartbeatStatus{}
	selectResult, setResult, err := c.obtainHeartbeat(ctx)
	heartbeat.SelectResult = selectResult
	heartbeat.SetResult = setResult
	if err != nil {
		if event := c.classifyCommandError(err); event != nil {
			event.BkCloudID = r.bkCloudID
			data.Events = []*haprobe.DbEvent{event}
			return
		}
		heartbeat.State = haprobe.RedisStateFailed
		heartbeat.FailureReason = err.Error()
		status.HeartbeatStatus = heartbeat
		return
	}
	heartbeat.State = haprobe.RedisStateOk
	status.HeartbeatStatus = heartbeat
}

func (r *Redis) beginCollecting(ctx context.Context, wg *sync.WaitGroup, dataC chan<- *plugin.HarvestData) {
	for _, c := range r.collectors {
		wg.Add(1)

		go func(t *collector) {
			defer wg.Done()

			r.collecting(ctx, t, dataC)
		}(c)
	}
}

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

package mysql

import (
	"context"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/internal/probe/harvester/plugin"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/machine"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

const (
	Name    = "mysql"
	Version = "v1.0.0"

	MySqlConfigFileType  = "ini"
	MySqlBindPort        = "mysql.port"
	MySqlBindAddress     = "mysqld.bind-address"
	MySqlConnectionProto = "tcp"
)

var (
	ErrInvalidMySqlIp   = gerrors.Newf(gerrors.InvalidParameter, "invalid MySQL ip")
	ErrInvalidMySqlPort = gerrors.Newf(gerrors.InvalidParameter, "invalid MySQL port")
	ErrReadMySqlConfig  = gerrors.Newf(gerrors.Failure, "failed to read MySQL config file")
)

// MySql mysql harvester
type MySql struct {
	// NOTE: Must include UnimplementedMethod
	plugin.UnimplementedMethod

	machineID string
	serviceID string
	wg        sync.WaitGroup
	cfg       *config.MySqlHarvesterConfig
	// key: the mysql endpoint
	collectors map[string]*collector
}

// NewMySql constructor
func NewMySql(cfg *config.MySqlHarvesterConfig) (*MySql, error) {
	msql := &MySql{
		cfg: cfg,
	}

	return msql, nil
}

// Name returns the name of the plugin.
func (m *MySql) Name() (string, error) {
	return Name, nil
}

// Version returns the version of the plugin.
func (m *MySql) Version() (string, error) {
	return Version, nil
}

// Close closes the plugin.
func (m *MySql) Close() error {
	logger.Info("MySQL harvester plugin closed successfully")
	return nil
}

// Harvest harvests data from the target instance.
func (m *MySql) Harvest(ctx context.Context, machineID, serviceID string) (<-chan *plugin.HarvestData, error) {
	logger.Info("start mysql harvest, interval time is: %v", m.cfg.Interval)

	m.machineID = machineID
	m.serviceID = serviceID

	dataC := make(chan *plugin.HarvestData, 1024)

	// Load all collectors.
	m.loadCollectors()

	m.wg.Add(1)
	go func(ctx context.Context) {
		defer m.wg.Done()
		defer close(dataC)

		timer := time.NewTimer(m.cfg.Interval)
		defer timer.Stop()

		for {
			select {
			case <-ctx.Done():
				logger.Info("exit harvester(mysql)")
				return

			case <-timer.C:
				wg := &sync.WaitGroup{}

				// Start the collectors.
				m.beginCollecting(wg, dataC)

				// Wait for the collectors to stop.
				wg.Wait()

				timer.Reset(m.cfg.Interval)
			}
		}
	}(ctx)

	return dataC, nil
}

func (m *MySql) makeCollector(epoint config.DbEndpointConfig, eport int) *collector {
	c := &collector{}

	c.accessLayer = epoint.AccessLayer
	c.machineType = epoint.MachineType
	c.clusterType = epoint.ClusterType

	c.user = m.cfg.User
	c.password = m.cfg.Password

	c.endpoint = &hanet.Endpoint{}
	c.endpoint.Proto = epoint.Proto
	c.endpoint.Host = epoint.Ip
	c.endpoint.Port = eport

	return c
}

func (m *MySql) loadAdminCollectors(epoint config.DbEndpointConfig) {
	for _, ports := range epoint.AdminPorts {
		eports, err := parsePorts(ports)
		if err != nil {
			continue
		}

		for _, eport := range eports {
			c := m.makeCollector(epoint, eport)
			m.collectors[c.endpoint.String()] = c
		}

	}
}

func (m *MySql) loadStorageCollector(epoint config.DbEndpointConfig) {
	for _, ports := range epoint.Ports {

		eports, err := parsePorts(ports)
		if err != nil {
			continue
		}

		for _, eport := range eports {
			c := m.makeCollector(epoint, eport)
			m.collectors[c.endpoint.String()] = c
		}
	}

}

func (m *MySql) loadCollectors() {
	if m.collectors == nil {
		m.collectors = map[string]*collector{}
	}

	for _, epoint := range m.cfg.Endpoints {

		if len(epoint.AdminPorts) != 0 {
			m.loadAdminCollectors(epoint)
		}

		if len(epoint.Ports) != 0 {
			m.loadStorageCollector(epoint)
		}
	}
}

func (m *MySql) collecting(c *collector, dataC chan<- *plugin.HarvestData) {
	metrics := &haprobe.MySqlMetric{
		SequenceID:      machine.NewSequenceID(),
		MachineID:       m.machineID,
		MessageID:       machine.NewMessageID(),
		ServiceID:       m.serviceID,
		ReportTimestamp: uint64(time.Now().Unix()),
		Status:          &haprobe.MySqlStatus{},
	}

	defer func() {
		c.close()

		dataC <- &plugin.HarvestData{
			AccessLayer: c.accessLayer,
			ClusterType: c.clusterType,
			MachineType: c.machineType,
			Value:       metrics,
		}
	}()

	if hostStatus, err := c.obtainHostStatus(); err != nil {
		logger.Warn("failed to obtain the host status, errmsg: %s", err)
	} else {
		metrics.Host = hostStatus
	}

	dbEvent, err := c.open()
	if err != nil {
		metrics.Event = dbEvent
		logger.Error("failed to open the collector for the db: %s", c.endpoint)
		return
	}

	if c.isTendbHaProxy() {
		dbStatus, err := c.obtainTendbHaProxyStatus()
		if err != nil {
			logger.Warn("failed to obtain the MySQL(TendbHaProxy) status, errmsg: %s", err)
			return
		}

		metrics.Status.ProxyStatus = dbStatus
		return
	}

	if c.isTendbClusterProxy() {
		dbStatus, err := c.obtainTendbClusterProxyStatus()
		if err != nil {
			logger.Warn("failed to obtain the MySQL(TendbClusterProxy) status, errmsg: %s", err)
			return
		}

		metrics.Status.SpiderCtlStatus = dbStatus
		return
	}

	// Get the global status.
	// TendbHa and TendbCluster both support the global status.
	if dbStatus, err := c.obtainGlobalStatus(); err != nil {
		logger.Warn("failed to obtain the MySQL status, errmsg: %s", err)
	} else {
		metrics.Status.GlobalStatus = dbStatus
	}
}

func (m *MySql) beginCollecting(wg *sync.WaitGroup, dataC chan<- *plugin.HarvestData) {
	for _, c := range m.collectors {
		wg.Add(1)

		go func(t *collector) {
			defer wg.Done()

			m.collecting(t, dataC)
		}(c)
	}
}

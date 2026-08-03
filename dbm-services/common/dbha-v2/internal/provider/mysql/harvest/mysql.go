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

// Package mysql implements the MySQL harvester plugin used to collect status from
// MySQL-family backends (TendbHA mysql storage, TendbHA mysql-proxy admin ports,
// TendbCluster spider / spider-ctl). The plugin is driven by config.RawHarvesterConfig:
// admin owns the credentials and Interval / Timeout, probe routes endpoints into either
// the regular mysql instance or the dedicated mysqlProxyAdmin instance.
package harvest

import (
	"context"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/internal/probe/harvester/base"
	"dbm-services/common/dbha-v2/internal/probe/harvester/plugin"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/machine"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

const (
	Name                = "mysql"
	NameMySqlProxyAdmin = "mysqlProxyAdmin"

	MySqlConfigFileType  = "ini"
	MySqlBindPort        = "mysql.port"
	MySqlBindAddress     = "mysqld.bind-address"
	MySqlConnectionProto = "tcp"

	mysqlCollectStateOk     = "ok"
	mysqlCollectStateFailed = "failed"
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

	bkCloudID int
	agentID   string
	machineID string
	serviceID string
	name      string
	wg        sync.WaitGroup
	cfg       *config.RawHarvesterConfig
	// key: the mysql endpoint
	collectors map[string]*collector
}

// NewMySql constructs a MySql harvester named Name; used for regular mysql storage / spider endpoints.
func NewMySql(cfg *config.RawHarvesterConfig) (*MySql, error) {
	return newMySql(cfg, Name)
}

// NewMySqlProxyAdmin constructs a MySql harvester named NameMySqlProxyAdmin; used for TendbHA
// mysql-proxy admin ports so logs can distinguish it from the regular mysql plugin instance.
func NewMySqlProxyAdmin(cfg *config.RawHarvesterConfig) (*MySql, error) {
	return newMySql(cfg, NameMySqlProxyAdmin)
}

func newMySql(cfg *config.RawHarvesterConfig, name string) (*MySql, error) {
	if name == "" {
		name = Name
	}
	return &MySql{
		cfg:  cfg,
		name: name,
	}, nil
}

// Name returns the plugin instance name (Name or NameMySqlProxyAdmin).
func (m *MySql) Name() (string, error) {
	if m.name == "" {
		return Name, nil
	}
	return m.name, nil
}

// Close closes the plugin.
func (m *MySql) Close() error {
	logger.Info("harvester plugin closed, name: %s", m.name)
	return nil
}

// Harvest harvests data from the target instance.
func (m *MySql) Harvest(ctx context.Context, machineID, serviceID string) (<-chan *plugin.HarvestData, error) {
	logger.Info("start mysql harvest, name: %s, interval: %s", m.name, m.cfg.Interval)

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
				logger.Info("exit harvester, name: %s", m.name)
				return

			case <-timer.C:
				wg := &sync.WaitGroup{}

				m.beginCollecting(wg, dataC)

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
	c.instanceRole = epoint.InstanceRole

	c.user = m.cfg.User
	c.password = m.cfg.Password
	c.timeout = m.cfg.Timeout

	c.endpoint = &hanet.Endpoint{}
	c.endpoint.Proto = epoint.Proto
	c.endpoint.Host = epoint.Ip
	c.endpoint.Port = eport

	return c
}

func (m *MySql) loadAdminCollectors(epoint config.DbEndpointConfig) {
	for _, ports := range epoint.AdminPorts {
		eports, err := base.ParsePorts(ports)
		if err != nil {
			continue
		}

		for _, eport := range eports {
			c := m.makeCollector(epoint, eport)
			c.isAdminNode = true
			m.collectors[c.endpoint.String()] = c
		}

	}
}

func (m *MySql) loadStorageCollector(epoint config.DbEndpointConfig) {
	for _, ports := range epoint.Ports {

		eports, err := base.ParsePorts(ports)
		if err != nil {
			continue
		}

		for _, eport := range eports {
			c := m.makeCollector(epoint, eport)
			c.isAdminNode = false
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

// collectProxyServicePort handles a TendbHA mysql-proxy data (service) port with
// a lightweight reachability probe (SELECT 1) followed by a write-heartbeat path.
// It deliberately skips obtainGlobalStatus / obtainHostStatus / obtainSlaveStatus
// (all forward to the backend master and only duplicate the direct backend probe).
// It assumes c.db is already opened by the caller.
func (m *MySql) collectProxyServicePort(c *collector, status *haprobe.MySqlStatus) {

	servicePortStatus, err := c.obtainTendbHaProxyServicePortStatus()
	status.ProxyServicePortStatus = servicePortStatus
	if err != nil {
		logger.Warn(
			"failed to probe tendbha proxy data port, ip: %s, port: %d, errmsg: %s",
			c.endpoint.Host, c.endpoint.Port, err,
		)
	}

	heartbeatStatus, err := c.obtainHeartbeatStatus(false)
	status.HeartbeatStatus = heartbeatStatus
	if err != nil {
		logger.Warn(
			"failed to write heartbeat via tendbha proxy data port, ip: %s, port: %d, errmsg: %s",
			c.endpoint.Host, c.endpoint.Port, err,
		)
	}
}

func collectStatusResult(err error) (string, string) {
	if err != nil {
		return mysqlCollectStateFailed, hamysql.SanitizeConnectionError(err)
	}
	return mysqlCollectStateOk, ""
}

func (m *MySql) collectProxyAdminPort(c *collector, status *haprobe.MySqlStatus) {
	dbStatus, err := c.obtainTendbHaProxyStatus()
	if dbStatus == nil {
		dbStatus = &haprobe.MySqlProxyStatus{}
	}
	dbStatus.State, dbStatus.FailureReason = collectStatusResult(err)
	status.ProxyStatus = dbStatus
	if err != nil {
		logger.Warn("failed to obtain the MySQL(TendbHaProxy) status, errmsg: %s", err)
	}
}

func (m *MySql) collectSpiderCtlStatus(c *collector, status *haprobe.MySqlStatus) {
	dbStatus, err := c.obtainTendbClusterProxyStatus()
	if dbStatus == nil {
		dbStatus = &haprobe.MySqlSpiderCtlStatus{}
	}
	dbStatus.State, dbStatus.FailureReason = collectStatusResult(err)
	status.SpiderCtlStatus = dbStatus
	if err != nil {
		logger.Warn("failed to obtain the MySQL(TendbClusterProxy) status, errmsg: %s", err)
	}
}

func (m *MySql) collecting(c *collector, dataC chan<- *plugin.HarvestData) {
	status := &haprobe.MySqlStatus{}

	data := &plugin.HarvestData{
		HarvestBaseData: haprobe.HarvestBaseData{
			SequenceID:  machine.NewSequenceID(),
			MessageID:   machine.NewMessageID(),
			MachineID:   m.machineID,
			ServiceID:   m.serviceID,
			BkCloudID:   m.bkCloudID,
			AgentID:     m.agentID,
			DbIp:        c.endpoint.Host,
			DbPort:      c.endpoint.Port,
			AccessLayer: c.accessLayer,
			ClusterType: c.clusterType,
			MachineType: c.machineType,
		},
	}

	defer func() {
		c.close()
		data.Value = status
		data.ReportTimestamp = uint64(time.Now().Unix())
		dataC <- data
	}()

	isProxyServicePort := c.isTendbHaProxy() && !c.isAdmin()

	if !isProxyServicePort {
		if hostStatus, err := c.obtainHostStatus(); err != nil {
			logger.Warn("failed to obtain the host status, errmsg: %s", err)
		} else {
			data.Host = hostStatus
		}
	}

	dbEvent, err := c.open()
	if err != nil {
		dbEvent.BkCloudID = m.bkCloudID
		data.Events = []*haprobe.DbEvent{dbEvent}
		logger.Error("failed to open the collector for the db: %s", c.endpoint)
		return
	}

	if isProxyServicePort {
		m.collectProxyServicePort(c, status)
		return
	}

	// Proxy admin port is not MySQL; special-case and return early.
	if c.isTendbHaProxy() && c.isAdmin() {
		m.collectProxyAdminPort(c, status)
		return
	}

	// disable session forwarding
	if err := c.disableSpiderSessionForwarding(); err != nil {
		logger.Warn("failed to disable spider session forwarding, errmsg: %s", err)
		return
	}

	// special case for tdbctl
	if c.isTendbClusterProxy() && c.isAdmin() {
		m.collectSpiderCtlStatus(c, status)
	}

	c.collectCommonStatus(status)
}

// collectCommonStatus collects the common status for all mysql instances.
func (c *collector) collectCommonStatus(status *haprobe.MySqlStatus) {
	dbStatus, err := c.obtainGlobalStatus()
	if dbStatus == nil {
		dbStatus = &haprobe.MySqlGlobalStatus{}
	}
	dbStatus.State, dbStatus.FailureReason = collectStatusResult(err)
	status.GlobalStatus = dbStatus
	if err != nil {
		logger.Warn("failed to obtain the MySQL status, errmsg: %s", err)
	}

	isSlave := c.isSlave()

	heartbeatStatus, err := c.obtainHeartbeatStatus(!isSlave)
	status.HeartbeatStatus = heartbeatStatus
	if err != nil {
		logger.Warn("failed to obtain the heartbeat status, errmsg: %s", err)
	}

	if isSlave {
		slaveStatus, err := c.obtainSlaveStatus()
		if slaveStatus == nil {
			slaveStatus = &haprobe.MySqlSlaveStatus{}
		}
		slaveStatus.State, slaveStatus.FailureReason = collectStatusResult(err)
		status.SlaveStatus = slaveStatus
		if err != nil {
			logger.Warn("failed to obtain the slave status, errmsg: %s", err)
		}
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

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

// Package harvest implements the MySQL harvester plugin used to collect status from
// MySQL-family backends (TendbHA mysql storage, TendbHA mysql-proxy admin ports,
// TendbCluster spider / spider-ctl). The plugin is driven by config.RawHarvesterConfig:
// admin owns the credentials and Interval / Timeout, probe routes endpoints into either
// the regular mysql instance or the dedicated mysqlProxyAdmin instance.
package harvest

import (
	"context"
	"errors"
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

	minCollectInterval       = 5 * time.Second
	minHeartbeatInterval     = 1 * time.Second
	minReplDelayInterval     = 5 * time.Second
	defaultCollectInterval   = 20 * time.Second
	defaultHeartbeatInterval = 3 * time.Second
	defaultReplDelayInterval = 20 * time.Second
)

var (
	ErrInvalidMySqlIp   = gerrors.Newf(gerrors.InvalidParameter, "invalid MySQL ip")
	ErrInvalidMySqlPort = gerrors.Newf(gerrors.InvalidParameter, "invalid MySQL port")
	ErrReadMySqlConfig  = gerrors.Newf(gerrors.Failure, "failed to read MySQL config file")
)

// portSpec declares one port and its admin status.
type portSpec struct {
	port    int
	isAdmin bool
}

// fillStatusFunc fills the group's sub-field(s) of a MySqlStatus after the connection is open.
// Returns a DbEvent only when a real exception occurred; nil otherwise.
type fillStatusFunc func(c *collector, status *haprobe.MySqlStatus) *haprobe.DbEvent

// harvestGroup declares one mysql collection group.
type harvestGroup struct {
	// htype tags every HarvestData this group emits and drives receiver-side routing.
	htype haprobe.HarvestType
	// interval is the group's collection cadence.
	interval time.Duration
	// accept reports whether an endpoint belongs to this group.
	accept func(c *collector) bool
	// emit produces one HarvestData for a single collector.
	emit func(c *collector, dataC chan<- *plugin.HarvestData)
}

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
	// harvestGroups declares every harvest group (default / heartbeat / repldelay)
	harvestGroups []*harvestGroup
	// collectors keyed by harvest group
	collectors map[haprobe.HarvestType][]*collector
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

	// Declare groups, then load each group's collectors.
	m.harvestGroups = m.buildHarvestGroups()
	m.loadCollectors()

	// One scheduling loop per non-empty group, each on its own cadence.
	for _, g := range m.harvestGroups {
		if len(m.collectors[g.htype]) == 0 {
			logger.Info("skip empty harvest group, name: %s, group: %s", m.name, g.htype)
			continue
		}
		m.wg.Add(1)
		go m.runGroupLoop(ctx, g, dataC)
	}

	// Close dataC only after every group loop has exited.
	go func() {
		m.wg.Wait()
		close(dataC)
	}()

	return dataC, nil
}

// runGroupLoop drives one harvest group on its own timer, fanning out over the group's
// collectors every tick via beginCollecting.
func (m *MySql) runGroupLoop(ctx context.Context, g *harvestGroup, dataC chan<- *plugin.HarvestData) {
	defer m.wg.Done()

	timer := time.NewTimer(g.interval)
	defer timer.Stop()

	for {
		select {
		case <-ctx.Done():
			logger.Info("exit harvester, name: %s, group: %s", m.name, g.htype)
			return

		case <-timer.C:
			wg := &sync.WaitGroup{}

			m.beginCollecting(wg, dataC, g)

			wg.Wait()

			timer.Reset(g.interval)
		}
	}
}

func (m *MySql) makeCollector(epoint config.DbEndpointConfig, eport int, isAdmin bool) *collector {
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
	c.isAdminNode = isAdmin

	return c
}

// loadCollectors makes the collectors for all harvest groups.
func (m *MySql) loadCollectors() {
	m.collectors = map[haprobe.HarvestType][]*collector{}

	for _, g := range m.harvestGroups {
		// one group of same type collectors
		m.collectors[g.htype] = m.makeCollectorGroup(g)
	}
}

// parsePorts parses the ports from the endpoint config.
func (m *MySql) parsePorts(epoint config.DbEndpointConfig, isAdmin bool) []portSpec {
	portSpecs := []portSpec{}
	portStrList := epoint.Ports

	if isAdmin {
		portStrList = epoint.AdminPorts
	}

	for _, portStr := range portStrList {
		ports, err := base.ParsePorts(portStr)
		if err != nil {
			continue
		}

		for _, port := range ports {
			portSpecs = append(portSpecs, portSpec{port: port, isAdmin: isAdmin})
		}
	}

	return portSpecs
}

// makeCollectorGroup makes the collectors for the given harvest group.
func (m *MySql) makeCollectorGroup(hGroup *harvestGroup) []*collector {
	cs := []*collector{}

	for _, epoint := range m.cfg.Endpoints {
		portSpecs := []portSpec{}
		portSpecs = append(portSpecs, m.parsePorts(epoint, false)...)
		portSpecs = append(portSpecs, m.parsePorts(epoint, true)...)

		for _, onePortSpec := range portSpecs {
			c := m.makeCollector(epoint, onePortSpec.port, onePortSpec.isAdmin)

			if hGroup.accept(c) {
				cs = append(cs, c)
			}
		}
	}

	return cs
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

// newHarvestData builds a HarvestData envelope for one collector, tagged with the HarvestType.
func (m *MySql) newHarvestData(c *collector, htype haprobe.HarvestType) *plugin.HarvestData {
	return &plugin.HarvestData{
		HarvestBaseData: haprobe.HarvestBaseData{
			HarvestType:  htype,
			SequenceID:   machine.NewSequenceID(),
			MessageID:    machine.NewMessageID(),
			MachineID:    m.machineID,
			ServiceID:    m.serviceID,
			BkCloudID:    m.bkCloudID,
			AgentID:      m.agentID,
			DbIp:         c.endpoint.Host,
			DbPort:       c.endpoint.Port,
			AccessLayer:  c.accessLayer,
			ClusterType:  c.clusterType,
			MachineType:  c.machineType,
			InstanceRole: c.instanceRole,
		},
	}
}

// collecting is the default group's emit: it produces a full status snapshot for one collector.
func (m *MySql) collecting(c *collector, dataC chan<- *plugin.HarvestData) {
	status := &haprobe.MySqlStatus{}

	data := m.newHarvestData(c, haprobe.HarvestTypeDefault)

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
	fwdCtx, fwdCancel := c.queryCtx()
	defer fwdCancel()
	if err := c.disableSpiderSessionForwarding(fwdCtx); err != nil {
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
}

// beginCollecting fans out one round of the given group over its collectors.
func (m *MySql) beginCollecting(wg *sync.WaitGroup, dataC chan<- *plugin.HarvestData, g *harvestGroup) {
	for _, c := range m.collectors[g.htype] {
		wg.Add(1)

		go func(t *collector) {
			defer wg.Done()

			g.emit(t, dataC)
		}(c)
	}
}

func (m *MySql) collectInterval() time.Duration {
	if m.cfg.Interval < minCollectInterval {
		logger.Warn("collect interval is less than the minimum value, reset to the default value, "+
			"config: %s, minimum: %s, default: %s", m.cfg.Interval, minCollectInterval, defaultCollectInterval)
		return defaultCollectInterval
	}
	return m.cfg.Interval
}

func (m *MySql) heartbeatInterval() time.Duration {
	if m.cfg.HeartbeatInterval < minHeartbeatInterval {
		logger.Warn("heartbeat interval is less than the minimum value, reset to the default value, "+
			"config: %s, minimum: %s, default: %s", m.cfg.HeartbeatInterval, minHeartbeatInterval, defaultHeartbeatInterval)
		return defaultHeartbeatInterval
	}
	return m.cfg.HeartbeatInterval
}

func (m *MySql) replDelayInterval() time.Duration {
	if m.cfg.ReplDelayInterval < minReplDelayInterval {
		logger.Warn("repl delay interval is less than the minimum value, reset to the default value, "+
			"config: %s, minimum: %s, default: %s", m.cfg.ReplDelayInterval, minReplDelayInterval, defaultReplDelayInterval)
		return defaultReplDelayInterval
	}
	return m.cfg.ReplDelayInterval
}

// buildHarvestGroups declares every mysql collection group (cadence, endpoint filter, emit).
func (m *MySql) buildHarvestGroups() []*harvestGroup {
	return []*harvestGroup{
		{
			htype:    haprobe.HarvestTypeDefault,
			interval: m.collectInterval(),
			accept:   func(c *collector) bool { return true },
			emit:     m.collecting,
		},
		{
			htype:    haprobe.HarvestTypeHeartbeat,
			interval: m.heartbeatInterval(),
			accept:   func(c *collector) bool { return !c.isTendbhaProxyAdminPort() },
			emit:     m.collectHeartbeat,
		},
		{
			htype:    haprobe.HarvestTypeReplDelay,
			interval: m.replDelayInterval(),
			accept: func(c *collector) bool {
				return c.isPlainMysqlStorage()
			},
			emit: m.collectReplDelay,
		},
	}
}

// emitDbStatus opens a connection, lets fillStatus populate a fresh MySqlStatus, and sends one
// HarvestData tagged with htype.
func (m *MySql) emitDbStatus(c *collector, htype haprobe.HarvestType,
	dataC chan<- *plugin.HarvestData, fillStatus fillStatusFunc) {
	status := &haprobe.MySqlStatus{}
	var event *haprobe.DbEvent = nil

	data := m.newHarvestData(c, htype)

	defer func() {
		c.close()

		data.Value = status
		if (event != nil) && (len(data.Events) == 0) {
			event.BkCloudID = m.bkCloudID
			data.Events = []*haprobe.DbEvent{event}
		}
		data.ReportTimestamp = uint64(time.Now().Unix())

		dataC <- data
	}()

	if c.endpoint == nil {
		logger.Error("invalid collector, its endpoint is nil, group: %s", htype)
		return
	}

	dbEvent, err := c.open()
	if err != nil {
		dbEvent.BkCloudID = m.bkCloudID
		data.Events = []*haprobe.DbEvent{dbEvent}
		logger.Error("failed to open the collector for the db: %s, group: %s", c.endpoint, htype)
		return
	}

	event = fillStatus(c, status)
}

// collectHeartbeat is the heartbeat group's emit: every probed instance REPLACE
// dbha_heartbeat with sql_log_bin OFF (local write probe, not replication lag),
// then reads HeartbeatDelay from that same local row.
func (m *MySql) collectHeartbeat(c *collector, dataC chan<- *plugin.HarvestData) {
	var fillStatus fillStatusFunc = func(c *collector, status *haprobe.MySqlStatus) *haprobe.DbEvent {
		heartbeatStatus, err := c.obtainHeartbeatStatus(false, heartbeatWriteMaxAttempts)
		status.HeartbeatStatus = heartbeatStatus
		if err != nil {
			logger.Warn("failed to obtain the heartbeat status, host: %s, port: %d, group: %s, errmsg: %s",
				c.endpoint.Host, c.endpoint.Port, haprobe.HarvestTypeHeartbeat, err)
		}

		if heartbeatStatus == nil || heartbeatStatus.WriteSuccess {
			return nil
		}
		return c.writeHeartbeatFailureEvent(errors.New(heartbeatStatus.WriteFailureReason))
	}

	m.emitDbStatus(c, haprobe.HarvestTypeHeartbeat, dataC, fillStatus)
}

// collectReplDelay is the repldelay group's emit: every probed instance REPLACE
// dbha_repl_heartbeat (binlog ON) for its own host:port — a replica may also be
// another topology's master; then also SHOW SLAVE STATUS and read delay from the
// replicated row keyed by Master_Host/Master_Port/Master_Server_Id when present.
func (m *MySql) collectReplDelay(c *collector, dataC chan<- *plugin.HarvestData) {
	var fillStatus fillStatusFunc = func(c *collector, status *haprobe.MySqlStatus) *haprobe.DbEvent {
		masterStatus, err := c.obtainMasterStatus()
		status.MasterStatus = masterStatus
		if err != nil {
			logger.Warn("failed to obtain the master status, ip: %s, port: %d, group: %s, errmsg: %s",
				c.endpoint.Host, c.endpoint.Port, haprobe.HarvestTypeReplDelay, err)
		}

		slaveStatus, err := c.obtainSlaveStatus()
		if err != nil {
			logger.Warn("failed to obtain the slave status, ip: %s, port: %d, group: %s, errmsg: %s",
				c.endpoint.Host, c.endpoint.Port, haprobe.HarvestTypeReplDelay, err)
		}

		status.SlaveStatus = slaveStatus
		return nil
	}

	m.emitDbStatus(c, haprobe.HarvestTypeReplDelay, dataC, fillStatus)
}

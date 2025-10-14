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
	"fmt"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/internal/probe/config"
	"dbm-services/common/dbha-v2/internal/probe/harvester/plugin"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/machine"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

const (
	Name    = "mysql"
	Version = "v1.0.0"
)

// MySql mysql harvester
type MySql struct {
	// NOTE: Must include UnimplementedMethod
	plugin.UnimplementedMethod

	machineID      string
	serviceID      string
	wg             sync.WaitGroup
	cfg            config.HarvesterConfig
	historyMetrics map[string]*haprobe.DatabaseMetric
}

// NewMySql constructor
func NewMySql(cfg config.HarvesterConfig) (*MySql, error) {
	msql := &MySql{
		cfg:            cfg,
		historyMetrics: make(map[string]*haprobe.DatabaseMetric),
	}

	return msql, nil
}

func (m *MySql) connectMySql() ([]*hamysql.DB, []*haprobe.DbEvent, error) {
	epoints, err := hanet.NewEndpoints(m.cfg.Endpoint)
	if err != nil {
		return nil, nil, err
	}

	events := []*haprobe.DbEvent{}
	dbs := []*hamysql.DB{}
	for _, epoint := range epoints {
		db, err := hamysql.New(
			hamysql.OptionProto(epoint.Proto),
			hamysql.OptionIP(epoint.Host),
			hamysql.OptionPort(epoint.Port),
			hamysql.OptionUser(m.cfg.User),
			hamysql.OptionPassword(m.cfg.Password),
		)

		if err != nil {
			logger.Warn("create mysql db operator failed, %v", err)
			events = append(events, &haprobe.DbEvent{
				Name:       haprobe.DbEventNameDetectFailure,
				Reason:     haprobe.DbEventNameReasonConnectionException,
				DbTypeName: haprobe.DbTypeMysql,
				Endpoint:   epoint,
				Message:    err.Error(),
			})

			continue
		}

		dbs = append(dbs, db)
	}

	if len(dbs) == 0 {
		return nil, events, gerrors.New(gerrors.MysqlFailure, "no usable mysql db operator")
	}

	return dbs, events, nil
}

// collectAndSaveMetrics collects and saves metrics.
func (m *MySql) collectAndSaveMetrics() (*haprobe.MySQLMetric, error) {
	// collect metrics from system
	systemMetric, err := m.collectSystemMetrics()
	if err != nil {
		logger.Error("failed to collect host metrics, %v", err)
		return nil, err
	}

	logger.Debug("system metrics(%v)", *systemMetric)

	// collect metrics from mysql instances
	mysqlMetrics, events, err := m.collectMysqlMetrics()
	if err != nil {
		logger.Warn("failed to collect mysql metrics, %v", err)
	}

	logger.Debug("mysql metrics(%v)", mysqlMetrics)

	// combine metrics
	metrics := &haprobe.MySQLMetric{
		SequenceID:      machine.NewSequenceID(),
		MachineID:       m.machineID,
		MessageID:       machine.NewMessageID(),
		ServiceID:       m.serviceID,
		ReportTimestamp: uint64(time.Now().Unix()),
		Host:            systemMetric,
		Events:          events,
		Databases:       mysqlMetrics, // slice, mysql instance metrics
	}

	return metrics, nil
}

// collectSystemMetrics collects system metrics.
func (m *MySql) collectSystemMetrics() (*haprobe.HostMetric, error) {
	systemMetric := &haprobe.HostMetric{}
	if err := obtainCPUMetrics(systemMetric); err != nil {
		logger.Info("failed to harvest CPU info. errmsg: %v", err)
		return systemMetric, err
	}

	if err := obtainStorageMetrics(systemMetric); err != nil {
		logger.Info("failed to harvest Swap/Memory/Disk info. errmsg: %v", err)
		return systemMetric, err
	}

	if err := obtainNetworkMetrics(systemMetric); err != nil {
		logger.Info("failed to harvest Network info. errmsg: %v", err)
		return systemMetric, err
	}

	return systemMetric, nil
}

// collectMySQLInfo collect all instances MySQL metrics.
func (m *MySql) collectMysqlMetrics() ([]*haprobe.DatabaseMetric, []*haprobe.DbEvent, error) {
	var allDbMetrics []*haprobe.DatabaseMetric

	dbs, events, err := m.connectMySql()
	if err != nil {
		return nil, events, err
	}

	// Iterate over configured instances
	for _, db := range dbs {
		// create a DatabaseMetric to store instance metrics
		instanceDbMetrics := haprobe.DatabaseMetric{}

		if err := collectMySQLInfo(db.DB(), &instanceDbMetrics); err != nil {
			continue
		}

		// realtime QPS
		instanceName := fmt.Sprintf("%s:%d", db.Host(), db.Port())
		m.calculateRealTimeQPS(instanceName, &instanceDbMetrics)

		// add single instance metrics to all metrics
		allDbMetrics = append(allDbMetrics, &instanceDbMetrics)

		logger.Debug("mysql db metric(%v)", instanceDbMetrics)
	}

	return allDbMetrics, events, nil
}

// calculateRealTimeQPS to calculate realtime QPS
func (m *MySql) calculateRealTimeQPS(instanceName string, currentMetric *haprobe.DatabaseMetric) {

	// get history metric
	previousMetric, exists := m.historyMetrics[instanceName]
	if !exists {
		// fisrt time to collect, not to calculate
		m.historyMetrics[instanceName] = currentMetric
		return
	}

	// calculate difference between current and previous metric
	queryDiff := currentMetric.QueryTotal - previousMetric.QueryTotal
	if queryDiff > 0 {
		interval := m.cfg.Interval.Seconds()
		realTimeQPS := float64(queryDiff) / interval
		currentMetric.QPS = uint(realTimeQPS)
	}

	// Realtime TPS
	commitDiff := currentMetric.QueryCommits - previousMetric.QueryCommits
	rollbackDiff := currentMetric.QueryRollbacks - previousMetric.QueryRollbacks
	totalDiff := commitDiff + rollbackDiff
	if totalDiff > 0 {
		interval := m.cfg.Interval.Seconds()
		realTimeTPS := float64(totalDiff) / interval
		currentMetric.TPS = uint(realTimeTPS)
	}

	m.historyMetrics[instanceName] = currentMetric
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

	m.wg.Add(1)
	go func(ctx context.Context) {
		defer m.wg.Done()
		defer close(dataC)

		ticker := time.NewTicker(m.cfg.Interval)
		defer ticker.Stop()

		for {
			select {
			case <-ctx.Done():
				logger.Info("exit harvester(mysql)")
				return

			case <-ticker.C:
				// collect data from the target instance.
				metrics, err := m.collectAndSaveMetrics()
				if err != nil {
					logger.Error("failed to collect mysql metrics: %v", err)
					// Retry next instance if failed to maintain availability
					continue
				}

				logger.Debug("mysql harvest data(%v)", *metrics)

				dataC <- &plugin.HarvestData{
					Value: metrics,
				}
			}
		}
	}(ctx)

	return dataC, nil
}

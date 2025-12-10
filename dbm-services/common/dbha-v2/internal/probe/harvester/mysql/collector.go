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
	"time"

	"dbm-services/common/dbha-v2/internal/probe/harvester/base"
	"dbm-services/common/dbha-v2/pkg/converter"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

type collector struct {
	base.Collector

	clusterType haprobe.DbmMetadataClusterType
	machineType haprobe.DbmMetadataMachineType
	accessLayer haprobe.DbmMetadataAccessLayerType
	user        string
	password    string
	endpoint    *hanet.Endpoint
	db          *hamysql.GormDB
	isAdminNode bool
}

func (c *collector) open() (*haprobe.DbEvent, error) {
	db, err := hamysql.NewGormDB(
		hamysql.OptionProto(c.endpoint.Proto),
		hamysql.OptionIP(c.endpoint.Host),
		hamysql.OptionPort(c.endpoint.Port),
		hamysql.OptionUser(c.user),
		hamysql.OptionPassword(c.password),
		hamysql.OptionSkipInitializeWithVersion(false),
		hamysql.OptionDisableDatetimePrecision(true),
		hamysql.OptionCharset(""),
	)

	if err != nil {
		logger.Warn("create mysql db operator failed, %v", err)
		event := &haprobe.DbEvent{
			Name:       haprobe.DbEventNameDetectFailure,
			Reason:     haprobe.DbEventNameReasonConnectionException,
			DbTypeName: haprobe.DbTypeMysql,
			Endpoint:   c.endpoint,
			Message:    err.Error(),
		}

		return event, err
	}

	sqlDb, err := db.DB().DB()

	if err != nil {
		event := &haprobe.DbEvent{
			Name:       haprobe.DbEventNameDetectFailure,
			Reason:     haprobe.DbEventNameReasonConnectionException,
			DbTypeName: haprobe.DbTypeMysql,
			Endpoint:   c.endpoint,
			Message:    err.Error(),
		}

		return event, err
	}

	sqlDb.SetMaxIdleConns(1)
	sqlDb.SetMaxOpenConns(3)
	sqlDb.SetConnMaxLifetime(time.Minute * 3)

	c.db = db
	return nil, nil
}

func (c *collector) close() {
	if c.db != nil {
		c.db.Close()
	}
}

func (c *collector) isTendbHaProxy() bool {
	return c.accessLayer == haprobe.DbmMetadataAccessLayerTypeProxy &&
		c.machineType == haprobe.DbmMetadataMachineTypeProxy &&
		c.clusterType == haprobe.DbmMetadataClusterTypeTendb
}

func (c *collector) isTendbClusterProxy() bool {
	return c.accessLayer == haprobe.DbmMetadataAccessLayerTypeProxy &&
		c.machineType == haprobe.DbmMetadataMachineTypeSpider &&
		c.clusterType == haprobe.DbmMetadataClusterTypeTendbCluster
}

func (c *collector) isAdmin() bool {
	return c.isAdminNode
}

func (c *collector) obtainTendbClusterProxyStatus() (*haprobe.MySqlSpiderCtlStatus, error) {
	var routes []haprobe.MySqlSpiderCtlRoute
	err := c.db.DB().Raw("select * from mysql.servers").Scan(&routes).Error

	if err != nil {
		logger.Warn("failed to get MySQL spider routes, errmsg: %s", err)
		return nil, err
	}

	var nodes []haprobe.MySqlSpiderCtlNode
	err = c.db.DB().Raw("select * from information_schema.TDBCTL_NODES").Scan(&nodes).Error

	if err != nil {
		logger.Warn("failed to get MySQL spider nodes, errmsg: %s", err)
		return nil, err
	}

	status := &haprobe.MySqlSpiderCtlStatus{
		Routes:   routes,
		CtlNodes: nodes,
	}

	return status, nil
}

func (c *collector) obtainTendbHaProxyStatus() (*haprobe.MySqlProxyStatus, error) {
	var backends []haprobe.MySqlProxyBackend
	err := c.db.DB().Raw("select * from backends").Scan(&backends).Error

	if err != nil {
		logger.Warn("failed to get MySQL proxy status, errmsg: %s", err)
		return nil, err
	}

	return &haprobe.MySqlProxyStatus{Backends: backends}, nil
}

func (c *collector) obtainGlobalStatus() (*haprobe.MySqlGlobalStatus, error) {
	var statusResults []globalStatus
	err := c.db.DB().Raw("SHOW GLOBAL STATUS").Scan(&statusResults).Error
	if err != nil {
		return nil, err
	}

	dbStatus := convertToMySqlStatus(statusResults)

	var version string
	err = c.db.DB().Raw("SELECT VERSION() as version").Scan(&version).Error
	if err != nil {
		logger.Warn("failed to get mysql version, errmsg: %s", err)
		return nil, err
	}
	dbStatus.Version = version

	var portResult globalStatus
	err = c.db.DB().Raw("SHOW VARIABLES LIKE 'port'").Scan(&portResult).Error
	if err != nil {
		logger.Warn("failed to get mysql listen port, result: %s, errmsg: %s", portResult, err)
		return nil, err
	}

	port, err := converter.ToInt(portResult.Value)
	if err != nil {
		logger.Error("failed to convert mysql listen port to int, port: %v, errmsg: %s", portResult.Value, err)
		return nil, err
	}

	logger.Debug("mysql listen port:%v", port)

	dbStatus.ListenPort = port

	// Key buffer read hit rate
	if dbStatus.KeyReadRequests != 0 {
		dbStatus.KeyBufferHitRate = float64(dbStatus.KeyReads) / float64(dbStatus.KeyReadRequests)
	}

	return dbStatus, err
}

// obtainlHostStatus obtain this host status
func (c *collector) obtainHostStatus() (*haprobe.HostMetric, error) {
	hostStatus := &haprobe.HostMetric{}

	if err := c.SetCpuStatus(hostStatus); err != nil {
		logger.Warn("failed to update CPU status, errmsg: %s", err)
	}

	if err := c.SetNetStatus(hostStatus); err != nil {
		logger.Warn("failed to update Net status, errmsg: %s", err)
	}

	if err := c.SetMemoryStatus(hostStatus); err != nil {
		logger.Warn("failed to update memory status, errmsg: %s", err)
	}

	if err := c.SetDiskStatus(hostStatus); err != nil {
		logger.Warn("failed to update memory status, errmsg: %s", err)
	}

	return hostStatus, nil
}

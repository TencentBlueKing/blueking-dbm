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

package switcher

import (
	"database/sql"

	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
)

// SpiderInstanceInfo represents spider node information in TenDBCluster
type SpiderInstanceInfo struct {
	IP         string                        `json:"ip"`
	Port       int                           `json:"port"`
	AdminPort  int                           `json:"admin_port"`
	SpiderRole hamodel.DbmMetadataSpiderRole `json:"spider_role"`
	Status     hamodel.DbmMetadataStatus     `json:"status"`
}

// TdbctlRouteInfo contains TDBCTL routing information
type TdbctlRouteInfo struct {
	ServerName string `gorm:"column:Server_name"`
	Host       string `gorm:"column:HOST"`
	UserName   string `gorm:"column:Username"`
	Password   string `gorm:"column:Password"`
	Port       int    `gorm:"column:PORT"`
	Wrapper    string `gorm:"column:Wrapper"`
}

// TdbctlPrimaryInfo holds information for primary TDBCTL node
type TdbctlPrimaryInfo struct {
	ServerName string `gorm:"column:SERVER_NAME"`
	Host       string `gorm:"column:HOST"`
	Port       int    `gorm:"column:PORT"`
	/* if 1, indicate this server is primary
	only primary node broken-down trigger elect
	*/
	IsThisServer int `gorm:"column:IS_THIS_SERVER"`
}

// TdbctlNodeInfo represents node information of TDBCTL node
type TdbctlNodeInfo struct {
	ServerName        string `gorm:"column:SERVER_NAME;NOT NULL"`
	Host              string `gorm:"column:HOST;NOT NULL"`
	Port              int    `gorm:"column:PORT;default:0;NOT NULL"`
	ReplicationMaster string `gorm:"column:REPLICATION_MASTER;NOT NULL"`
	ClusterRole       string `gorm:"column:CLUSTER_ROLE;NOT NULL"`
	Status            string `gorm:"column:STATUS;NOT NULL"`
	Message           string `gorm:"column:MESSAGE;NOT NULL"`
	ReplicationInfo   string `gorm:"column:REPLICATION_INFO;NOT NULL"`
}

// TenDBClusterInstanceMetadata extends MySQL metadata with spider nodes information
type TenDBClusterInstanceMetadata struct {
	MySQLInstanceMetadata
	SpiderNodes []SpiderInstanceInfo
}

// TenDBClusterBaseSwitchInstance provides base switching functionality for TenDBCluster
type TenDBClusterBaseSwitchInstance struct {
	MySQLBaseSwitchInstance

	// The following are instance metadata information from DBM

	SpiderNodes []SpiderInstanceInfo

	// The following are information from TDBCTL node

	TdbctlRouteTable     []TdbctlRouteInfo
	PrimaryTdbctl        *TdbctlPrimaryInfo
	NewPrimaryTdbctl     *TdbctlPrimaryInfo
	SecondaryTdbctlNodes []TdbctlNodeInfo
}

// GetNodeRoute get route info from route table by ip,port
func (sw *TenDBClusterBaseSwitchInstance) GetNodeRoute(host string, port int) *TdbctlRouteInfo {
	// todo
	return nil
}

// QueryRouteInfo query route info from mysql.servers
func (sw *TenDBClusterBaseSwitchInstance) QueryRouteInfo(db *sql.DB) ([]TdbctlRouteInfo, error) {
	// todo
	return nil, nil
}

// QueryNodesInfo query nodes info from information_schema.TDBCTL_NODES
func (sw *TenDBClusterBaseSwitchInstance) QueryNodesInfo(db *sql.DB) (map[string]TdbctlNodeInfo, error) {
	// todo
	return nil, nil
}

// RemoveNodeFromRoute connect primary node and remove input node's route
func (sw *TenDBClusterBaseSwitchInstance) RemoveNodeFromRoute(primaryConn *sql.DB, host string, port int) error {
	// todo
	return nil
}

// GetPrimary found primary node from any connected tdbctl node's route table
// If no primary found, return error.
// Any blow condition could get primary success
//  1. There is only one node: PrimaryRole
//  2. No primary role found, and all alive SecondaryRole node's ReplicationMaster are the same,
//     then thought the ReplicationMaster must be the Primary node's ServerName
func (sw *TenDBClusterBaseSwitchInstance) GetPrimary() error {
	// todo
	return nil
}

// SetSpiderNodes get all spider nodes from dbmeta
func (sw *TenDBClusterBaseSwitchInstance) SetSpiderNodes() error {
	// todo
	return nil
}

// CheckSwitch check switch condition
func (sw *TenDBClusterBaseSwitchInstance) CheckSwitch() (bool, error) {
	// todo
	return true, nil
}

// TenDBClusterSpiderSwitchInstance switch instance for spider
type TenDBClusterSpiderSwitchInstance struct {
	TenDBClusterBaseSwitchInstance
}

// EnablePrimary connect candidate node and execute TDBCTL ENABLE PRIMARY FORCE
func (sw *TenDBClusterSpiderSwitchInstance) EnablePrimary(rawPrimaryNode *TdbctlNodeInfo) error {
	// todo
	return nil
}

// ElectPrimaryCandidate elect primary candidate
func (sw *TenDBClusterSpiderSwitchInstance) ElectPrimaryCandidate() (*TdbctlNodeInfo, error) {
	// todo
	return nil, nil
}

// DoSwitch do spider(include tdbctl) switch
// 1. release broken-down node's name service if exist
// 2. found primary tdbctl, if primary broken-down, do elect first
// 3. remove broken-down node from primary-tdbctl route table
// 4. primary-tdbctl do flush routing
func (sw *TenDBClusterSpiderSwitchInstance) DoSwitch() error {
	// todo
	return nil
}

// DoFinal do final work
func (sw *TenDBClusterSpiderSwitchInstance) DoFinal() error {
	// todo
	return nil
}

// ShowSwitchInstanceInfo show db-mysql instance's switch info
func (sw *TenDBClusterSpiderSwitchInstance) ShowSwitchInstanceInfo() string {
	// todo
	return ""
}

// TenDBClusterRemoteSwitchInstance switch instance for remote
type TenDBClusterRemoteSwitchInstance struct {
	TenDBClusterBaseSwitchInstance
}

// CheckSwitch check slave before switch
func (sw *TenDBClusterRemoteSwitchInstance) CheckSwitch() (bool, error) {
	// todo
	return true, nil
}

// DoSwitch do remote switch
// 1. connect primary tdbctl and update route
// 2. flush routing
func (sw *TenDBClusterRemoteSwitchInstance) DoSwitch() error {
	// todo
	return nil
}

// ShowSwitchInstanceInfo show db-mysql instance's switch info
func (sw *TenDBClusterRemoteSwitchInstance) ShowSwitchInstanceInfo() string {
	// todo
	return ""
}

// UpdateMetaInfo swap master, slave 's meta info in cmdb
func (sw *TenDBClusterRemoteSwitchInstance) UpdateMetaInfo() error {
	// todo
	return nil
}

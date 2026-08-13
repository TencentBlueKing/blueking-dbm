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

package haprobe

var _ DBTyper = (*MySqlStatus)(nil)

// MySqlStatus MySQL status
type MySqlStatus struct {
	// Spider Controller Status
	SpiderCtlStatus *MySqlSpiderCtlStatus `json:"spider_ctl_status,omitempty"`

	// Proxy Status
	ProxyStatus *MySqlProxyStatus `json:"proxy_status,omitempty"`

	// Proxy Service (data) Port Status
	ProxyServicePortStatus *MySqlProxyServicePortStatus `json:"proxy_service_port_status,omitempty"`

	// Global Status
	GlobalStatus *MySqlGlobalStatus `json:"global_status,omitempty"`

	// Heartbeat Status
	HeartbeatStatus *MySqlHeartbeatStatus `json:"heartbeat_status,omitempty"`

	// Master Status
	MasterStatus *MySqlHeartbeatStatus `json:"master_status,omitempty"`

	// Slave Status
	SlaveStatus *MySqlSlaveStatus `json:"slave_status,omitempty"`

	// Storage Engines
	InnoDB *InnoDBStatus `json:"innodb,omitempty"`
}

// GetDbType Return the Db type name, this function name can't be changed.
func (m MySqlStatus) GetDbType() DbType {
	return DbTypeMySql
}

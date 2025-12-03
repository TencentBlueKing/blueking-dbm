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

// MySqlProxyBackend MySQL proxy backend
type MySqlProxyBackend struct {
	BackendNdx       int    `gorm:"column:backend_ndx"       json:"backend_ndx"`
	Address          string `gorm:"column:address"           json:"address"`
	State            string `gorm:"column:state"             json:"state"`
	Type             string `gorm:"column:type"              json:"type"`
	UUID             string `gorm:"column:uuid"              json:"uuid"`
	ConnectedClients int    `gorm:"column:connected_clients" json:"connected_clients"`
	RefreshTime      int    `gorm:"column:refresh_time"      json:"refresh_time"`
}

// MySqlProxyStatus MySQL proxy status for the TendbHA cluster.
type MySqlProxyStatus struct {
	Backends []MySqlProxyBackend `json:"backends"`
}

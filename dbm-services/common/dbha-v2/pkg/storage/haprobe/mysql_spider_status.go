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

// MySqlSpiderCtlRoute MySQL spider node information.
type MySqlSpiderCtlRoute struct {
	ServerName string `gorm:"column:Server_Name" json:"server_name"`
	Host       string `gorm:"column:Host"        json:"host"`
	Db         string `gorm:"column:Db"          json:"db"`
	UserName   string `gorm:"column:Username"    json:"user_name"`
	Port       int    `gorm:"column:Port"        json:"port"`
	Wrapper    string `gorm:"column:Wrapper"     json:"wrapper"`
	Owner      string `gorm:"column:Owner"       json:"owner"`
}

// MySqlSpiderCtlNode MySQL spider controller node information.
type MySqlSpiderCtlNode struct {
	ServerName        string `gorm:"column:SERVER_NAME"        json:"server_name"`
	Host              string `gorm:"column:HOST"               json:"host"`
	Port              int    `gorm:"column:PORT"               json:"port"`
	ReplicationMaster string `gorm:"column:REPLICATION_MASTER" json:"replication_master"`
	ReplicationInfo   string `gorm:"column:REPLICATION_INFO"   json:"replication_info"`
	ClusterRole       string `gorm:"column:CLUSTER_ROLE"       json:"cluster_role"`
	Status            string `gorm:"column:STATUS"             json:"status"`
	Message           string `gorm:"column:MESSAGE"            json:"message"`
}

// MySqlSpiderCtlStatus MySQL spider status for the TendbCluster.
type MySqlSpiderCtlStatus struct {
	Routes   []MySqlSpiderCtlRoute `json:"routes"`
	CtlNodes []MySqlSpiderCtlNode  `json:"ctl_nodes"`
}

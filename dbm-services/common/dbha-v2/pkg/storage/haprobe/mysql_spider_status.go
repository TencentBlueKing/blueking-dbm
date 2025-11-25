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
	ServerName string `json:"server_name"`
	Host       string `json:"host"`
	Db         string `json:"db"`
	UserName   string `json:"user_name"`
	Port       int    `json:"port"`
	Wrapper    string `json:"wrapper"`
	Owner      string `json:"owner"`
}

// MySqlSpiderCtlNode MySQL spider controller node information.
type MySqlSpiderCtlNode struct {
	ServerName        string `json:"server_name"`
	Host              string `json:"host"`
	Port              int    `json:"port"`
	ReplicationMaster string `json:"replication_master"`
	ReplicationInfo   string `json:"replication_info"`
	ClusterRole       string `json:"cluster_role"`
	Status            string `json:"status"`
	Message           string `json:"message"`
}

// MySqlSpiderCtlStatus MySQL spider status for the TendbCluster.
type MySqlSpiderCtlStatus struct {
	Routes   []*MySqlSpiderCtlRoute `json:"routes"`
	CtlNodes []*MySqlSpiderCtlNode  `json:"ctl_nodes"`
}

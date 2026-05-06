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

// RedisClusterStatus RedisCluster storage status
type RedisClusterStatus struct {
	Base        RedisBaseStatus        `json:"base,omitempty"`
	Memory      RedisMemoryStatus      `json:"memory,omitempty"`
	Master      RedisMasterInfo        `json:"master,omitempty"`
	Persistence RedisPersistenceStatus `json:"persistence,omitempty"`

	ClusterConnections     int64                    `json:"cluster_connections,omitempty"`
	BlockedClients         int64                    `json:"blocked_clients,omitempty"`
	MaxMemoryHuman         string                   `json:"maxmemory_human,omitempty"`
	MasterReplOffset       int64                    `json:"master_repl_offset,omitempty"`
	ReplBacklogActive      int                      `json:"repl_backlog_active,omitempty"`
	SlaveStates            []RedisClusterSlaveState `json:"slave_states,omitempty"`
	InstantaneousOpsPerSec int64                    `json:"instantaneous_ops_per_sec,omitempty"`
	SyncFull               int64                    `json:"sync_full,omitempty"`
	SyncPartialErr         int64                    `json:"sync_partial_err,omitempty"`
	TotalErrorReplies      int64                    `json:"total_error_replies,omitempty"`
	ClusterEnabled         int                      `json:"cluster_enabled,omitempty"`
	Keyspace               []RedisDBKeyspace        `json:"keyspace,omitempty"`
}

// RedisClusterSlaveState RedisCluster slave state
type RedisClusterSlaveState struct {
	ID     int    `json:"id,omitempty"`
	IP     string `json:"ip,omitempty"`
	Port   int    `json:"port,omitempty"`
	State  string `json:"state,omitempty"`
	Offset int64  `json:"offset,omitempty"`
	Lag    int64  `json:"lag,omitempty"`
}

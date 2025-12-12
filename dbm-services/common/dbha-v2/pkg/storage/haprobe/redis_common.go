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

// RedisDBKeyspace keyspace info for a single database
type RedisDBKeyspace struct {
	DB      int   `json:"db,omitempty"`
	Keys    int64 `json:"keys,omitempty"`
	Expires int64 `json:"expires,omitempty"`
	AvgTTL  int64 `json:"avg_ttl,omitempty"`
}

// RedisBaseStatus common fields for all Redis storage types
type RedisBaseStatus struct {
	UptimeInSeconds        int64  `json:"uptime_in_seconds,omitempty"`
	ConnectedClients       int64  `json:"connected_clients,omitempty"`
	RejectedConnections    int64  `json:"rejected_connections,omitempty"`
	Role                   string `json:"role,omitempty"`
	ConnectedSlaves        int64  `json:"connected_slaves,omitempty"`
	MasterLinkStatus       string `json:"master_link_status,omitempty"`
	MasterLastIOSecondsAgo int64  `json:"master_last_io_seconds_ago,omitempty"`
	SlaveReplOffset        int64  `json:"slave_repl_offset,omitempty"`
}

// RedisMemoryStatus memory related fields
type RedisMemoryStatus struct {
	UsedMemoryHuman       string  `json:"used_memory_human,omitempty"`
	MemFragmentationRatio float64 `json:"mem_fragmentation_ratio,omitempty"`
}

// RedisMasterInfo master node info (for slave nodes)
type RedisMasterInfo struct {
	MasterHost string `json:"master_host,omitempty"`
	MasterPort int    `json:"master_port,omitempty"`
}

// RedisSlaveState common slave state structure
type RedisSlaveState struct {
	ID    int    `json:"id,omitempty"`
	State string `json:"state,omitempty"`
}

// RedisPersistenceStatus persistence related fields
type RedisPersistenceStatus struct {
	RDBLastBgsaveStatus string `json:"rdb_last_bgsave_status,omitempty"`
	AOFLastWriteStatus  string `json:"aof_last_write_status,omitempty"`
}

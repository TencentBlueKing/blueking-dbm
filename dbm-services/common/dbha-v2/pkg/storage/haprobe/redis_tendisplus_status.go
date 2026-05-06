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

// RedisTendisPlusStatus TendisPlus storage status
type RedisTendisPlusStatus struct {
	Base   RedisBaseStatus `json:"base,omitempty"`
	Master RedisMasterInfo `json:"master,omitempty"`

	UsedMemoryRss          int64                              `json:"used_memory_rss,omitempty"`
	UsedMemoryRssHuman     string                             `json:"used_memory_rss_human,omitempty"`
	MasterReplOffset       int64                              `json:"master_repl_offset,omitempty"`
	SlaveStates            []RedisSlaveState                  `json:"slave_states,omitempty"`
	RocksDBSlaveStates     []RedisTendisPlusRocksDBSlaveState `json:"rocksdb_slave_states,omitempty"`
	InstantaneousOpsPerSec int64                              `json:"instantaneous_ops_per_sec,omitempty"`
	SyncFull               int64                              `json:"sync_full,omitempty"`
	SyncPartialOk          int64                              `json:"sync_partial_ok,omitempty"`
	SyncPartialErr         int64                              `json:"sync_partial_err,omitempty"`
	ClusterEnabled         int                                `json:"cluster_enabled,omitempty"`
	RocksDBBgErrorCount    int64                              `json:"rocksdb_bg_error_count,omitempty"`
	Keyspace               []RedisDBKeyspace                  `json:"keyspace,omitempty"`
}

// RedisTendisPlusRocksDBSlaveState TendisPlus RocksDB slave state
type RedisTendisPlusRocksDBSlaveState struct {
	RocksDBID int    `json:"rocksdb_id,omitempty"`
	SlaveID   int    `json:"slave_id,omitempty"`
	State     string `json:"state,omitempty"`
}

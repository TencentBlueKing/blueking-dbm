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

var _ DBTyper = (*RedisStatus)(nil)

// Redis probe state values used by every Redis probe item.
const (
	// RedisStateOk indicates the command executed without error.
	RedisStateOk = "ok"
	// RedisStateFailed indicates the command execution failed.
	RedisStateFailed = "failed"
)

// RedisStatus Redis status. It aggregates the three probe items: the INFO
// Replication probe, the SELECT + SET write probe and the TYPE read-only probe.
type RedisStatus struct {
	// ReplicationStatus is the INFO Replication probe result for storage instances.
	ReplicationStatus *RedisReplicationStatus `json:"replication_status,omitempty"`

	// HeartbeatStatus is the SELECT + SET write probe result for storage masters.
	HeartbeatStatus *RedisHeartbeatStatus `json:"heartbeat_status,omitempty"`

	// ReadCheckStatus is the TYPE read-only probe result for proxy instances.
	ReadCheckStatus *RedisReadCheckStatus `json:"read_check_status,omitempty"`
}

// GetDbType Return the Db type name, this function name can't be changed.
func (r RedisStatus) GetDbType() DbType {
	return DbTypeRedis
}

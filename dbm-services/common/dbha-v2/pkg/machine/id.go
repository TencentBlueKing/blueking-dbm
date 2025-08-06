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

package machine

import (
	"bk-dbconfig/pkg/core/logger"
	"crypto/sha256"
	"encoding/binary"
	"hash/fnv"
	"sync"
	"time"

	"github.com/denisbrodbeck/machineid"
	"github.com/google/uuid"
)

var (
	sf         *Snowflake
	sfmu       sync.Mutex
	id         string
	idErr      error
	idHash     uint64
	lastSeqID  uint64
	idOnce     ResetOnce
	idHashOnce ResetOnce
)

// Hash Calculate the hash value of any string.
// s    The target string value
// bits The number of digits to be retained.
func Hash(s string, bits uint) uint64 {
	h1 := sha256.Sum256([]byte(s))
	h2 := fnv.New64a()
	h2.Write(h1[:])

	fullHash := binary.BigEndian.Uint64(h1[:8]) ^ h2.Sum64()
	mask := uint64(1<<bits - 1)
	return fullHash & mask
}

// NewMachineID  return the  machine-id
func ID() (string, error) {
	idOnce.Do(func() error {
		id, idErr = machineid.ProtectedID("dbha-v2")
		return idErr
	})
	return id, idErr
}

// NewSequenceID create a new sequence-id
func NewSequenceID() uint64 {
	sfmu.Lock()
	defer sfmu.Unlock()

	if lastSeqID == 0 {
		lastSeqID = uint64(time.Now().UnixMicro())
	}

	idHashOnce.Do(func() error {
		idHash = Hash(id, machineIDBits)
		return nil
	})

	if sf == nil {
		epoch, _ := time.Parse("2006-01-02", "2024-08-01")
		s, e := NewSnowflake(idHash, epoch)
		if e != nil {
			logger.Warn("failed to generate snowflake sequence-id, use the defalut generate strategy, %v", e)
			return 0
		}
		sf = s
	}

	id, err := sf.NextID()

	if err != nil {
		// After the time rewind, only one retry is allowed.
		s, e := NewSnowflake(idHash, time.Now())
		if e != nil {
			logger.Warn("failed to generate snowflake sequence-id, use the defalut generate strategy, %v", e)
			lastSeqID++
			return lastSeqID
		}

		sf = s
		id, err = sf.NextID()
	}

	if err != nil {
		logger.Warn("failed to generate snowflake sequence-id, use the defalut generate strategy, %v", err)
		lastSeqID++
		return lastSeqID
	}

	lastSeqID = id
	return id
}

// NewMessageID create a new message-id
func NewMessageID() string {
	id := uuid.New()
	return id.String()
}

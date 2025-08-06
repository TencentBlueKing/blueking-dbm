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
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"sync"
	"time"
)

const (
	timeBits              = 41  // timestamp bit count
	machineIDBits         = 10  // machine id bit count
	sequenceBits          = 12  // serial number bit count
	maxRollbackTimeMillis = 100 // Max rollback time
	maxMachineID          = -1 ^ (-1 << machineIDBits)
	maxSequence           = -1 ^ (-1 << sequenceBits)
	timeShift             = machineIDBits + sequenceBits
	machineShift          = sequenceBits
)

type Snowflake struct {
	mu            sync.Mutex
	epoch         uint64 // Customize era time(in milliseconds).
	machineID     uint64 // Machine ID.
	sequence      uint64 // Serial number.
	lastTimestamp uint64 // The timestamp when the ID was last generated.
	timeBackward  bool   // Clock rewind indicator.
}

// NewSnowflake create new snowflake object
func NewSnowflake(machineID uint64, epoch time.Time) (*Snowflake, error) {
	if machineID < 0 || machineID > maxMachineID {
		return nil, gerrors.New(gerrors.InvalidParameter, "machine-id out of range")
	}

	return &Snowflake{
		epoch:     uint64(epoch.UnixMilli()),
		machineID: machineID,
	}, nil
}

func (s *Snowflake) NextID() (uint64, error) {
	s.mu.Lock()
	defer s.mu.Unlock()

	current := uint64(time.Now().UnixMilli()) - s.epoch

	if current < s.lastTimestamp {
		s.timeBackward = true
		offset := s.lastTimestamp - current

		if offset > maxRollbackTimeMillis {
			// Allow for clock rollbacks within 100 milliseconds.
			return 0, gerrors.New(gerrors.Failure, "clock moved backwards too much")
		}

		// Wait for the clock to catch up.
		time.Sleep(time.Duration(offset) * time.Millisecond)
		current = uint64(time.Now().UnixMilli()) - s.epoch

		if current < s.lastTimestamp {
			return 0, gerrors.New(gerrors.Failure, "clock moved backwards after waiting")
		}
	}

	if current == s.lastTimestamp {
		s.sequence = (s.sequence + 1) & maxSequence
		if s.sequence == 0 {
			// The current millisecond sequence number has been exhausted.
			// Waitint for the nexe millisecond.
			current = uint64(s.waitNextMillis())
		}
	} else {
		s.sequence = current & maxSequence
	}

	s.lastTimestamp = current
	return (current << timeShift) | (s.machineID << machineShift) | s.sequence, nil
}

func (s *Snowflake) waitNextMillis() uint64 {
	current := uint64(time.Now().UnixMilli()) - s.epoch

	for current <= s.lastTimestamp {
		time.Sleep(100 * time.Microsecond)
		current = uint64(time.Now().UnixMilli()) - s.epoch
	}

	return current
}

func (s *Snowflake) ParseID(id uint64) (timestamp, machineID, sequence uint64) {
	timestamp = (id >> timeShift) + uint64(s.epoch)
	machineID = (id >> machineShift) & maxMachineID
	sequence = id & maxSequence
	return
}

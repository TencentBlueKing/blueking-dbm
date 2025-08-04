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
	"sync"
	"time"
)

const (
	timeBits      = 41 // timestamp bit count
	machineIDBits = 10 // machine id bit count
	sequenceBits  = 12 // serial number bit count
	maxMachineID  = -1 ^ (-1 << machineIDBits)
	maxSequence   = -1 ^ (-1 << sequenceBits)
	timeShift     = machineIDBits + sequenceBits
	machineShift  = sequenceBits
)

type Snowflake struct {
	mu            sync.Mutex
	epoch         int64 // Customize era time(in milliseconds).
	machineID     int64 // Machine ID.
	sequence      int64 // Serial number.
	lastTimestamp int64 // The timestamp when the ID was last generated.
	timeBackward  bool  // Clock rewind indicator.
}

// NewSnowflake create new snowflake object
func NewSnowflake(machineID int64, epoch time.Time) (*Snowflake, error) {
	return nil, nil
}

func (s *Snowflake) NextID() uint64 {
	return 0
}

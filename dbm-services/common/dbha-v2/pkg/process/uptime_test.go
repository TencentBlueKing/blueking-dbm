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

package process

import (
	"testing"
	"time"
)

func TestSystemUptime(t *testing.T) {
	uptime, err := SystemUptime()
	if err != nil {
		t.Fatalf("SystemUptime failed, errmsg: %s", err)
	}
	if uptime <= 0 {
		t.Errorf("SystemUptime = %s, want > 0", uptime)
	}
}

func TestSelfUptime(t *testing.T) {
	uptime, err := SelfUptime()
	if err != nil {
		t.Fatalf("SelfUptime failed, errmsg: %s", err)
	}
	if uptime < 0 {
		t.Errorf("SelfUptime = %s, want >= 0", uptime)
	}
	sysUptime, err := SystemUptime()
	if err != nil {
		t.Fatalf("SystemUptime failed, errmsg: %s", err)
	}
	// Process cannot have started before the OS; allow a small tolerance.
	if uptime > sysUptime+time.Second {
		t.Errorf("SelfUptime %s > SystemUptime %s", uptime, sysUptime)
	}
}

func TestSelfStartedAt(t *testing.T) {
	startedAt, err := SelfStartedAt()
	if err != nil {
		t.Fatalf("SelfStartedAt failed, errmsg: %s", err)
	}
	now := time.Now()
	if startedAt.After(now.Add(time.Second)) {
		t.Errorf("SelfStartedAt %s is after now %s", startedAt, now)
	}
	lowerBound := time.Date(2020, 1, 1, 0, 0, 0, 0, time.UTC)
	if startedAt.Before(lowerBound) {
		t.Errorf("SelfStartedAt %s is before lower bound %s", startedAt, lowerBound)
	}
}

func TestSelfUptimeMonotonic(t *testing.T) {
	first, err := SelfUptime()
	if err != nil {
		t.Fatalf("SelfUptime failed, errmsg: %s", err)
	}
	time.Sleep(50 * time.Millisecond)
	second, err := SelfUptime()
	if err != nil {
		t.Fatalf("SelfUptime failed, errmsg: %s", err)
	}
	if second < first {
		t.Errorf("SelfUptime not monotonic: first %s, second %s", first, second)
	}
}

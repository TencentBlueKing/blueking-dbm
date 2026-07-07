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
	"crypto/sha1"
	"encoding/hex"
)

// Named-event layout: Local\dbha-probe-<first16hex(sha1(key))><suffix>.
const (
	eventNamePrefix   = `Local\dbha-probe-`
	stopEventSuffix   = "-stop"
	reloadEventSuffix = "-reload"
)

// DeriveEventName builds a deterministic named-event name from an opaque key.
// The same key must be used by the process that creates/waits on the event and
// by whatever sets it (the stop command for pid-file keys, or the keepalive stop
// script for the ping-http-addr key).
func DeriveEventName(key, suffix string) string {
	sum := sha1.Sum([]byte(key))
	return eventNamePrefix + hex.EncodeToString(sum[:])[:16] + suffix
}

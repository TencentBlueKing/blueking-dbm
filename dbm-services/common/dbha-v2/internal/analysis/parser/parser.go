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

package parser

import (
	"encoding/json"
	"fmt"
	"sync"

	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

// Processer parses one raw status payload into a DB event.
// Concrete implementations live in provider/<db>/parse and register via Register.
type Processer interface {
	Process(task json.RawMessage) (*haprobe.DbEvent, error)
}

// DBTyperWrapper pairs a DbType with its raw status payload.
type DBTyperWrapper struct {
	DbTypeName haprobe.DbType
	Value      json.RawMessage
}

var (
	parsersMu sync.RWMutex
	parsers   = map[haprobe.DbType]Processer{}
)

// Register registers a Processer for a DbType. Panics on duplicate, nil, or invalid DbType.
func Register(dbType haprobe.DbType, p Processer) {
	if dbType == haprobe.DbTypeNone || dbType == haprobe.DbTypeUnknown {
		panic(fmt.Sprintf("parser: refuse to register invalid DbType: %q", dbType))
	}
	if p == nil {
		panic(fmt.Sprintf("parser: refuse to register nil Processer for DbType: %s", dbType))
	}

	parsersMu.Lock()
	defer parsersMu.Unlock()

	if _, exists := parsers[dbType]; exists {
		panic(fmt.Sprintf("parser: duplicate DbType registration: %s", dbType))
	}
	parsers[dbType] = p
}

// Lookup returns the registered Processer for a DbType, if any.
func Lookup(dbType haprobe.DbType) (Processer, bool) {
	parsersMu.RLock()
	defer parsersMu.RUnlock()
	p, ok := parsers[dbType]
	return p, ok
}

// RegisteredDbTypes returns all registered DbTypes (unordered).
func RegisteredDbTypes() []haprobe.DbType {
	parsersMu.RLock()
	defer parsersMu.RUnlock()
	out := make([]haprobe.DbType, 0, len(parsers))
	for dt := range parsers {
		out = append(out, dt)
	}
	return out
}

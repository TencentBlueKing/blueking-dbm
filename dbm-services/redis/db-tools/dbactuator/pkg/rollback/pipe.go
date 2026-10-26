// TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
// Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
// Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at https://opensource.org/licenses/MIT
// Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
// an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.

package rollback

import (
	"context"
	"errors"
	"fmt"

	"github.com/go-redis/redis/v8"
)

// A batch stays far below the 1GB query buffer of redis, tendisssd and tendisplus.
const (
	pipeBatchCmds  = 1000
	pipeBatchBytes = 16 << 20
)

// pipeExecer sends one batch and returns each command's error reply, nil for a normal reply.
// An error means the batch did not complete: the instance ran some prefix of it, replies unseen.
type pipeExecer interface {
	execBatch(cmds [][]string) ([]error, error)
}

// redisPipe sends a batch as one pipeline. Batches go one after another and the next is only
// sent once every reply of the last is in, so pooled connections keep the order too.
type redisPipe struct {
	cli *redis.Client
}

func (r redisPipe) execBatch(cmds [][]string) ([]error, error) {
	ctx := context.Background()
	pipe := r.cli.Pipeline()
	for _, args := range cmds {
		cmd := make([]interface{}, len(args))
		for i, arg := range args {
			cmd[i] = arg
		}
		pipe.Do(ctx, cmd...)
	}
	results, _ := pipe.Exec(ctx)
	if len(results) != len(cmds) {
		return nil, fmt.Errorf("pipeline returned %d results for %d commands", len(results), len(cmds))
	}
	replies := make([]error, len(cmds))
	for i, res := range results {
		err := res.Err()
		if err == nil || err == redis.Nil {
			continue
		}
		var reply redis.Error
		if !errors.As(err, &reply) {
			return nil, err
		}
		replies[i] = err
	}
	return replies, nil
}

// inFlightError is a failure while a batch was out: commands after a failed one may have run,
// so the instance may hold writes past a hole.
type inFlightError struct {
	err error
}

func (e *inFlightError) Error() string { return e.err.Error() }

func (e *inFlightError) Unwrap() error { return e.err }

// failedInFlight tells whether err left the instance with writes past a failed command.
func failedInFlight(err error) bool {
	var e *inFlightError
	return errors.As(err, &e)
}

// commandPipe sends commands in order, a batch at a time. onReply sees each command with its
// error reply once the batch is back; returning an error stops the pipe.
type commandPipe struct {
	exec    pipeExecer
	onReply func(args []string, reply error) error
	cmds    [][]string
	bytes   int
}

func (p *commandPipe) add(args []string) error {
	p.cmds = append(p.cmds, args)
	for _, arg := range args {
		p.bytes += len(arg)
	}
	if len(p.cmds) >= pipeBatchCmds || p.bytes >= pipeBatchBytes {
		return p.flush()
	}
	return nil
}

// flush sends what is queued. Its errors are inFlightErrors.
func (p *commandPipe) flush() error {
	if len(p.cmds) == 0 {
		return nil
	}
	cmds := p.cmds
	p.cmds, p.bytes = nil, 0
	replies, err := p.exec.execBatch(cmds)
	if err != nil {
		return &inFlightError{fmt.Errorf("batch of %d commands broke off: %v", len(cmds), err)}
	}
	for i, args := range cmds {
		if err = p.onReply(args, replies[i]); err != nil {
			return &inFlightError{err}
		}
	}
	return nil
}

// splitArgs splits a line the way redis-cli does (sdssplitargs), undoing tredisbinlog's
// sdscatrepr: double quotes with \xHH, \n, \r, \t, \b, \a and \<c> escapes, single quotes with
// \', and bare words, which only end at a space, \n, \r or \t. A quote may start mid-word; a
// closing quote must end the word. ok is false
// on unbalanced quotes, where redis-cli prints "Invalid argument(s)" and sends nothing.
func splitArgs(line string) (args []string, ok bool) {
	i, n := 0, len(line)
	isSpace := func(c byte) bool { return c == ' ' || c == '\n' || c == '\r' || c == '\t' || c == '\v' || c == '\f' }
	for {
		for i < n && isSpace(line[i]) {
			i++
		}
		if i >= n {
			return args, true
		}
		var cur []byte
		inq, insq := false, false
		for done := false; !done; {
			switch {
			case inq:
				switch {
				case i >= n:
					return nil, false
				case line[i] == '\\' && i+3 < n && line[i+1] == 'x' && isHex(line[i+2]) && isHex(line[i+3]):
					cur = append(cur, hexVal(line[i+2])<<4|hexVal(line[i+3]))
					i += 3
				case line[i] == '\\' && i+1 < n:
					i++
					switch c := line[i]; c {
					case 'n':
						cur = append(cur, '\n')
					case 'r':
						cur = append(cur, '\r')
					case 't':
						cur = append(cur, '\t')
					case 'b':
						cur = append(cur, '\b')
					case 'a':
						cur = append(cur, '\a')
					default:
						cur = append(cur, c)
					}
				case line[i] == '"':
					if i+1 < n && !isSpace(line[i+1]) {
						return nil, false
					}
					done = true
				default:
					cur = append(cur, line[i])
				}
			case insq:
				switch {
				case i >= n:
					return nil, false
				case line[i] == '\\' && i+1 < n && line[i+1] == '\'':
					i++
					cur = append(cur, '\'')
				case line[i] == '\'':
					if i+1 < n && !isSpace(line[i+1]) {
						return nil, false
					}
					done = true
				default:
					cur = append(cur, line[i])
				}
			default:
				switch {
				case i >= n || line[i] == ' ' || line[i] == '\n' || line[i] == '\r' || line[i] == '\t':
					done = true
				case line[i] == '"':
					inq = true
				case line[i] == '\'':
					insq = true
				default:
					cur = append(cur, line[i])
				}
			}
			if i < n {
				i++
			}
		}
		args = append(args, string(cur))
	}
}

func isHex(c byte) bool {
	return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F')
}

func hexVal(c byte) byte {
	switch {
	case c >= '0' && c <= '9':
		return c - '0'
	case c >= 'a' && c <= 'f':
		return c - 'a' + 10
	default:
		return c - 'A' + 10
	}
}

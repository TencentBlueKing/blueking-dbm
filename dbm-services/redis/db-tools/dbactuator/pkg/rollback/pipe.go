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
	"time"

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

// timedExec reports how long each batch took, telling the time spent waiting on the instance
// apart from the decoding that feeds the pipe.
type timedExec struct {
	exec    pipeExecer
	onBatch func(time.Duration)
}

func (t timedExec) execBatch(cmds [][]string) ([]error, error) {
	start := time.Now()
	replies, err := t.exec.execBatch(cmds)
	t.onBatch(time.Since(start))
	return replies, err
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

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

package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sync"
	"time"
)

const maxRememberedPushes = 64

type appStats struct {
	mu sync.Mutex

	dumpPath string
	dumpFile *os.File

	getProbeConfig int
	heartbeat      int
	push           int
	redisCmds      map[string]int
	lastPushes     []json.RawMessage
}

type statsView struct {
	GetProbeConfig int            `json:"get_probe_config"`
	Heartbeat      int            `json:"heartbeat"`
	Push           int            `json:"push"`
	RedisCmds      map[string]int `json:"redis_cmds"`
}

func newAppStats(dumpPath string) *appStats {
	return &appStats{
		dumpPath:   dumpPath,
		redisCmds:  map[string]int{},
		lastPushes: make([]json.RawMessage, 0, maxRememberedPushes),
	}
}

func (s *appStats) openDump() error {
	if s.dumpPath == "" {
		return nil
	}
	if dir := filepath.Dir(s.dumpPath); dir != "" && dir != "." {
		if err := os.MkdirAll(dir, 0o755); err != nil {
			return err
		}
	}
	f, err := os.OpenFile(s.dumpPath, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0o644)
	if err != nil {
		return err
	}
	s.dumpFile = f
	return nil
}

func (s *appStats) closeDump() {
	if s.dumpFile != nil {
		_ = s.dumpFile.Close()
	}
}

func (s *appStats) incGetProbeConfig() {
	s.mu.Lock()
	s.getProbeConfig++
	s.mu.Unlock()
}

func (s *appStats) incHeartbeat() {
	s.mu.Lock()
	s.heartbeat++
	s.mu.Unlock()
}

func (s *appStats) incRedis(cmd string) {
	s.mu.Lock()
	s.redisCmds[cmd]++
	s.mu.Unlock()
}

func (s *appStats) recordPush(payload []byte) {
	copied := append([]byte(nil), payload...)
	s.mu.Lock()
	defer s.mu.Unlock()
	s.push++
	s.lastPushes = append(s.lastPushes, json.RawMessage(copied))
	if len(s.lastPushes) > maxRememberedPushes {
		s.lastPushes = s.lastPushes[len(s.lastPushes)-maxRememberedPushes:]
	}
	if s.dumpFile == nil {
		return
	}
	rec := struct {
		TS      string          `json:"ts"`
		Payload json.RawMessage `json:"payload"`
	}{
		TS:      time.Now().UTC().Format(time.RFC3339Nano),
		Payload: copied,
	}
	enc := json.NewEncoder(s.dumpFile)
	_ = enc.Encode(rec)
}

func (s *appStats) snapshot() statsView {
	s.mu.Lock()
	defer s.mu.Unlock()
	cmds := make(map[string]int, len(s.redisCmds))
	for k, v := range s.redisCmds {
		cmds[k] = v
	}
	return statsView{
		GetProbeConfig: s.getProbeConfig,
		Heartbeat:      s.heartbeat,
		Push:           s.push,
		RedisCmds:      cmds,
	}
}

func (s *appStats) lastPayloads() []json.RawMessage {
	s.mu.Lock()
	defer s.mu.Unlock()
	out := make([]json.RawMessage, len(s.lastPushes))
	copy(out, s.lastPushes)
	return out
}

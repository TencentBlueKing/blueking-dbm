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
	"bufio"
	"fmt"
	"io"
	"net"
	"strconv"
	"strings"
)

const redisInfoBody = `# Server
redis_version:7.0.0
uptime_in_seconds:100

# Clients
connected_clients:1
rejected_connections:0

# Memory
used_memory_human:1.00M
mem_fragmentation_ratio:1.00

# Stats
total_error_replies:0
sync_full:0
sync_partial_err:0

# Replication
role:master
connected_slaves:0

# Keyspace
db0:keys=1,expires=0,avg_ttl=0
`

func startRedis(addr string, st *appStats) (func(), error) {
	lis, err := net.Listen("tcp", addr)
	if err != nil {
		return nil, err
	}
	done := make(chan struct{})
	go acceptRedis(lis, st, done)
	return func() {
		_ = lis.Close()
		<-done
	}, nil
}

func acceptRedis(lis net.Listener, st *appStats, done chan struct{}) {
	defer close(done)
	for {
		conn, err := lis.Accept()
		if err != nil {
			return
		}
		go serveRedisConn(conn, st)
	}
}

func serveRedisConn(conn net.Conn, st *appStats) {
	defer conn.Close()
	r := bufio.NewReader(conn)
	for {
		args, err := readRESPCommand(r)
		if err != nil {
			return
		}
		if len(args) == 0 {
			continue
		}
		cmd := strings.ToUpper(args[0])
		st.incRedis(cmd)
		if !writeRedisReply(conn, cmd) {
			return
		}
	}
}

func writeRedisReply(w io.Writer, cmd string) bool {
	switch cmd {
	case "PING":
		_, _ = io.WriteString(w, "+PONG\r\n")
	case "AUTH":
		_, _ = io.WriteString(w, "+OK\r\n")
	case "HELLO":
		_, _ = io.WriteString(w, "-ERR unknown command 'HELLO'\r\n")
	case "INFO":
		writeRESPBulk(w, redisInfoBody)
	case "QUIT":
		_, _ = io.WriteString(w, "+OK\r\n")
		return false
	default:
		_, _ = io.WriteString(w, "+OK\r\n")
	}
	return true
}

func readRESPCommand(r *bufio.Reader) ([]string, error) {
	prefix, err := r.ReadByte()
	if err != nil {
		return nil, err
	}
	if prefix != '*' {
		return nil, fmt.Errorf("expected RESP array")
	}
	n, err := readRESPIntLine(r)
	if err != nil {
		return nil, err
	}
	args := make([]string, 0, n)
	for i := 0; i < n; i++ {
		s, err := readRESPBulk(r)
		if err != nil {
			return nil, err
		}
		args = append(args, s)
	}
	return args, nil
}

func readRESPBulk(r *bufio.Reader) (string, error) {
	prefix, err := r.ReadByte()
	if err != nil {
		return "", err
	}
	if prefix != '$' {
		return "", fmt.Errorf("expected RESP bulk string")
	}
	n, err := readRESPIntLine(r)
	if err != nil {
		return "", err
	}
	if n < 0 {
		return "", nil
	}
	buf := make([]byte, n+2)
	if _, err := io.ReadFull(r, buf); err != nil {
		return "", err
	}
	return string(buf[:n]), nil
}

func readRESPIntLine(r *bufio.Reader) (int, error) {
	line, err := r.ReadString('\n')
	if err != nil {
		return 0, err
	}
	line = strings.TrimSpace(line)
	return strconv.Atoi(line)
}

func writeRESPBulk(w io.Writer, body string) {
	_, _ = fmt.Fprintf(w, "$%d\r\n%s\r\n", len(body), body)
}

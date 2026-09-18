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

package haredis

import (
	"bufio"
	"crypto/md5"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"sort"
	"strconv"
	"strings"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
)

const (
	defaultTwemproxyAdminDialTimeout = 10 * time.Second
	defaultTwemproxyAdminDeadline    = 5 * time.Second

	twemproxyGetServersCmd    = "get nosqlproxy servers"
	twemproxyChangeBackendCmd = "change nosqlproxy %s %s"
)

// TwemproxyServerMap maps a hash segment to its backend instance address.
type TwemproxyServerMap map[string]string

// ByteArray returns a stable JSON encoding of "seg|addr" pairs, sorted descending.
func (m TwemproxyServerMap) ByteArray() []byte {
	segList := make([]string, 0, len(m))
	for seg, addr := range m {
		segList = append(segList, fmt.Sprintf("%s|%s", seg, addr))
	}
	sort.Slice(segList, func(i, j int) bool {
		return segList[i] > segList[j]
	})
	x, _ := json.Marshal(segList)
	return x
}

// String returns a stable JSON encoding of "seg|addr" pairs, sorted descending.
func (m TwemproxyServerMap) String() string {
	return string(m.ByteArray())
}

// MD5String returns the hex MD5 of String().
func (m TwemproxyServerMap) MD5String() string {
	return fmt.Sprintf("%x", md5.Sum(m.ByteArray()))
}

// TwemproxyAdminClient talks to a twemproxy admin port using a
// line-oriented protocol (not Redis RESP).
type TwemproxyAdminClient struct {
	opts options
}

func defaultTwemproxyAdminOptions() []Option {
	return []Option{
		OptionDialTimeout(defaultTwemproxyAdminDialTimeout),
		OptionReadWriteTimeout(defaultTwemproxyAdminDeadline),
	}
}

// NewTwemproxyAdminClient creates a twemproxy admin client.
// Default timeouts are applied first and can be overridden by opts.
// no need to close the client.
func NewTwemproxyAdminClient(opts ...Option) (*TwemproxyAdminClient, error) {
	cli := &TwemproxyAdminClient{}
	allOpts := append(defaultTwemproxyAdminOptions(), opts...)
	for _, opt := range allOpts {
		if err := opt.apply(&cli.opts); err != nil {
			return nil, err
		}
	}

	if cli.opts.ip == "" {
		return nil, gerrors.New(gerrors.InvalidParameter, "twemproxy ip is empty")
	}
	if cli.opts.port <= 0 {
		return nil, gerrors.Newf(gerrors.InvalidParameter, "invalid twemproxy port: %d", cli.opts.port)
	}

	return cli, nil
}

// addr returns host:port suitable for net.Dial, including bracketed IPv6.
func (c *TwemproxyAdminClient) addr() string {
	return net.JoinHostPort(c.opts.ip, strconv.Itoa(c.opts.port))
}

func (c *TwemproxyAdminClient) deadline() time.Duration {
	d := c.opts.readTimeout
	if c.opts.writeTimeout > d {
		d = c.opts.writeTimeout
	}
	return d
}

// connectAndWrite connects to the twemproxy admin port and writes the command.
func (c *TwemproxyAdminClient) connectAndWrite(cmd string) (net.Conn, error) {
	nc, err := net.DialTimeout("tcp", c.addr(), c.opts.dialTimeout)
	if err != nil {
		return nil, err
	}
	_ = nc.SetDeadline(time.Now().Add(c.deadline()))
	if _, err = nc.Write([]byte(cmd)); err != nil {
		_ = nc.Close()
		return nil, err
	}
	return nc, nil
}

// GetServerMap sends "get nosqlproxy servers" and parses "addr app seg weight".
func (c *TwemproxyAdminClient) GetServerMap() (TwemproxyServerMap, error) {
	nc, err := c.connectAndWrite(twemproxyGetServersCmd)
	if err != nil {
		return nil, err
	}
	defer nc.Close()

	reader := bufio.NewReader(nc)
	segs := make(TwemproxyServerMap)
	for {
		line, _, err := reader.ReadLine()
		if err != nil {
			if err == io.EOF {
				break
			}
			return nil, err
		}
		strws := strings.Split(string(line), " ")
		if len(strws) == 4 {
			segs[strws[2]] = strws[0]
		}
	}
	return segs, nil
}

// ChangeBackend sends "change nosqlproxy $from $to" and reads one response line.
func (c *TwemproxyAdminClient) ChangeBackend(from, to string) (string, error) {
	nc, err := c.connectAndWrite(fmt.Sprintf(twemproxyChangeBackendCmd, from, to))
	if err != nil {
		return "nil", err
	}
	defer nc.Close()

	return bufio.NewReader(nc).ReadString('\n')
}

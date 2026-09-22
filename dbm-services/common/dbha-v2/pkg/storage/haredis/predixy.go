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
	"context"
	"crypto/md5"
	"encoding/json"
	"fmt"
	"sort"
	"strconv"
	"strings"
)

// PredixyServer is one backend entry from Predixy INFO Servers.
type PredixyServer struct {
	Server        string `json:"server"`
	Role          string `json:"role,omitempty"`
	Group         string `json:"group,omitempty"`
	DC            string `json:"dc,omitempty"`
	CurrentIsFail int    `json:"current_is_fail"`
	Connections   int    `json:"connections,omitempty"`
	Connect       int    `json:"connect,omitempty"`
	Requests      uint64 `json:"requests,omitempty"`
	Responses     uint64 `json:"responses,omitempty"`
	SendBytes     uint64 `json:"send_bytes,omitempty"`
	RecvBytes     uint64 `json:"recv_bytes,omitempty"`
}

// PredixyServerList is a parsed INFO Servers section.
type PredixyServerList []*PredixyServer

// ParsePredixyInfoServers parses the INFO Servers section returned by Predixy.
func ParsePredixyInfoServers(info string) PredixyServerList {
	rets := make(PredixyServerList, 0)
	item := &PredixyServer{}

	flush := func() {
		if item.Server == "" {
			return
		}
		rets = append(rets, item)
		item = &PredixyServer{}
	}

	for _, line := range strings.Split(info, "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			flush()
			continue
		}
		if strings.HasPrefix(line, "#") {
			continue
		}

		kv := strings.SplitN(line, ":", 2)
		if len(kv) < 2 {
			continue
		}
		key, value := kv[0], strings.TrimSpace(kv[1])
		switch key {
		case "Server":
			item.Server = value
		case "Role":
			item.Role = value
		case "Group":
			item.Group = value
		case "DC":
			item.DC = value
		case "CurrentIsFail":
			item.CurrentIsFail, _ = strconv.Atoi(value)
		case "Connections":
			item.Connections, _ = strconv.Atoi(value)
		case "Connect":
			item.Connect, _ = strconv.Atoi(value)
		case "Requests":
			item.Requests, _ = strconv.ParseUint(value, 10, 64)
		case "Responses":
			item.Responses, _ = strconv.ParseUint(value, 10, 64)
		case "SendBytes":
			item.SendBytes, _ = strconv.ParseUint(value, 10, 64)
		case "RecvBytes":
			item.RecvBytes, _ = strconv.ParseUint(value, 10, 64)
		}
	}
	flush()
	return rets
}

// MD5String returns the hex MD5 of sorted "server|current_is_fail" pairs.
func (l PredixyServerList) MD5String() string {
	pairs := make([]string, 0, len(l))
	for _, item := range l {
		if item == nil {
			continue
		}
		pairs = append(pairs, fmt.Sprintf("%s|%d", item.Server, item.CurrentIsFail))
	}
	sort.Strings(pairs)

	out, _ := json.Marshal(pairs)
	return fmt.Sprintf("%x", md5.Sum(out))
}

// GetPredixyInfoServers connects to a Predixy data port and runs INFO Servers.
func GetPredixyInfoServers(cli *Client) (PredixyServerList, error) {
	if cli == nil {
		return nil, fmt.Errorf("nil redis client")
	}

	ctx, cancel := context.WithTimeout(context.Background(), cli.opts.readTimeout)
	defer cancel()

	raw, err := cli.DB().Info(ctx, "servers").Result()
	if err != nil {
		return nil, err
	}
	return ParsePredixyInfoServers(raw), nil
}

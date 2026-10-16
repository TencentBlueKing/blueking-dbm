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

	"dbm-services/common/dbha-v2/pkg/gerrors"
)

// PredixyServer is one backend entry from Predixy INFO Servers.
type PredixyServer struct {
	Server string `json:"server"`
	// Slot is the raw INFO Servers "Slots" value. Segments inside it are already ascending.
	// It may be empty when the running Predixy omits it, and an empty value still participates in the backend MD5.
	Slot          string `json:"slot,omitempty"`
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
		switch strings.ToLower(key) {
		case "server":
			item.Server = value
		case "slots", "slot":
			item.Slot = value
		case "role":
			item.Role = value
		case "group":
			item.Group = value
		case "dc":
			item.DC = value
		case "currentisfail":
			item.CurrentIsFail, _ = strconv.Atoi(value)
		case "connections":
			item.Connections, _ = strconv.Atoi(value)
		case "connect":
			item.Connect, _ = strconv.Atoi(value)
		case "requests":
			item.Requests, _ = strconv.ParseUint(value, 10, 64)
		case "responses":
			item.Responses, _ = strconv.ParseUint(value, 10, 64)
		case "sendbytes":
			item.SendBytes, _ = strconv.ParseUint(value, 10, 64)
		case "recvbytes":
			item.RecvBytes, _ = strconv.ParseUint(value, 10, 64)
		}
	}
	flush()
	return rets
}

// backendByteArray returns a stable JSON encoding of "slots|server" pairs, sorted descending.
// Slots is hashed as the raw string. Segments inside it are already ascending.
// A missing Slots value is kept as an empty string so every server still contributes.
func (l PredixyServerList) backendByteArray() []byte {
	pairs := make([]string, 0, len(l))
	for _, item := range l {
		if item == nil {
			continue
		}
		pairs = append(pairs, fmt.Sprintf("%s|%s", item.Slot, item.Server))
	}
	sort.Slice(pairs, func(i, j int) bool {
		return pairs[i] > pairs[j]
	})
	out, _ := json.Marshal(pairs)
	return out
}

// BackendString returns the stable encoding hashed by MD5String.
func (l PredixyServerList) BackendString() string {
	return string(l.backendByteArray())
}

// MD5String returns the hex MD5 of sorted "slots|server" pairs.
// Slots is the raw string and may be empty when it is omitted.
// CurrentIsFail is not part of the digest.
// cluster show routing and the PredixyTendisplusInstance switch both use this value.
func (l PredixyServerList) MD5String() string {
	return fmt.Sprintf("%x", md5.Sum(l.backendByteArray()))
}

// PredixyAdminChange runs "admin change <from> <to>" on an authenticated Predixy client.
// The client must be logged in with the predixy admin password.
// A nil error means the reply, after trimming space and uppercasing, is exactly "OK".
func PredixyAdminChange(cli *Client, from, to string) error {
	if cli == nil {
		return gerrors.New(gerrors.InvalidParameter, "nil redis client")
	}

	ctx, cancel := context.WithTimeout(context.Background(), cli.opts.readTimeout)
	defer cancel()

	raw, err := cli.DB().Do(ctx, "admin", "change", from, to).Result()
	if err != nil {
		return err
	}

	rsp := ReplyString(raw)
	if strings.ToUpper(strings.TrimSpace(rsp)) != RedisReplyOK {
		return gerrors.Newf(gerrors.Failure, "predixy admin change response is not %s: %s", RedisReplyOK, rsp)
	}
	return nil
}

// GetPredixyInfoServers connects to a Predixy data port and runs INFO Servers.
func GetPredixyInfoServers(cli *Client) (PredixyServerList, error) {
	if cli == nil {
		return nil, gerrors.New(gerrors.InvalidParameter, "nil redis client")
	}

	ctx, cancel := context.WithTimeout(context.Background(), cli.opts.readTimeout)
	defer cancel()

	raw, err := cli.DB().Info(ctx, "servers").Result()
	if err != nil {
		return nil, err
	}
	return ParsePredixyInfoServers(raw), nil
}

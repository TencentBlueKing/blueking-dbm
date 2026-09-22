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
	"fmt"
	"strings"
)

// ClusterNode is one line from CLUSTER NODES.
type ClusterNode struct {
	NodeID    string `json:"node_id"`
	Address   string `json:"address"`
	Flags     string `json:"flags"`
	Role      string `json:"role"`
	MasterID  string `json:"master_id,omitempty"`
	LinkState string `json:"link_state"`
	Slots     string `json:"slots,omitempty"`
}

// ParseClusterNodes parses CLUSTER NODES output.
func ParseClusterNodes(raw string) []ClusterNode {
	nodes := make([]ClusterNode, 0)
	for _, line := range strings.Split(raw, "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}

		fields := strings.Fields(line)
		if len(fields) < 8 {
			continue
		}

		addr := strings.Split(fields[1], "@")[0]
		masterID := fields[3]
		if masterID == "-" {
			masterID = ""
		}

		slots := ""
		if len(fields) > 8 {
			slots = strings.Join(fields[8:], " ")
		}

		nodes = append(nodes, ClusterNode{
			NodeID:    fields[0],
			Address:   addr,
			Flags:     fields[2],
			Role:      clusterNodeRole(fields[2], masterID, slots),
			MasterID:  masterID,
			LinkState: fields[7],
			Slots:     slots,
		})
	}
	return nodes
}

func clusterNodeRole(flags, masterID, slots string) string {
	for _, flag := range strings.Split(flags, ",") {
		switch flag {
		case "master":
			return "master"
		case "slave":
			return "slave"
		}
	}
	if masterID != "" {
		return "slave"
	}
	if slots != "" {
		return "master"
	}
	return ""
}

// GetClusterNodes connects to a redis-compatible node and runs CLUSTER NODES.
func GetClusterNodes(cli *Client) ([]ClusterNode, error) {
	if cli == nil {
		return nil, fmt.Errorf("nil redis client")
	}

	ctx, cancel := context.WithTimeout(context.Background(), cli.opts.readTimeout)
	defer cancel()

	raw, err := cli.DB().ClusterNodes(ctx).Result()
	if err != nil {
		return nil, err
	}
	return ParseClusterNodes(raw), nil
}

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
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"reflect"
	"time"

	"dbm-services/common/dbha-v2/pkg/proto"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"google.golang.org/grpc/status"
)

var errNoHaServersTarget = errors.New("list-ha-servers needs admin-grpc-addr or admin-web-addr")

const (
	haServersCallTimeout = 10 * time.Second
	haServersHTTPPath    = "/api/admin/meta/ha-servers"
)

// haServerView is the protocol-neutral form used to compare gRPC and HTTP results.
type haServerView struct {
	Role      string   `json:"role"`
	ID        string   `json:"id"`
	IPs       []string `json:"ips"`
	StartTime string   `json:"start_time"`
	UpdatedAt string   `json:"updated_at"`
	Uptime    string   `json:"uptime"`
}

type grpcHaServersResult struct {
	GRPCCode string         `json:"grpc_code"`
	Code     string         `json:"code"`
	Errmsg   string         `json:"errmsg"`
	Servers  []haServerView `json:"servers"`
	IPs      []string       `json:"ips"`
}

type httpHaServersResult struct {
	Status  int            `json:"status"`
	Code    int            `json:"code"`
	Message string         `json:"message"`
	RawData string         `json:"raw_data,omitempty"`
	Servers []haServerView `json:"servers"`
	IPs     []string       `json:"ips"`
}

type haServersComparison struct {
	GRPC       *grpcHaServersResult `json:"grpc,omitempty"`
	HTTP       *httpHaServersResult `json:"http,omitempty"`
	Consistent *bool                `json:"consistent,omitempty"`
}

type haServersEnvelope struct {
	Data    json.RawMessage `json:"data"`
	Code    int             `json:"code"`
	Message string          `json:"message"`
}

type haServersData struct {
	Servers []haServerView `json:"servers"`
	IPs     []string       `json:"ips"`
}

// listHaServers calls the requested protocols and prints one comparison JSON line to stdout.
func listHaServers(grpcAddr, webAddr string) error {
	result, err := collectHaServers(grpcAddr, webAddr)
	if err != nil {
		return err
	}

	encoded, err := json.Marshal(result)
	if err != nil {
		return err
	}
	fmt.Println(string(encoded))

	return nil
}

// collectHaServers calls the requested protocols. consistent is set only when both are called.
func collectHaServers(grpcAddr, webAddr string) (*haServersComparison, error) {
	if grpcAddr == "" && webAddr == "" {
		return nil, errNoHaServersTarget
	}

	ctx, cancel := context.WithTimeout(context.Background(), haServersCallTimeout)
	defer cancel()

	result := &haServersComparison{}
	if grpcAddr != "" {
		grpcResult, err := callListHaServersGRPC(ctx, grpcAddr)
		if err != nil {
			return nil, err
		}
		result.GRPC = grpcResult
	}

	if webAddr != "" {
		httpResult, err := callListHaServersHTTP(ctx, webAddr)
		if err != nil {
			return nil, err
		}
		result.HTTP = httpResult
	}

	if result.GRPC != nil && result.HTTP != nil {
		consistent := reflect.DeepEqual(result.GRPC.Servers, result.HTTP.Servers) &&
			reflect.DeepEqual(result.GRPC.IPs, result.HTTP.IPs)
		result.Consistent = &consistent
	}

	return result, nil
}

func callListHaServersGRPC(ctx context.Context, addr string) (*grpcHaServersResult, error) {
	conn, err := grpc.NewClient(addr, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		return nil, err
	}
	defer conn.Close()

	resp, err := proto.NewAdminServiceClient(conn).ListHaServers(ctx, &proto.ListHaServersRequest{})
	result := &grpcHaServersResult{GRPCCode: status.Code(err).String(), Servers: []haServerView{}, IPs: []string{}}
	if err != nil {
		log.Printf("admin grpc list_ha_servers failed, grpc_code: %s, errmsg: %s", result.GRPCCode, err)
		return result, nil
	}

	result.Code = resp.GetCode().String()
	result.Errmsg = resp.GetErrmsg()
	result.IPs = append(result.IPs, resp.GetIps()...)
	for _, s := range resp.GetServers() {
		result.Servers = append(result.Servers, haServerView{
			Role: s.GetRole(), ID: s.GetId(), IPs: append([]string{}, s.GetIps()...),
			StartTime: s.GetStartTime(), UpdatedAt: s.GetUpdatedAt(), Uptime: s.GetUptime(),
		})
	}
	log.Printf("admin grpc list_ha_servers, grpc_code: OK, code: %s, servers: %d", result.Code, len(result.Servers))

	return result, nil
}

func callListHaServersHTTP(ctx context.Context, addr string) (*httpHaServersResult, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, "http://"+addr+haServersHTTPPath, nil)
	if err != nil {
		return nil, err
	}

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	result := &httpHaServersResult{Status: resp.StatusCode, Servers: []haServerView{}, IPs: []string{}}
	var envelope haServersEnvelope
	if err := json.Unmarshal(body, &envelope); err != nil {
		result.RawData = string(body)
		return result, nil
	}
	result.Code, result.Message = envelope.Code, envelope.Message

	var data haServersData
	if err := json.Unmarshal(envelope.Data, &data); err != nil {
		result.RawData = string(envelope.Data)
		return result, nil
	}
	if data.Servers != nil {
		result.Servers = data.Servers
	}
	if data.IPs != nil {
		result.IPs = data.IPs
	}
	log.Printf("admin http list_ha_servers, status: %d, code: %d, servers: %d",
		result.Status, result.Code, len(result.Servers))

	return result, nil
}

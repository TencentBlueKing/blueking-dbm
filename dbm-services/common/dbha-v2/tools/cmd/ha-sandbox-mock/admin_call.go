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
	"log"
	"time"

	"dbm-services/common/dbha-v2/pkg/proto"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

const adminGRPCCallTimeout = 5 * time.Second

func callAdminGRPC(addr string) error {
	ctx, cancel := context.WithTimeout(context.Background(), adminGRPCCallTimeout)
	defer cancel()

	conn, err := grpc.NewClient(addr, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		return err
	}
	defer conn.Close()

	cli := proto.NewAdminServiceClient(conn)
	hb, err := cli.Heartbeat(ctx, &proto.HeartbeatRequest{ClientID: "ha-sandbox-mock"})
	if err != nil {
		log.Printf("admin grpc heartbeat failed, errmsg: %s", err)
		return err
	}
	log.Printf("admin grpc heartbeat, grpc_code: OK, code: %d", hb.GetCode())

	pc, err := cli.GetProbeConfig(ctx, &proto.ProbeConfigRequest{
		BkCloudId: 0,
		Ip:        "127.0.0.1",
		ClientID:  "ha-sandbox-mock",
	})
	if err != nil {
		log.Printf("admin grpc get_probe_config failed, errmsg: %s", err)
		return err
	}
	log.Printf("admin grpc get_probe_config, grpc_code: OK, code: %s", pc.GetCode().String())
	return nil
}

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

// Package main is a loopback mock of etcd gRPC and MySQL wire protocol for dbha-v2 HA sandbox tests.
package main

import (
	"flag"
	"log"
	"os"
	"os/signal"
	"syscall"
)

type mockConfig struct {
	etcdAddr      string
	mysqlAddr     string
	httpAddr      string
	adminGRPCAddr string
	adminWebAddr  string
	listHaServers bool
}

func main() {
	cfg := parseFlags()
	if err := run(cfg); err != nil {
		log.Printf("ha sandbox mock stopped, errmsg: %s", err)
		os.Exit(1)
	}
}

func parseFlags() mockConfig {
	cfg := mockConfig{}
	flag.StringVar(&cfg.etcdAddr, "etcd-addr", "127.0.0.1:12379", "etcd gRPC mock listen address")
	flag.StringVar(&cfg.mysqlAddr, "mysql-addr", "127.0.0.1:23306", "MySQL protocol mock listen address")
	flag.StringVar(&cfg.httpAddr, "http-addr", "127.0.0.1:18091", "HTTP health listen address")
	flag.StringVar(&cfg.adminGRPCAddr, "admin-grpc-addr", "",
		"if set, call Admin Heartbeat and GetProbeConfig then exit")
	flag.StringVar(&cfg.adminWebAddr, "admin-web-addr", "",
		"Admin web address used by --list-ha-servers for GET /api/admin/meta/ha-servers")
	flag.BoolVar(&cfg.listHaServers, "list-ha-servers", false,
		"call Admin ListHaServers (gRPC) and the HTTP meta API, print one comparison JSON line, then exit")
	flag.Parse()
	return cfg
}

func run(cfg mockConfig) error {
	if cfg.adminGRPCAddr != "" && !cfg.listHaServers {
		return callAdminGRPC(cfg.adminGRPCAddr)
	}

	if cfg.listHaServers {
		return listHaServers(cfg.adminGRPCAddr, cfg.adminWebAddr)
	}

	ctl := newDepControl(cfg.etcdAddr, cfg.mysqlAddr)
	defer ctl.stopAll()
	if err := ctl.startEtcd(); err != nil {
		return err
	}
	if err := ctl.startMySQL(); err != nil {
		return err
	}

	httpLn, err := startHTTPHealth(cfg.httpAddr, cfg.etcdAddr, cfg.mysqlAddr, ctl)
	if err != nil {
		return err
	}
	defer httpLn.Close()
	logHTTPReady(cfg.httpAddr)

	sigC := make(chan os.Signal, 1)
	signal.Notify(sigC, syscall.SIGINT, syscall.SIGTERM)
	<-sigC
	log.Printf("ha sandbox mock shutting down")
	return nil
}

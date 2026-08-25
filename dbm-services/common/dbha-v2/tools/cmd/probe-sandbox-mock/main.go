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

// Package main is a sandbox mock of admin, receiver, and redis for probe full-path tests.
package main

import (
	"flag"
	"log"
	"os"
	"os/signal"
	"syscall"
)

func main() {
	cfg := parseFlags()
	if err := run(cfg); err != nil {
		log.Printf("sandbox mock stopped, errmsg: %s", err)
		os.Exit(1)
	}
}

func parseFlags() mockConfig {
	cfg := mockConfig{}
	flag.StringVar(&cfg.adminAddr, "admin-addr", "127.0.0.1:19001", "gRPC Admin listen address")
	flag.StringVar(&cfg.receiverAddr, "receiver-addr", "127.0.0.1:19100", "gRPC Receiver listen address")
	flag.StringVar(&cfg.redisAddr, "redis-addr", "127.0.0.1:16379", "Redis RESP listen address")
	flag.StringVar(&cfg.httpAddr, "http-addr", "127.0.0.1:18090", "HTTP stats listen address")
	flag.StringVar(&cfg.dumpPath, "dump", "/tmp/probe-sandbox/results/receiver.jsonl", "receiver payload dump file")
	flag.StringVar(&cfg.patchYAML, "patch-yaml", "", "patch gen-config YAML reporter to grpc and exit")
	flag.StringVar(&cfg.logPath, "log-path", "/tmp/probe-sandbox/logs/probe.log", "log.path written by -patch-yaml")
	flag.Parse()
	return cfg
}

func run(cfg mockConfig) error {
	if cfg.patchYAML != "" {
		return patchProbeYAML(cfg.patchYAML, cfg.receiverAddr, cfg.logPath)
	}

	st := newAppStats(cfg.dumpPath)
	stoppers, err := startServers(cfg, st)
	if err != nil {
		return err
	}
	defer stopAll(stoppers)

	log.Printf(
		"sandbox mock ready, admin: %s, receiver: %s, redis: %s, http: %s",
		cfg.adminAddr, cfg.receiverAddr, cfg.redisAddr, cfg.httpAddr,
	)

	sigC := make(chan os.Signal, 1)
	signal.Notify(sigC, syscall.SIGINT, syscall.SIGTERM)
	<-sigC
	log.Printf("sandbox mock shutting down")
	return nil
}

type mockConfig struct {
	adminAddr    string
	receiverAddr string
	redisAddr    string
	httpAddr     string
	dumpPath     string
	patchYAML    string
	logPath      string
}

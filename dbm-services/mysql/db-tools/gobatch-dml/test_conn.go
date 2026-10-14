//go:build ignore

// 连接探测小工具: 每隔 interval 新建一个 mysql 连接并执行 select version(), 总耗时超过 threshold 记录日志
// 用法: go run test_conn.go -dsn 'user:pass@tcp(1.2.3.4:3306)/?timeout=5s' [-interval 2s] [-threshold 100ms] [-v]
package main

import (
	"context"
	"database/sql"
	"flag"
	"fmt"
	"log"
	"net"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/go-sql-driver/mysql"
)

type probeResult struct {
	dial      time.Duration // dns + tcp 三次握手
	handshake time.Duration // mysql 协议握手 + 认证 (connect - dial)
	connect   time.Duration // 拿到可用连接的总耗时
	query     time.Duration // select version()
	total     time.Duration
	localAddr string
	version   string
	err       error
}

// 探测是串行的, 用全局变量把 dial 阶段的耗时带回 probe
const probeNet = "tcp-probe"

var curResult *probeResult

func init() {
	mysql.RegisterDialContext(probeNet, func(ctx context.Context, addr string) (net.Conn, error) {
		st := time.Now()
		var d net.Dialer
		c, err := d.DialContext(ctx, "tcp", addr)
		if curResult != nil {
			curResult.dial = time.Since(st)
			if c != nil {
				curResult.localAddr = c.LocalAddr().String()
			}
		}
		return c, err
	})
}

func probe(baseCfg *mysql.Config, timeout time.Duration) (r probeResult) {
	cfg := baseCfg.Clone()
	cfg.Net = probeNet
	curResult = &r
	defer func() { curResult = nil }()

	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	connector, err := mysql.NewConnector(cfg)
	if err != nil {
		r.err = fmt.Errorf("new connector: %w", err)
		return
	}
	db := sql.OpenDB(connector)
	defer db.Close()

	st := time.Now()
	defer func() { r.total = time.Since(st) }()

	conn, err := db.Conn(ctx)
	r.connect = time.Since(st)
	r.handshake = r.connect - r.dial
	if err != nil {
		r.err = fmt.Errorf("connect: %w", err)
		return
	}
	defer conn.Close()

	qst := time.Now()
	err = conn.QueryRowContext(ctx, "select version()").Scan(&r.version)
	r.query = time.Since(qst)
	if err != nil {
		r.err = fmt.Errorf("query: %w", err)
	}
	return
}

func main() {
	dsn := flag.String("dsn", "", "mysql dsn, e.g. user:pass@tcp(1.2.3.4:3306)/?timeout=5s")
	interval := flag.Duration("interval", 2*time.Second, "probe interval")
	threshold := flag.Duration("threshold", 100*time.Millisecond, "log when total cost exceeds this")
	verbose := flag.Bool("v", false, "log every probe")
	flag.Parse()

	if *dsn == "" {
		flag.Usage()
		os.Exit(1)
	}
	cfg, err := mysql.ParseDSN(*dsn)
	if err != nil {
		log.Fatalf("parse dsn failed: %v", err)
	}
	if cfg.Timeout == 0 {
		cfg.Timeout = 1 * time.Second
	}
	probeTimeout := cfg.Timeout + 5*time.Second

	log.SetFlags(log.LstdFlags | log.Lmicroseconds)
	log.Printf("start probe addr=%s user=%s interval=%s threshold=%s", cfg.Addr, cfg.User, *interval, *threshold)

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, os.Interrupt, syscall.SIGTERM)

	var rounds, slow, failed int
	var maxCost time.Duration
	ticker := time.NewTicker(*interval)
	defer ticker.Stop()

	for {
		r := probe(cfg, probeTimeout)
		rounds++
		if r.total > maxCost {
			maxCost = r.total
		}
		msg := fmt.Sprintf("total=%s dial=%s handshake=%s connect=%s query=%s local=%s version=%s",
			r.total, r.dial, r.handshake, r.connect, r.query, r.localAddr, r.version)
		switch {
		case r.err != nil:
			failed++
			log.Printf("[ERROR] %s err=%v", msg, r.err)
		case r.total > *threshold:
			slow++
			log.Printf("[SLOW] %s", msg)
		case *verbose:
			log.Printf("[OK] %s", msg)
		}

		select {
		case <-sig:
			log.Printf("summary: rounds=%d slow=%d failed=%d max=%s", rounds, slow, failed, maxCost)
			return
		case <-ticker.C:
		}
	}
}

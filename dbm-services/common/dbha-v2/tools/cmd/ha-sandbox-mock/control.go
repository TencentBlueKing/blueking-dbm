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
	"io"
	"log"
	"net"
	"net/http"
	"sync"

	"google.golang.org/grpc"
)

const (
	controlEtcdKVPath     = "/control/etcd/kv"
	controlEtcdStopPath   = "/control/etcd/stop"
	controlEtcdStartPath  = "/control/etcd/start"
	controlMySQLStopPath  = "/control/mysql/stop"
	controlMySQLStartPath = "/control/mysql/start"
	controlMaxBodyBytes   = 1 << 20
)

// depControl owns the etcd and MySQL mocks so each can be stopped and restarted on the same
// address independently. The etcd store survives restarts.
type depControl struct {
	mu         sync.Mutex
	etcdAddr   string
	mysqlAddr  string
	store      *etcdStore
	etcdSrv    *grpc.Server
	etcdLn     net.Listener
	mysqlLn    net.Listener
	mysqlConns map[net.Conn]struct{}
}

func newDepControl(etcdAddr, mysqlAddr string) *depControl {
	return &depControl{
		etcdAddr:   etcdAddr,
		mysqlAddr:  mysqlAddr,
		store:      newEtcdStore("http://" + etcdAddr),
		mysqlConns: map[net.Conn]struct{}{},
	}
}

func (c *depControl) startEtcd() error {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.etcdSrv != nil {
		return nil
	}

	srv, ln, err := serveEtcdStore(c.etcdAddr, c.store)
	if err != nil {
		return err
	}
	c.etcdSrv, c.etcdLn = srv, ln
	logEtcdReady(c.etcdAddr)

	return nil
}

func (c *depControl) stopEtcd() {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.etcdSrv == nil {
		return
	}

	c.etcdSrv.Stop()
	_ = c.etcdLn.Close()
	c.etcdSrv, c.etcdLn = nil, nil
	log.Printf("etcd mock stopped, addr: %s", c.etcdAddr)
}

func (c *depControl) startMySQL() error {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.mysqlLn != nil {
		return nil
	}

	ln, err := net.Listen("tcp", c.mysqlAddr)
	if err != nil {
		return err
	}
	c.mysqlLn = ln
	go c.acceptMySQL(ln)
	logMySQLReady(c.mysqlAddr)

	return nil
}

// stopMySQL closes the listener and every accepted connection, so pooled clients fail fast.
func (c *depControl) stopMySQL() {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.mysqlLn == nil {
		return
	}

	_ = c.mysqlLn.Close()
	c.mysqlLn = nil
	for conn := range c.mysqlConns {
		_ = conn.Close()
	}
	c.mysqlConns = map[net.Conn]struct{}{}
	log.Printf("mysql mock stopped, addr: %s", c.mysqlAddr)
}

func (c *depControl) stopAll() {
	c.stopEtcd()
	c.stopMySQL()
}

func (c *depControl) acceptMySQL(ln net.Listener) {
	for {
		conn, err := ln.Accept()
		if err != nil {
			return
		}

		c.mu.Lock()
		c.mysqlConns[conn] = struct{}{}
		c.mu.Unlock()

		go func() {
			handleMySQLConn(conn)
			c.mu.Lock()
			delete(c.mysqlConns, conn)
			c.mu.Unlock()
		}()
	}
}

// registerControlHandlers adds loopback-only test controls to mux.
func (c *depControl) registerControlHandlers(mux *http.ServeMux) {
	mux.HandleFunc(controlEtcdKVPath, c.handleEtcdKV)
	mux.HandleFunc(controlEtcdStopPath, c.postOnly(func() error { c.stopEtcd(); return nil }))
	mux.HandleFunc(controlEtcdStartPath, c.postOnly(c.startEtcd))
	mux.HandleFunc(controlMySQLStopPath, c.postOnly(func() error { c.stopMySQL(); return nil }))
	mux.HandleFunc(controlMySQLStartPath, c.postOnly(c.startMySQL))
}

func (c *depControl) postOnly(action func() error) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			w.WriteHeader(http.StatusMethodNotAllowed)
			return
		}

		if err := action(); err != nil {
			log.Printf("mock control failed, path: %s, errmsg: %s", r.URL.Path, err)
			w.WriteHeader(http.StatusInternalServerError)
			return
		}
		w.WriteHeader(http.StatusNoContent)
	}
}

// handleEtcdKV puts (PUT, body is the raw value) or deletes (DELETE) the key given by ?key=.
func (c *depControl) handleEtcdKV(w http.ResponseWriter, r *http.Request) {
	key := r.URL.Query().Get("key")
	if key == "" {
		w.WriteHeader(http.StatusBadRequest)
		return
	}

	switch r.Method {
	case http.MethodPut:
		value, err := io.ReadAll(io.LimitReader(r.Body, controlMaxBodyBytes))
		if err != nil {
			w.WriteHeader(http.StatusBadRequest)
			return
		}
		c.store.putRaw(key, value)
	case http.MethodDelete:
		c.store.deleteRaw(key)
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}

	log.Printf("mock etcd kv changed, method: %s, key: %s", r.Method, key)
	w.WriteHeader(http.StatusNoContent)
}

func (s *etcdStore) putRaw(key string, value []byte) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.rev++
	s.kvs[key] = etcdKV{value: append([]byte(nil), value...)}
}

func (s *etcdStore) deleteRaw(key string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.rev++
	delete(s.kvs, key)
}

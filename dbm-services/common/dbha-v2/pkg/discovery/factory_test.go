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

package discovery_test

import (
	"context"
	"dbm-services/common/dbha-v2/pkg/discovery"
	"log"
	"os"
	"testing"

	clientv3 "go.etcd.io/etcd/client/v3"
)

var client *clientv3.Client
var reg *discovery.Registry
var dis *discovery.Discovery

func setup() {

	endpoints := os.Getenv("DBHA_ETCD_ENDPOINTS")
	user := os.Getenv("DBHA_ETCD_USER")
	password := os.Getenv("DBHA_ETCD_PASSWORD")

	log.Println("endpoints:", endpoints)
	log.Println("user:", user)
	log.Println("password:", password)

	if endpoints == "" {
		log.Fatal("endpoints is required")
	}

	if user == "" {
		log.Fatal("user is required")
	}

	if password == "" {
		log.Fatal("password is required")
	}

	cli, err := discovery.NewClient([]string{endpoints}, user, password)
	if err != nil {
		log.Fatalf("failed to create etcd client. errmsg:%s", err.Error())
	}

	client = cli

	r, err := discovery.NewRegistry(client, "test-service-id", 10)
	if err != nil {
		log.Fatalf("failed to create registry. errmsg:%s", err.Error())
	}

	reg = r

	d, err := discovery.NewDiscovery(client)
	if err != nil {
		log.Fatalf("failed to create discovery. errmsg:%s", err.Error())
	}

	err = reg.SetService(context.Background(), "")
	if err != nil {
		log.Fatalf("failed to set service. errmsg:%s", err.Error())
	}

	dis = d
}

func teardown() {

	reg.Close()
	dis.Close()
}

func TestRegistrySetService(t *testing.T) {

	err := reg.SetService(context.Background(), "test-id")
	if err != nil {
		t.Logf("failed to set service. errmsg:%s", err.Error())
	}
}

func TestDiscotryGetWithPrefix(t *testing.T) {

	kvs, err := dis.GetWithPrefix(context.Background(), "")
	if err != nil {
		t.Logf("failed to get service. errmsg:%s", err.Error())
	}

	for key, value := range kvs {
		t.Logf("key:%s, value:%s", key, value)
	}
}

func TestMain(m *testing.M) {

	setup()

	code := m.Run()

	teardown()

	os.Exit(code)
}

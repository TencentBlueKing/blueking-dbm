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

package config

import (
	"context"
	"errors"
	"go/ast"
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"sync"
	"testing"
	"time"

	"dbm-services/common/dbha-v2/pkg/dbcred"
	"dbm-services/common/dbha-v2/pkg/probeconfig"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

var (
	credTestOnce sync.Once
	mongoFill    = &recordingResolver{}
	riakFill     = &recordingResolver{err: errors.New("riak fill boom")}
)

type recordingResolver struct {
	mu      sync.Mutex
	calls   int
	err     error
	lastAPI string
}

func (r *recordingResolver) Fill(_ context.Context, _ int, items []*dbcred.Item) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.calls++
	if r.err != nil {
		return r.err
	}
	for _, it := range items {
		it.User = "filled-user"
		it.Password = "filled-pass"
	}
	return nil
}

func (r *recordingResolver) Configure(lookup dbcred.ConfigLookup) error {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.calls++
	if api, ok := lookup("redis_password"); ok {
		r.lastAPI = api.Api
	}
	return r.err
}

func (r *recordingResolver) reset() {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.calls = 0
	r.lastAPI = ""
}

func (r *recordingResolver) callCount() int {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.calls
}

func ensureCredTestResolvers(t *testing.T) {
	t.Helper()
	credTestOnce.Do(func() {
		dbcred.Register(haprobe.DbTypeMongo, mongoFill)
		dbcred.Register(haprobe.DbTypeRiak, riakFill)
	})
	mongoFill.reset()
	riakFill.reset()
}

func TestFillInstanceCredentialsWritesBackByClusterID(t *testing.T) {
	ensureCredTestResolvers(t)

	items := []probeconfig.ProbeMetadataItem{
		{
			ClusterID:   101,
			ClusterType: string(haprobe.DbmMetadataClusterTypeMongoReplicaSet),
			IP:          "127.0.0.1",
			Port:        27017,
			User:        "static-u",
			Password:    "static-p",
		},
		{
			ClusterID:   202,
			ClusterType: string(haprobe.DbmMetadataClusterTypeTendbha),
			IP:          "127.0.0.1",
			Port:        3306,
			User:        "mysql-u",
			Password:    "mysql-p",
		},
	}

	fillInstanceCredentials(context.Background(), 0, items)

	if items[0].User != "filled-user" || items[0].Password != "filled-pass" {
		t.Fatalf("mongo item not filled, user: %s, password set: %t",
			items[0].User, items[0].Password != "")
	}
	if items[1].User != "mysql-u" || items[1].Password != "mysql-p" {
		t.Fatalf("unregistered mysql should keep static creds, user: %s", items[1].User)
	}
	if mongoFill.callCount() != 1 {
		t.Fatalf("mongo Fill calls: %d, want 1", mongoFill.callCount())
	}
}

func TestFillInstanceCredentialsContinuesAfterGroupError(t *testing.T) {
	ensureCredTestResolvers(t)

	items := []probeconfig.ProbeMetadataItem{
		{
			ClusterID:   1,
			ClusterType: string(haprobe.DbmMetadataClusterTypeRiak),
			IP:          "127.0.0.1",
			Port:        8087,
		},
		{
			ClusterID:   2,
			ClusterType: string(haprobe.DbmMetadataClusterTypeMongoReplicaSet),
			IP:          "127.0.0.1",
			Port:        27017,
		},
	}

	fillInstanceCredentials(context.Background(), 0, items)

	if items[1].User != "filled-user" || items[1].Password != "filled-pass" {
		t.Fatalf("mongo group should still fill after riak error, user: %s", items[1].User)
	}
	if items[0].User != "" || items[0].Password != "" {
		t.Fatalf("failed riak group should keep empty credentials")
	}
}

func TestLookupDbmApiReadsSnapshot(t *testing.T) {
	saved := Snapshot()
	t.Cleanup(func() { Apply(saved) })

	Apply(Configuration{
		DbmApis: []DbmApi{{
			Name: "redis_password", Api: "http://127.0.0.1:8000/pass",
			Token: "tok", Method: "POST", Timeout: time.Second,
		}},
	})

	got, ok := LookupDbmApi("redis_password")
	if !ok {
		t.Fatal("LookupDbmApi should find redis_password")
	}
	if got.Api != "http://127.0.0.1:8000/pass" {
		t.Fatalf("api: %s", got.Api)
	}
	if _, ok := LookupDbmApi("missing"); ok {
		t.Fatal("missing name should return false")
	}
}

func TestDbmApisEqualNilAndEmpty(t *testing.T) {
	if !DbmApisEqual(nil, nil) {
		t.Fatal("nil vs nil should be equal")
	}
	if !DbmApisEqual(nil, []DbmApi{}) {
		t.Fatal("nil vs empty should be equal")
	}
	if !DbmApisEqual([]DbmApi{}, nil) {
		t.Fatal("empty vs nil should be equal")
	}
	a := []DbmApi{{Name: "a"}}
	b := []DbmApi{{Name: "a"}}
	if !DbmApisEqual(a, b) {
		t.Fatal("identical entries should be equal")
	}
	if DbmApisEqual(a, []DbmApi{{Name: "b"}}) {
		t.Fatal("different names should not be equal")
	}
}

// TestGenProbeConfigCallsFillInstanceCredentials locks the conflict-resolution
// wiring so a future rebase cannot drop the credential fill silently.
func TestGenProbeConfigCallsFillInstanceCredentials(t *testing.T) {
	src, err := os.ReadFile(filepath.Join(".", "probe_config.go"))
	if err != nil {
		t.Fatalf("read probe_config.go failed, errmsg: %s", err)
	}
	fset := token.NewFileSet()
	file, err := parser.ParseFile(fset, "probe_config.go", src, 0)
	if err != nil {
		t.Fatalf("parse probe_config.go failed, errmsg: %s", err)
	}

	var genFn *ast.FuncDecl
	for _, decl := range file.Decls {
		fn, ok := decl.(*ast.FuncDecl)
		if !ok || fn.Name == nil || fn.Name.Name != "GenProbeConfig" {
			continue
		}
		genFn = fn
		break
	}
	if genFn == nil || genFn.Body == nil {
		t.Fatal("GenProbeConfig not found")
	}

	found := false
	ast.Inspect(genFn.Body, func(n ast.Node) bool {
		call, ok := n.(*ast.CallExpr)
		if !ok {
			return true
		}
		ident, ok := call.Fun.(*ast.Ident)
		if ok && ident.Name == "fillInstanceCredentials" {
			found = true
			return false
		}
		return true
	})
	if !found {
		t.Fatal("GenProbeConfig must call fillInstanceCredentials")
	}
}

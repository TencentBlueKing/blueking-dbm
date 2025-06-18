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
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"log"
	"testing"
	"time"
)

func TestRegsitrySetService(t *testing.T) {
	ctx := context.Background()

	err := reg.SetService(ctx, "registry-test-value")
	if err != nil {
		t.Errorf("failed to set service. errmsg: %v", err)
	}

	resp, err := client.Get(ctx, reg.GetRootKey())
	if err != nil {
		t.Errorf("failed to get service value. errmsg: %v", err)
	}

	if len(resp.Kvs) == 0 {
		t.Errorf("undefined service value")
	}
	if string(resp.Kvs[0].Value) != "registry-test-value" {
		t.Errorf("service value does not match. Expected: registry-test-value, Got: %s", string(resp.Kvs[0].Value))
	}

	if resp.Kvs[0].Lease == 0 {
		t.Errorf("service has no lease attached")
	}

}

func TestRegistrySet(t *testing.T) {
	ctx := context.Background()

	err := reg.Set(ctx, "registry-test-key", "registry-test-value")
	if err != nil {
		t.Errorf("failed to set key. errmsg: %v", err)
	}

	time.Sleep(10 * time.Second)

	expectedKey := reg.GetRootKey() + "/registry-test-key"
	resp, err := client.Get(ctx, expectedKey)

	if err != nil {
		t.Errorf("failed to get child node value. errmsg: %v", err)
	}
	if len(resp.Kvs) == 0 {
		t.Errorf("missing child node value. errmsg: %v", err)
	}
	if string(resp.Kvs[0].Value) != "registry-test-value" {
		t.Errorf("service value does not match. Expected: registry-test-value, Got: %s", string(resp.Kvs[0].Value))
	}
}

func TestRegistryLeaseManagement(t *testing.T) {
	ctx := context.Background()

	err := reg.SetService(ctx, "registry-test-value")
	if err != nil {
		t.Errorf("failed to set service. errmsg: %v", err.Error())
	}

	resp, err := client.Get(ctx, reg.GetRootKey())
	if err != nil {
		t.Errorf("failed to get service value. errmsg: %v", err.Error())
	}
	if len(resp.Kvs) == 0 {
		t.Errorf("service value expired. errmsg: %v", err)
	}

	initialLeaseID := resp.Kvs[0].Lease

	time.Sleep(10 * time.Second)

	resp, err = client.Get(ctx, reg.GetRootKey())
	if err != nil {
		t.Errorf("failed to get service value. errmsg: %v", err.Error())
	}
	if len(resp.Kvs) == 0 {
		t.Errorf("service value expired. errmsg: %v", err)
	}

	if resp.Kvs[0].Lease != initialLeaseID {
		t.Errorf("The lease ID has changed, likely due to lease renewal.")
	}
}

func TestRegistryInvalidParameters(t *testing.T) {
	ctx := context.Background()

	err := reg.Set(ctx, "", "registry-test-value")
	if err == nil {
		t.Errorf("expect an error to be returned for empty keys")
	}
	if err.(*gerrors.Error).Code() != gerrors.InvalidParameter {
		t.Errorf("expected error code: InvalidParameter, actual: %v", err)
	}
}

func TestRegistryClose(t *testing.T) {
	newreg, err := discovery.NewRegistry(client, "test-service-id", 10)
	if err != nil {
		log.Fatalf("failed to create registry. errmsg:%s", err.Error())
	}

	ctx := context.Background()

	err = newreg.SetService(ctx, "registry-test-value")
	if err != nil {
		t.Errorf("failed to set service. errmsg: %v", err)
	}

	newreg.Close()

	err = newreg.SetService(ctx, "registry-test-value")
	if err == nil {
		t.Errorf("expect SetService to return an error after being closed")
	}
}

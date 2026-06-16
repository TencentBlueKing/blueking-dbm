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

package handler

import "testing"

func TestBuildListRequestBkCloudID(t *testing.T) {
	t.Parallel()

	req, err := buildListRequest(ListOptions{BkCloudID: -1})
	if err != nil {
		t.Fatalf("build list request failed: %s", err)
	}
	if req.BkCloudID != nil {
		t.Fatalf("bk cloud id = %v, want nil", *req.BkCloudID)
	}

	req, err = buildListRequest(ListOptions{BkCloudID: 0})
	if err != nil {
		t.Fatalf("build list request failed: %s", err)
	}
	if req.BkCloudID == nil || *req.BkCloudID != 0 {
		t.Fatalf("bk cloud id = %v, want 0", req.BkCloudID)
	}
}

func TestBuildUpdateRequestBkCloudID(t *testing.T) {
	t.Parallel()

	req, err := buildUpdateRequest(UpdateOptions{ID: 1, Status: "enabled", BkCloudID: -1})
	if err != nil {
		t.Fatalf("build update request failed: %s", err)
	}
	if req.QueryArgs.BkCloudID != nil {
		t.Fatalf("bk cloud id = %v, want nil", *req.QueryArgs.BkCloudID)
	}

	req, err = buildUpdateRequest(UpdateOptions{ID: 1, Status: "enabled", BkCloudID: 0})
	if err != nil {
		t.Fatalf("build update request failed: %s", err)
	}
	if req.QueryArgs.BkCloudID == nil || *req.QueryArgs.BkCloudID != 0 {
		t.Fatalf("bk cloud id = %v, want 0", req.QueryArgs.BkCloudID)
	}
}

func TestBuildUpdateRequestSetClusterName(t *testing.T) {
	t.Parallel()

	req, err := buildUpdateRequest(UpdateOptions{ID: 1, SetClusterName: "cluster-b"})
	if err != nil {
		t.Fatalf("build update request failed: %s", err)
	}
	if req.QueryArgs.ClusterName != nil {
		t.Fatalf("query cluster name = %v, want nil", *req.QueryArgs.ClusterName)
	}
	if req.SetArgs.ClusterName == nil || *req.SetArgs.ClusterName != "cluster-b" {
		t.Fatalf("set cluster name = %v, want cluster-b", req.SetArgs.ClusterName)
	}
}

func TestBuildDeleteRequestBkCloudID(t *testing.T) {
	t.Parallel()

	req, err := buildDeleteRequest(DeleteOptions{ID: 1, BkCloudID: -1})
	if err != nil {
		t.Fatalf("build delete request failed: %s", err)
	}
	if req.BkCloudID != nil {
		t.Fatalf("bk cloud id = %v, want nil", *req.BkCloudID)
	}

	req, err = buildDeleteRequest(DeleteOptions{ID: 1, BkCloudID: 0})
	if err != nil {
		t.Fatalf("build delete request failed: %s", err)
	}
	if req.BkCloudID == nil || *req.BkCloudID != 0 {
		t.Fatalf("bk cloud id = %v, want 0", req.BkCloudID)
	}
}

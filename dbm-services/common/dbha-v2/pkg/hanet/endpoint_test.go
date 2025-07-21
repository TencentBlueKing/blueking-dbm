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

package hanet_test

import (
	"dbm-services/common/dbha-v2/pkg/hanet"
	"testing"
)

func TestEndpoint(t *testing.T) {
	epoint, err := hanet.NewEndpoint("tcp://127.0.0.1:3306")
	if err != nil {
		t.Fatalf("create endpoint failed, %v", err)
	}

	if epoint.Proto != "tcp" {
		t.Fatalf("unidentified schema(%s)", epoint.Proto)
	}

	if epoint.Host != "127.0.0.1" {
		t.Fatalf("unidentified host(%s)", epoint.Host)
	}

	if epoint.Port != 3306 {
		t.Fatalf("unidentified port(%d)", epoint.Port)
	}
}

func TestEndpoints(t *testing.T) {
	epoints, err := hanet.NewEndpoints("tcp://127.0.0.1:3306;tcp6://127.0.0.2:3308")
	if err != nil {
		t.Fatalf("create endpoints failed, %v", err)
	}

	if len(epoints) != 2 {
		t.Fatalf("create endpoints failed, invalide endpoint count(%d)", len(epoints))
	}

	if epoints[0].Proto != "tcp" {
		t.Fatalf("unidentified schema(%s)", epoints[0].Proto)
	}

	if epoints[0].Host != "127.0.0.1" {
		t.Fatalf("unidentified host(%s)", epoints[0].Host)
	}

	if epoints[0].Port != 3306 {
		t.Fatalf("unidentified port(%d)", epoints[0].Port)
	}

	if epoints[1].Proto != "tcp6" {
		t.Fatalf("unidentified schema(%s)", epoints[1].Proto)
	}

	if epoints[1].Host != "127.0.0.2" {
		t.Fatalf("unidentified host(%s)", epoints[1].Host)
	}

	if epoints[1].Port != 3308 {
		t.Fatalf("unidentified port(%d)", epoints[1].Port)
	}
}

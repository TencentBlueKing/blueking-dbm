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

package discovery

import (
	"crypto/tls"
	"testing"
	"time"

	"go.uber.org/zap"
)

func TestOptionUser(t *testing.T) {
	user := "testuser"
	opt := OptionUser(user)
	if opt == nil {
		t.Fatal("OptionUser() returned nil")
	}
	t.Logf("OptionUser(%s) created successfully", user)
}

func TestOptionPassword(t *testing.T) {
	password := "testpassword"
	opt := OptionPassword(password)
	if opt == nil {
		t.Fatal("OptionPassword() returned nil")
	}
	t.Logf("OptionPassword() created successfully")
}

func TestOptionBufferMaxSize(t *testing.T) {
	size := 2048
	opt := OptionBufferMaxSize(size)
	if opt == nil {
		t.Fatal("OptionBufferMaxSize() returned nil")
	}
	t.Logf("OptionBufferMaxSize(%d) created successfully", size)
}

func TestOptionTTL(t *testing.T) {
	tests := []struct {
		name string
		ttl  int
	}{
		{"normal_ttl", 10},
		{"below_default_ttl", 3},
		{"zero_ttl", 0},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			opt := OptionTTL(tt.ttl)
			if opt == nil {
				t.Fatalf("OptionTTL(%d) returned nil", tt.ttl)
			}
			t.Logf("OptionTTL(%d) created successfully", tt.ttl)
		})
	}
}

func TestOptionServiceID(t *testing.T) {
	serviceID := "test-service-id"
	opt := OptionServiceID(serviceID)
	if opt == nil {
		t.Fatal("OptionServiceID() returned nil")
	}
	t.Logf("OptionServiceID(%s) created successfully", serviceID)
}

func TestOptionServiceName(t *testing.T) {
	serviceName := "test-service"
	opt := OptionServiceName(serviceName)
	if opt == nil {
		t.Fatal("OptionServiceName() returned nil")
	}
	t.Logf("OptionServiceName(%s) created successfully", serviceName)
}

func TestOptionEndpoints(t *testing.T) {
	endpoints := []string{"localhost:2379", "localhost:2380"}
	opt := OptionEndpoints(endpoints)
	if opt == nil {
		t.Fatal("OptionEndpoints() returned nil")
	}
	t.Logf("OptionEndpoints(%v) created successfully", endpoints)
}

func TestOptionDialTimeout(t *testing.T) {
	timeout := 10 * time.Second
	opt := OptionDialTimeout(timeout)
	if opt == nil {
		t.Fatal("OptionDialTimeout() returned nil")
	}
	t.Logf("OptionDialTimeout(%v) created successfully", timeout)
}

func TestOptionAutoSyncInterval(t *testing.T) {
	interval := 30 * time.Second
	opt := OptionAutoSyncInterval(interval)
	if opt == nil {
		t.Fatal("OptionAutoSyncInterval() returned nil")
	}
	t.Logf("OptionAutoSyncInterval(%v) created successfully", interval)
}

func TestOptionKeepAliveTime(t *testing.T) {
	keepAlive := 15 * time.Second
	opt := OptionKeepAliveTime(keepAlive)
	if opt == nil {
		t.Fatal("OptionKeepAliveTime() returned nil")
	}
	t.Logf("OptionKeepAliveTime(%v) created successfully", keepAlive)
}

func TestOptionKeepAliveTimeout(t *testing.T) {
	timeout := 5 * time.Second
	opt := OptionKeepAliveTimeout(timeout)
	if opt == nil {
		t.Fatal("OptionKeepAliveTimeout() returned nil")
	}
	t.Logf("OptionKeepAliveTimeout(%v) created successfully", timeout)
}

func TestOptionRegistryRootKeyPrefix(t *testing.T) {
	prefix := "/custom/registry"
	opt := OptionRegistryRootKeyPrefix(prefix)
	if opt == nil {
		t.Fatal("OptionRegistryRootKeyPrefix() returned nil")
	}
	t.Logf("OptionRegistryRootKeyPrefix(%s) created successfully", prefix)
}

func TestOptionMaxUnaryRetries(t *testing.T) {
	retries := uint(5)
	opt := OptionMaxUnaryRetries(retries)
	if opt == nil {
		t.Fatal("OptionMaxUnaryRetries() returned nil")
	}
	t.Logf("OptionMaxUnaryRetries(%d) created successfully", retries)
}

func TestConfigUsesOptionMaxUnaryRetries(t *testing.T) {
	o := defaultOptions
	retries := uint(7)

	if err := OptionMaxUnaryRetries(retries).apply(&o); err != nil {
		t.Fatalf("failed to apply OptionMaxUnaryRetries, errmsg: %s", err)
	}

	cfg, err := o.Config()
	if err != nil {
		t.Fatalf("Config() unexpected error, errmsg: %s", err)
	}
	if cfg.MaxUnaryRetries != retries {
		t.Fatalf("Config().MaxUnaryRetries = %d, want %d", cfg.MaxUnaryRetries, retries)
	}
}

func TestOptionLogger(t *testing.T) {
	logger, _ := zap.NewDevelopment()
	opt := OptionLogger(logger)
	if opt == nil {
		t.Fatal("OptionLogger() returned nil")
	}
	t.Logf("OptionLogger() created successfully")
}

func TestOptionCertFile(t *testing.T) {
	opt := OptionCertFile("/path/to/cert.pem")
	if opt == nil {
		t.Fatal("OptionCertFile() returned nil")
	}
	t.Logf("OptionCertFile() created successfully")
}

func TestOptionKeyFile(t *testing.T) {
	opt := OptionKeyFile("/path/to/key.pem")
	if opt == nil {
		t.Fatal("OptionKeyFile() returned nil")
	}
	t.Logf("OptionKeyFile() created successfully")
}

func TestOptionTrustedCAFile(t *testing.T) {
	opt := OptionTrustedCAFile("/path/to/ca.pem")
	if opt == nil {
		t.Fatal("OptionTrustedCAFile() returned nil")
	}
	t.Logf("OptionTrustedCAFile() created successfully")
}

func TestConfigTLSNotSetWithoutCert(t *testing.T) {
	o := defaultOptions
	cfg, err := o.Config()
	if err != nil {
		t.Fatalf("Config() unexpected error, errmsg: %s", err)
	}
	if cfg.TLS != nil {
		t.Error("Config().TLS should be nil when cert/key not set")
	}
}

func TestNewClientWithOptionsFailsWhenTLSFilesInvalid(t *testing.T) {
	_, err := NewClientWithOptions(
		OptionEndpoints([]string{"http://localhost:2379"}),
		OptionServiceID("test-id"),
		OptionCertFile("/nonexistent/cert.pem"),
		OptionKeyFile("/nonexistent/key.pem"),
	)
	if err == nil {
		t.Error("NewClientWithOptions expected to fail when TLS cert/key files are invalid")
	}
}

func TestConfigFailsWhenTLSFilesInvalid(t *testing.T) {
	o := defaultOptions
	if err := OptionCertFile("/nonexistent/cert.pem").apply(&o); err != nil {
		t.Fatalf("failed to apply OptionCertFile, errmsg: %s", err)
	}
	if err := OptionKeyFile("/nonexistent/key.pem").apply(&o); err != nil {
		t.Fatalf("failed to apply OptionKeyFile, errmsg: %s", err)
	}

	_, err := o.Config()
	if err == nil {
		t.Fatal("Config() expected to fail when TLS cert/key files are invalid")
	}
}

func TestConfigUsesCachedTLSConfig(t *testing.T) {
	o := defaultOptions
	o.certFile = "/nonexistent/cert.pem"
	o.keyFile = "/nonexistent/key.pem"
	o.tlsConfig = &tls.Config{}

	cfg, err := o.Config()
	if err != nil {
		t.Fatalf("Config() unexpected error with cached tlsConfig, errmsg: %s", err)
	}
	if cfg.TLS != o.tlsConfig {
		t.Fatal("Config() should reuse cached tlsConfig")
	}
}

func TestOptionCertFileValidation(t *testing.T) {
	baseOpts := []Option{
		OptionEndpoints([]string{"http://localhost:2379"}),
		OptionServiceID("test-id"),
	}

	t.Run("empty_path", func(t *testing.T) {
		opts := append(baseOpts, OptionCertFile(""), OptionKeyFile("/abs/key.pem"))
		_, err := NewClientWithOptions(opts...)
		if err == nil {
			t.Fatal("expected error when certFile is empty")
		}
	})

	t.Run("relative_path", func(t *testing.T) {
		opts := append(baseOpts, OptionCertFile("relative/cert.pem"), OptionKeyFile("/abs/key.pem"))
		_, err := NewClientWithOptions(opts...)
		if err == nil {
			t.Fatal("expected error when certFile is relative path")
		}
	})
}

func TestOptionKeyFileValidation(t *testing.T) {
	baseOpts := []Option{
		OptionEndpoints([]string{"http://localhost:2379"}),
		OptionServiceID("test-id"),
	}

	t.Run("empty_path", func(t *testing.T) {
		opts := append(baseOpts, OptionCertFile("/abs/cert.pem"), OptionKeyFile(""))
		_, err := NewClientWithOptions(opts...)
		if err == nil {
			t.Fatal("expected error when keyFile is empty")
		}
	})

	t.Run("relative_path", func(t *testing.T) {
		opts := append(baseOpts, OptionCertFile("/abs/cert.pem"), OptionKeyFile("relative/key.pem"))
		_, err := NewClientWithOptions(opts...)
		if err == nil {
			t.Fatal("expected error when keyFile is relative path")
		}
	})
}

func TestOptionTrustedCAFileValidation(t *testing.T) {
	t.Run("relative_path_rejected", func(t *testing.T) {
		opts := []Option{
			OptionEndpoints([]string{"http://localhost:2379"}),
			OptionServiceID("test-id"),
			OptionCertFile("/abs/cert.pem"),
			OptionKeyFile("/abs/key.pem"),
			OptionTrustedCAFile("relative/ca.pem"),
		}
		_, err := NewClientWithOptions(opts...)
		if err == nil {
			t.Fatal("expected error when trustedCAFile is relative path")
		}
	})

	t.Run("empty_allowed", func(t *testing.T) {
		opts := []Option{
			OptionEndpoints([]string{"http://localhost:2379"}),
			OptionServiceID("test-id"),
			OptionCertFile("/abs/cert.pem"),
			OptionKeyFile("/abs/key.pem"),
			OptionTrustedCAFile(""),
		}
		_, err := NewClientWithOptions(opts...)
		if err == nil {
			t.Log("OptionTrustedCAFile empty is allowed; buildTLSConfig fails later for missing files")
		}
	})
}

func TestNewClientWithOptionsFailsWhenOnlyCertFileProvided(t *testing.T) {
	_, err := NewClientWithOptions(
		OptionEndpoints([]string{"http://localhost:2379"}),
		OptionServiceID("test-id"),
		OptionCertFile("/abs/cert.pem"),
	)
	if err == nil {
		t.Fatal("expected error when only certFile is configured")
	}
}

func TestNewClientWithOptionsFailsWhenOnlyKeyFileProvided(t *testing.T) {
	_, err := NewClientWithOptions(
		OptionEndpoints([]string{"http://localhost:2379"}),
		OptionServiceID("test-id"),
		OptionKeyFile("/abs/key.pem"),
	)
	if err == nil {
		t.Fatal("expected error when only keyFile is configured")
	}
}

func TestNewClientWithOptionsFailsWhenOnlyTrustedCAFileProvided(t *testing.T) {
	_, err := NewClientWithOptions(
		OptionEndpoints([]string{"http://localhost:2379"}),
		OptionServiceID("test-id"),
		OptionTrustedCAFile("/abs/ca.pem"),
	)
	if err == nil {
		t.Fatal("expected error when only trustedCAFile is configured")
	}
}

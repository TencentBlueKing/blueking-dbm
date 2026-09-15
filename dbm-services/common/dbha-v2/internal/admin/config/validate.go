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
	"fmt"
	"net"
	"net/url"
	"os"
	"strings"
	"time"

	"dbm-services/common/dbha-v2/pkg/logger"
)

// Validate reports illegal values in cfg. Error messages must not contain secrets
// (storage password, harvester passwords, dbmApi tokens).
func Validate(cfg Configuration) error {
	var errs []string

	errs = append(errs, validateListenAddress("apm.listenAddress", cfg.Apm.ListenAddress)...)
	errs = append(errs, validateListenAddress("grpc.listenAddress", cfg.Grpc.ListenAddress)...)
	errs = append(errs, validateListenAddress("web.listenAddress", cfg.Web.ListenAddress)...)

	if strings.TrimSpace(cfg.Discovery.Endpoint) == "" {
		errs = append(errs, "discovery.endpoint is required")
	}
	if strings.TrimSpace(cfg.Storage.Endpoint) == "" {
		errs = append(errs, "storage.endpoint is required")
	}

	errs = append(errs, validateLog(cfg.Log)...)
	errs = append(errs, validateTLSPair("discovery", cfg.Discovery.CertFile, cfg.Discovery.KeyFile)...)
	errs = append(errs, validateDurationPositive("apm.readTimeout", cfg.Apm.ReadTimeout)...)
	errs = append(errs, validateDurationPositive("apm.writeTimeout", cfg.Apm.WriteTimeout)...)
	errs = append(errs, validateDurationPositive("web.readTimeout", cfg.Web.ReadTimeout)...)
	errs = append(errs, validateDurationPositive("web.writeTimeout", cfg.Web.WriteTimeout)...)
	errs = append(errs, validateDurationPositive("grpc.serverPingTime", cfg.Grpc.ServerPingTime)...)
	errs = append(errs, validateDurationPositive("grpc.pingTimeout", cfg.Grpc.PingTimeout)...)
	errs = append(errs, validateProbeGseConnTimeout(cfg.ProbeGse.ConnTimeout)...)

	if cfg.Log.FileCount < 0 {
		errs = append(errs, "log.fileCount must be >= 0")
	}
	if cfg.Log.FileSize < 0 {
		errs = append(errs, "log.fileSize must be >= 0")
	}
	if cfg.Grpc.MaxReceiveMessageSize < 0 {
		errs = append(errs, "grpc.maxReceiveMessageSize must be >= 0")
	}
	if cfg.Grpc.MaxSendMessageSize < 0 {
		errs = append(errs, "grpc.maxSendMessageSize must be >= 0")
	}

	if len(errs) == 0 {
		return nil
	}
	return fmt.Errorf("invalid admin configuration: %s", strings.Join(errs, "; "))
}

func validateLog(log LogConfig) []string {
	level := strings.ToLower(strings.TrimSpace(log.Level))
	if level == "" {
		return nil
	}
	switch logger.Level(level) {
	case logger.DebugLevel, logger.InfoLevel, logger.WarnLevel, logger.ErrorLevel, logger.FatalLevel:
		return nil
	default:
		return []string{fmt.Sprintf("log.level is invalid: %s", log.Level)}
	}
}

func validateListenAddress(field, raw string) []string {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return []string{fmt.Sprintf("%s is required", field)}
	}

	addr := raw
	if strings.Contains(raw, "://") {
		u, err := url.Parse(raw)
		if err != nil {
			return []string{fmt.Sprintf("%s is not a valid URL", field)}
		}
		addr = u.Host
		if addr == "" {
			return []string{fmt.Sprintf("%s is missing host:port", field)}
		}
	}

	host, port, err := net.SplitHostPort(addr)
	if err != nil {
		return []string{fmt.Sprintf("%s must be host:port", field)}
	}
	if port == "" {
		return []string{fmt.Sprintf("%s is missing port", field)}
	}
	if _, err := net.LookupPort("tcp", port); err != nil {
		return []string{fmt.Sprintf("%s has invalid port", field)}
	}
	_ = host
	return nil
}

func validateTLSPair(prefix, certFile, keyFile string) []string {
	certFile = strings.TrimSpace(certFile)
	keyFile = strings.TrimSpace(keyFile)
	if certFile == "" && keyFile == "" {
		return nil
	}
	if certFile == "" || keyFile == "" {
		return []string{fmt.Sprintf("%s.certFile and %s.keyFile must be set together", prefix, prefix)}
	}
	var errs []string
	if _, err := os.Stat(certFile); err != nil {
		errs = append(errs, fmt.Sprintf("%s.certFile is not readable", prefix))
	}
	if _, err := os.Stat(keyFile); err != nil {
		errs = append(errs, fmt.Sprintf("%s.keyFile is not readable", prefix))
	}
	return errs
}

func validateDurationPositive(field string, d time.Duration) []string {
	if d < 0 {
		return []string{fmt.Sprintf("%s must be >= 0", field)}
	}
	return nil
}

func validateProbeGseConnTimeout(raw string) []string {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return nil
	}
	if _, err := time.ParseDuration(raw); err != nil {
		return []string{"probeGse.connTimeout is not a valid duration"}
	}
	return nil
}

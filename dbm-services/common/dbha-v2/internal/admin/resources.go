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

package admin

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/internal/admin/api/open"
	adminapm "dbm-services/common/dbha-v2/internal/admin/apm"
	"dbm-services/common/dbha-v2/internal/admin/config"
	"dbm-services/common/dbha-v2/internal/admin/slot"
	"dbm-services/common/dbha-v2/pkg/discovery"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/haapm"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"

	"github.com/gin-gonic/gin"
	"github.com/hako/durafmt"
	"github.com/swaggest/swgui"
	"github.com/swaggest/swgui/v5emb"
)

const storageDrainTimeout = 5 * time.Second

type storageContextKey struct{}

type discoveryFingerprint struct {
	Endpoint      string
	User          string
	Password      string
	CertFile      string
	KeyFile       string
	TrustedCAFile string
}

type webFingerprint struct {
	Config     config.WebConfig
	DocFileDir string
}

type discoveryResource struct {
	client   *discovery.Client
	registry *discovery.Registry
}

type storageResource struct {
	db      *hamysql.GormDB
	mu      sync.Mutex
	active  int
	closing bool
	drained chan struct{}
}

func newStorageResource(db *hamysql.GormDB) *storageResource {
	drained := make(chan struct{})
	close(drained)
	return &storageResource{db: db, drained: drained}
}

func (r *storageResource) acquire() bool {
	r.mu.Lock()
	defer r.mu.Unlock()
	if r.closing {
		return false
	}
	if r.active == 0 {
		r.drained = make(chan struct{})
	}
	r.active++
	return true
}

func (r *storageResource) release() {
	r.mu.Lock()
	defer r.mu.Unlock()
	if r.active == 0 {
		return
	}
	r.active--
	if r.active == 0 {
		close(r.drained)
	}
}

func (r *storageResource) close(_ context.Context) {
	r.mu.Lock()
	r.closing = true
	drained := r.drained
	r.mu.Unlock()

	timer := time.NewTimer(storageDrainTimeout)
	defer timer.Stop()
	select {
	case <-drained:
	case <-timer.C:
		logger.Warn("storage drain timed out, timeout: %s", storageDrainTimeout)
	}
	r.db.Close()
}

func (s *Service) initSlots() {
	s.apmSlot = slot.New(slot.Spec[haapm.Server]{
		Name:        "apm",
		Fingerprint: apmFingerprint,
		Build:       s.buildApm,
		Close:       func(_ context.Context, server *haapm.Server) { _ = server.Stop() },
		// Same address cannot bind twice: Replace stops the current server then Serve a new
		// instance. Collector is reused because bindPrometheus skips when Collector != nil.
		// Different addresses Coexist (brief overlap), then the old server Stop on retire.
		Swap: func(old, next config.Configuration) slot.SwapPolicy {
			if old.Apm.ListenAddress == next.Apm.ListenAddress {
				return slot.SwapReplace
			}
			return slot.SwapCoexist
		},
	})
	s.discoverySlot = slot.New(slot.Spec[discoveryResource]{
		Name:        "discovery",
		Fingerprint: discoveryFP,
		Build:       s.buildDiscovery,
		Close:       closeDiscovery,
		Swap:        slot.AlwaysCoexist,
	})
	s.storageSlot = slot.New(slot.Spec[storageResource]{
		Name:        "storage",
		Fingerprint: storageFingerprint,
		Build:       s.buildStorage,
		Close:       func(ctx context.Context, resource *storageResource) { resource.close(ctx) },
		Swap:        slot.AlwaysCoexist,
	})
	s.webSlot = slot.New(slot.Spec[hanet.GinHTTPServer]{
		Name:        "web",
		Fingerprint: webFingerprintOf,
		Build:       s.buildWeb,
		Close:       func(_ context.Context, server *hanet.GinHTTPServer) { _ = server.Stop() },
		Swap: func(old, next config.Configuration) slot.SwapPolicy {
			if old.Web.ListenAddress == next.Web.ListenAddress {
				return slot.SwapReplace
			}
			return slot.SwapCoexist
		},
	})
	s.grpcSlot = newGRPCSlot(s)
	s.slots = []slot.Ops{s.discoverySlot, s.apmSlot, s.storageSlot, s.grpcSlot, s.webSlot}
}

func (s *Service) buildApm(_ context.Context, cfg config.Configuration) (*haapm.Server, error) {
	ep, err := hanet.Parse(cfg.Apm.ListenAddress, "http")
	if err != nil {
		return nil, gerrors.Newf(
			gerrors.InvalidConfiguration,
			"invalid admin apm listen address, errmsg: %s",
			err,
		)
	}
	return haapm.Serve(haapm.ServerConfig{
		Addr:         ep.HostPort(),
		Subsystem:    "dbha-v2-admin",
		ReadTimeout:  cfg.Apm.ReadTimeout,
		WriteTimeout: cfg.Apm.WriteTimeout,
	})
}

func (s *Service) buildDiscovery(ctx context.Context, cfg config.Configuration) (*discoveryResource, error) {
	tlsEnabled := cfg.Discovery.CertFile != "" && cfg.Discovery.KeyFile != ""
	endpoints, err := discovery.ParseEtcdEndpoints(cfg.Discovery.Endpoint, tlsEnabled)
	if err != nil {
		return nil, err
	}
	opts := []discovery.Option{
		discovery.OptionEndpoints(endpoints),
		discovery.OptionUser(cfg.Discovery.User),
		discovery.OptionPassword(cfg.Discovery.Password),
		discovery.OptionServiceName(s.info.Name),
		discovery.OptionServiceID(s.info.ID),
		discovery.OptionLogger(s.logger),
	}
	opts = appendDiscoveryTLS(opts, cfg.Discovery)
	client, err := discovery.NewClientWithOptions(opts...)
	if err != nil {
		return nil, err
	}
	resource := &discoveryResource{client: client, registry: client.CreateRegistry()}
	if err := s.setServiceInfo(ctx, resource.registry); err != nil {
		resource.registry.Close()
		return nil, err
	}
	return resource, nil
}

func appendDiscoveryTLS(opts []discovery.Option, cfg config.DiscoveryConfig) []discovery.Option {
	if cfg.CertFile != "" {
		opts = append(opts, discovery.OptionCertFile(cfg.CertFile))
	}
	if cfg.KeyFile != "" {
		opts = append(opts, discovery.OptionKeyFile(cfg.KeyFile))
	}
	if cfg.TrustedCAFile != "" {
		opts = append(opts, discovery.OptionTrustedCAFile(cfg.TrustedCAFile))
	}
	return opts
}

func discoveryFP(cfg config.Configuration) any {
	return discoveryFingerprint{
		Endpoint:      cfg.Discovery.Endpoint,
		User:          cfg.Discovery.User,
		Password:      cfg.Discovery.Password,
		CertFile:      cfg.Discovery.CertFile,
		KeyFile:       cfg.Discovery.KeyFile,
		TrustedCAFile: cfg.Discovery.TrustedCAFile,
	}
}

func apmFingerprint(cfg config.Configuration) any     { return cfg.Apm }
func storageFingerprint(cfg config.Configuration) any { return cfg.Storage }
func grpcFingerprint(cfg config.Configuration) any    { return cfg.Grpc }
func webFingerprintOf(cfg config.Configuration) any {
	return webFingerprint{Config: cfg.Web, DocFileDir: cfg.DocFileDir}
}

// slotFingerprintFuncs returns the Fingerprint closures used by initSlots, in slot order.
func slotFingerprintFuncs() []func(config.Configuration) any {
	return []func(config.Configuration) any{
		discoveryFP,
		apmFingerprint,
		storageFingerprint,
		grpcFingerprint,
		webFingerprintOf,
	}
}

func closeDiscovery(_ context.Context, resource *discoveryResource) {
	if resource.registry != nil {
		resource.registry.Close()
	}
}

func (s *Service) buildStorage(ctx context.Context, cfg config.Configuration) (*storageResource, error) {
	endpoint, err := hanet.NewEndpoint(cfg.Storage.Endpoint)
	if err != nil {
		return nil, gerrors.Newf(gerrors.InvalidConfiguration, "invalid storage configuration, errmsg: %s", err)
	}
	db, err := hamysql.NewGormDB(
		hamysql.OptionProto(endpoint.Proto),
		hamysql.OptionIP(endpoint.Host),
		hamysql.OptionPort(endpoint.Port),
		hamysql.OptionDBName(hamodel.DatabaseName),
		hamysql.OptionUser(cfg.Storage.User),
		hamysql.OptionPassword(cfg.Storage.Password),
		hamysql.OptionLogger(s.gormLogger),
	)
	if err != nil {
		return nil, err
	}
	sqlDB, err := db.DB().DB()
	if err == nil {
		err = sqlDB.PingContext(ctx)
	}
	if err != nil {
		db.Close()
		return nil, fmt.Errorf("ping mysql storage failed, errmsg: %w", err)
	}
	return newStorageResource(db), nil
}

func (s *Service) buildWeb(_ context.Context, cfg config.Configuration) (*hanet.GinHTTPServer, error) {
	ep, err := hanet.Parse(cfg.Web.ListenAddress, "http")
	if err != nil {
		return nil, gerrors.Newf(
			gerrors.InvalidConfiguration,
			"invalid admin web listen address, errmsg: %s",
			err,
		)
	}
	server := hanet.NewGinHTTPServer(&hanet.GinServerConfig{
		Host:         ep.Host,
		Port:         ep.Port,
		ReadTimeout:  cfg.Web.ReadTimeout,
		WriteTimeout: cfg.Web.WriteTimeout,
	})
	server.SetLifecycleMiddleware(s.storageHTTPMiddleware())
	server.SetMetricMiddleware(adminapm.MetricMiddleware())
	open.RegisterOpenAPI(s.currentDBForContext, server)
	server.SetSwaggerFileRoute(cfg.DocFileDir + "/swagger.json")
	handler := v5emb.NewHandlerWithConfig(swgui.Config{
		Title:       "admin api doc",
		SwaggerJSON: "/swagger.json",
		BasePath:    "/swagger-ui",
		ShowTopBar:  true,
		HideCurl:    false,
		JsonEditor:  true,
	})
	server.RegisterAPI(&hanet.ResetAPI{
		Method:  hanet.HttpMethodGet,
		Path:    "/swagger-ui/*any",
		Handler: gin.WrapH(handler),
	})
	if err := server.Start(); err != nil {
		return nil, err
	}
	return server, nil
}

func (s *Service) storageHTTPMiddleware() gin.HandlerFunc {
	return func(ctx *gin.Context) {
		resource := s.storageSlot.Get()
		if resource == nil || !resource.acquire() {
			ctx.AbortWithStatus(503)
			return
		}
		defer resource.release()
		requestCtx := context.WithValue(ctx.Request.Context(), storageContextKey{}, resource)
		ctx.Request = ctx.Request.WithContext(requestCtx)
		ctx.Next()
	}
}

func (s *Service) currentDB() *hamysql.GormDB {
	resource := s.storageSlot.Get()
	if resource == nil {
		return nil
	}
	return resource.db
}

func (s *Service) currentDBForContext(ctx context.Context) *hamysql.GormDB {
	return dbFromContext(ctx, s.currentDB)
}

func dbFromContext(ctx context.Context, fallback func() *hamysql.GormDB) *hamysql.GormDB {
	if resource, ok := ctx.Value(storageContextKey{}).(*storageResource); ok {
		return resource.db
	}
	return fallback()
}

func (s *Service) setServiceInfo(ctx context.Context, registry *discovery.Registry) error {
	s.infoMu.Lock()
	s.info.UpdatedAt = time.Now().Local()
	s.info.Uptime = durafmt.Parse(time.Since(s.info.StartTime)).String()
	data, err := json.Marshal(s.info)
	s.infoMu.Unlock()
	if err != nil {
		return err
	}
	return registry.SetService(ctx, string(data))
}

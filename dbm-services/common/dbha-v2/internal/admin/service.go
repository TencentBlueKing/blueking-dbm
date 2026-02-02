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
	"io"
	"net"
	"net/http"
	"strings"
	"sync"
	"time"

	"dbm-services/common/dbha-v2/internal/admin/api/open"
	"dbm-services/common/dbha-v2/internal/admin/api/open/handler"
	"dbm-services/common/dbha-v2/internal/admin/apm"
	"dbm-services/common/dbha-v2/internal/admin/config"
	"dbm-services/common/dbha-v2/internal/admin/strategy"
	"dbm-services/common/dbha-v2/pkg/constant"
	"dbm-services/common/dbha-v2/pkg/discovery"
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/haapm"
	"dbm-services/common/dbha-v2/pkg/hanet"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/machine"
	"dbm-services/common/dbha-v2/pkg/proto"
	"dbm-services/common/dbha-v2/pkg/storage/hamodel"
	"dbm-services/common/dbha-v2/pkg/storage/hamysql"
	"dbm-services/common/go-pubpkg/apm/metric"
	"dbm-services/common/go-pubpkg/apm/trace"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/hako/durafmt"
	"github.com/swaggest/swgui"
	"github.com/swaggest/swgui/v5emb"
	"go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin"
	"go.uber.org/zap"
	"google.golang.org/grpc"
	"google.golang.org/grpc/keepalive"
)

const (
	Name = "admin"
)

// Service is the admin service
type Service struct {
	proto.UnimplementedAdminServiceServer

	quit         chan struct{}
	info         discovery.ServiceInfo
	engine       *gin.Engine
	httpApmSvr   *http.Server
	discoveryCli *discovery.Client
	regCli       *discovery.Registry
	wg           sync.WaitGroup
	db           *hamysql.GormDB
	strategy     *strategy.Strategy
	address      string
	svr          *grpc.Server
	logger       *zap.Logger // only for the gRPC
	gormLogger   logger.Logger
}

// Heartbeat admin server heartbeat
func (a *Service) Heartbeat(ctx context.Context, req *proto.HeartbeatRequest) (*proto.HeartbeatResponse, error) {
	logger.Info("admin server heartbeat request(%v)", req)
	return &proto.HeartbeatResponse{Errmsg: "success"}, nil
}

// WatchConfig watch config
func (a *Service) WatchConfig(stream proto.AdminService_WatchConfigServer) error {
	ctx := stream.Context()

	for {
		select {
		case <-ctx.Done():
			logger.Error("admin server exited due to canceled context")
			return nil

		default:
			req, err := stream.Recv()
			if err == io.EOF {
				logger.Error("admin server exited. recv return errmsg(%v)", err)
				return nil
			}

			if err != nil {
				logger.Error("admin server exited. recv return errmsg(%v)", err)
				return nil
			}

			logger.Debug("request:%v", req)
			// NOTE: only test
			err = stream.Send(&proto.ProbeConfigResponse{
				Payload: "config respond",
			})
			if err != nil {
				logger.Error("respond config request failed, errmsg(%v)", err)
			}
		}
	}
}

// Run run admin service
func (s *Service) Run(ctx context.Context) error {
	ips, err := machine.GetLocalIPs()
	if err != nil {
		return err
	}

	s.info.Name = Name
	s.info.ID = uuid.New().String()
	s.info.StartTime = time.Now().Local()
	s.info.IPs = ips

	// create discovery client
	if err := s.createDiscovery(); err != nil {
		return err
	}

	// create apm server
	if err := s.createApmServer(); err != nil {
		return err
	}

	// create grpc server
	if err := s.createGrpcServer(); err != nil {
		return err
	}

	// create web server
	if err := s.createWebServer(); err != nil {
		return err
	}

	if err := haapm.AppStartupMetric.Set(float64(s.info.StartTime.Unix())); err != nil {
		logger.Warn("failed to update the startup time for this process, errmsg: %s", err)
	}

	if s.quit == nil {
		s.quit = make(chan struct{})
	}

	timerTimeout := 3 * time.Second
	timer := time.NewTimer(timerTimeout)
	defer timer.Stop()

	for {
		select {
		case <-s.quit:
			return nil

		case <-ctx.Done():
			return nil

		case <-timer.C:
			s.updateInfo()
			timer.Reset(timerTimeout)
		}
	}

}

// Close close admin service
func (s *Service) Close() {
	if s.svr != nil {
		s.svr.Stop()
		s.svr = nil
	}

	s.wg.Wait()
}

func (s *Service) createDiscovery() error {
	cli, err := discovery.NewClientWithOptions(
		discovery.OptionEndpoints(strings.Split(config.Cfg.Discovery.Endpoint, constant.Delimiter)),
		discovery.OptionUser(config.Cfg.Discovery.User),
		discovery.OptionPassword(config.Cfg.Discovery.Password),
		discovery.OptionServiceName(s.info.Name),
		discovery.OptionServiceID(s.info.ID),
		discovery.OptionLogger(s.logger),
	)

	if err != nil {
		return err
	}

	s.discoveryCli = cli

	s.regCli = cli.CreateRegistry()
	s.updateInfo()
	return nil
}

func (s *Service) updateInfo() {
	s.info.UpdatedAt = time.Now().Local()
	s.info.Uptime = durafmt.Parse(time.Now().Local().Sub(s.info.StartTime)).String()

	data, err := json.Marshal(s.info)
	if err != nil {
		logger.Warn("failed to marshal service info to json, errmsg: %s", err)
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	if err = s.regCli.SetService(ctx, string(data)); err != nil {
		logger.Warn("failed to update the service info in the registry, errmsg: %s", err)
	}
}

func (s *Service) createGrpcServer() error {
	kasp := keepalive.ServerParameters{
		Time:    constant.DefaultServerPingTime,
		Timeout: constant.DefaultPingTimeout,
	}

	kacp := keepalive.EnforcementPolicy{
		MinTime:             constant.DefaultKeepAliveMiniTime,
		PermitWithoutStream: true,
	}

	svr := grpc.NewServer(
		grpc.KeepaliveParams(kasp),
		grpc.KeepaliveEnforcementPolicy(kacp),
		grpc.MaxRecvMsgSize(constant.DefaultMaxReceiveMessageSize),
		grpc.MaxSendMsgSize(constant.DefaultMaxSendMessageSize),
	)

	proto.RegisterAdminServiceServer(svr, s)
	listen, err := net.Listen("tcp", config.Cfg.Grpc.ListenAddress)
	if err != nil {
		return gerrors.New(gerrors.NetException, err.Error())
	}

	s.svr = svr

	s.wg.Add(1)
	go func() {
		defer s.wg.Done()
		if err := s.svr.Serve(listen); err != nil {
			logger.Fatal("failed to run grpc server, errmsg: %s", err)
		}
		logger.Info("exited from the grpc server")
	}()

	return nil
}

func (s *Service) createApmServer() error {
	trace.Setup()

	if s.engine == nil {
		gin.SetMode(gin.ReleaseMode)
		s.engine = gin.Default()
		s.engine.Use(otelgin.Middleware("dbha-v2-admin"))
	}

	if s.httpApmSvr == nil {
		s.httpApmSvr = &http.Server{
			Handler:      s.engine,
			Addr:         config.Cfg.Apm.ListenAddress,
			ReadTimeout:  config.Cfg.Apm.ReadTimeout,
			WriteTimeout: config.Cfg.Apm.WriteTimeout,
		}
	}

	apm.InitAPM(s.info.ID, s.info.Name)
	metric.NewPrometheus("dbha-v2-admin", apm.Metrics).Use(s.engine)

	s.wg.Add(1)
	go func() {
		defer s.wg.Done()
		if err := s.httpApmSvr.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatal("failed to run apm server, errmsg: %s", err)
		}

		logger.Info("exited from the apm server")
	}()

	return nil
}

func (s *Service) createWebServer() error {
	// Initialize database connection
	if err := s.createStorage(); err != nil {
		return err
	}

	s.strategy = &strategy.Strategy{DB: s.db}

	strategyHandler := handler.NewStrategyHandler(s.strategy)

	serverConfig := &hanet.GinServerConfig{
		Host:         config.Cfg.Web.Host,
		Port:         config.Cfg.Web.Port,
		ReadTimeout:  config.Cfg.Web.ReadTimeout,
		WriteTimeout: config.Cfg.Web.WriteTimeout,
	}
	server := hanet.NewGinHTTPServer(serverConfig)

	// Set metric middleware for API requests
	server.SetMetricMiddleware(apm.MetricMiddleware())

	// register open api
	open.RegisterOpenAPI(strategyHandler, server)

	// add swagger api
	server.SetSwaggerFileRoute(config.Cfg.DocFileDir + "/swagger.json")
	hd := v5emb.NewHandlerWithConfig(swgui.Config{
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
		Handler: gin.WrapH(hd),
	})
	return server.Start()
}

func (s *Service) createStorage() error {
	epoint, err := hanet.NewEndpoint(config.Cfg.Storage.Endpoint)
	if err != nil {
		logger.Error("invalid storage configuration, errmsg: %s", err)
		return gerrors.Newf(gerrors.InvalidConfiguration, "invalid storage configuration, errmsg: %s", err)
	}

	db, err := hamysql.NewGormDB(
		hamysql.OptionProto(epoint.Proto),
		hamysql.OptionIP(epoint.Host),
		hamysql.OptionPort(epoint.Port),
		hamysql.OptionDBName(hamodel.DatabaseName),
		hamysql.OptionUser(config.Cfg.Storage.User),
		hamysql.OptionPassword(config.Cfg.Storage.Password),
		hamysql.OptionLogger(s.gormLogger),
	)

	if err != nil {
		logger.Warn("create mysql storage failed, errmsg: %s", err)
		return err
	}

	s.db = db
	return nil
}

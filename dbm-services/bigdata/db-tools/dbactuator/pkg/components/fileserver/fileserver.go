// Package fileserver TODO
package fileserver

import (
	"encoding/json"
	"fmt"
	"log"
	"math/rand"
	"net"
	"net/http"
	"strconv"
	"strings"
	"sync/atomic"
	"time"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/components"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/components/backup_download"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/cmutil"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/pkg/errors"
	"golang.org/x/net/netutil"
)

// FileServerComp TODO
type FileServerComp struct {
	Params FileServer `json:"extend"`
}

// FileServer TODO
type FileServer struct {
	// http file-server 监听地址. 不提供端口，会在 12000-19999 之间随机选择一个端口，不提供 ip 时默认 localhost
	BindAddress string `json:"bind_address" validate:"required"`
	// 将本地哪个目录通过 http 分享
	MountPath string `json:"mount_path" validate:"required"`
	// path_prefix 用在生成 url 时的路径前缀. 可留空
	PathPrefix string `json:"path_prefix"`
	// http basic auth user
	AuthUser string `json:"auth_user" validate:"required"`
	// http basic auth pass，为空时会随机生成密码
	AuthPass string `json:"auth_pass"`
	// 访问来源限制，从前往后匹配。格式 `["allow 1.1.1.1/32", "deny all"]`
	ACLs []string `json:"acls" example:"allow all"`
	// 暂不支持
	EnableTls bool `json:"enable_tls"`
	// 输出 download http 的信息，方便使用
	PrintDownload bool `json:"print_download"`

	bindHost       string
	bindPort       string
	procName       string
	procStartTime  time.Time
	lastActiveTime time.Time

	// 限制最大连接数，超过需要等待. 为 0 时表示不限制
	MaxConnections int `json:"max_connections"`
	// 超过最大空闲时间，自动退出. 示例 3600s, 60m, 1h
	ProcMaxIdleDuration string `json:"proc_maxidle_duration" example:"1h"`

	procMaxIdleDuration time.Duration
	server              *http.Server
	cw                  *ConnectionWatcher
}

// Example TODO
func (s *FileServerComp) Example() interface{} {
	comp := FileServerComp{
		Params: FileServer{
			BindAddress:         "1.1.1.1:18081",
			MountPath:           "/data/dbbak",
			PathPrefix:          "",
			AuthUser:            "test_bk_biz_id",
			AuthPass:            "",
			ACLs:                []string{"allow 127.0.0.1/32", "deny all"},
			MaxConnections:      10,
			ProcMaxIdleDuration: "1h",
		},
	}
	return comp
}

// New TODO
func (s *FileServer) New() error {
	var err error
	if s.BindAddress, err = s.getBindAddress(); err != nil {
		return err
	}
	if err = s.Validate(); err != nil {
		return err
	}
	if s.AuthUser == "" {
		return fmt.Errorf("no access user provided")
	}
	if s.AuthPass == "" {
		s.AuthPass = cmutil.RandomString(12)
	}
	if s.MaxConnections == 0 {
		s.MaxConnections = 9999
	}
	if s.ProcMaxIdleDuration == "" {
		s.procMaxIdleDuration = 3600 * time.Second
	} else {
		s.procMaxIdleDuration, err = time.ParseDuration(s.ProcMaxIdleDuration)
		if err != nil {
			return errors.Wrap(err, s.ProcMaxIdleDuration)
		}
	}
	if s.PathPrefix == "" {
		s.PathPrefix = fmt.Sprintf("/%s/", s.procName)
	}
	if len(s.ACLs) == 0 {
		s.ACLs = []string{fmt.Sprintf("allow %s/32", s.bindHost)}
	}
	// always "deny all"
	s.ACLs = append(s.ACLs, "deny all")
	// logger.Info("FileServer %+v", s)
	// print dbactuactor params format
	fmt.Println(s)
	return nil
}

// String 用于打印
func (s *FileServer) String() string {
	str, _ := json.Marshal(s)
	return string(str)
}

func (s *FileServer) getBindAddress() (string, error) {
	var host, port string
	var err error
	if s.BindAddress == "" {
		host = hostDefault
		port = getRandPort()
	} else {
		if host, port, err = net.SplitHostPort(s.BindAddress); err != nil {
			if strings.Contains(err.Error(), "missing port") {
				host = s.BindAddress
				port = getRandPort()
			} else {
				return "", err
			}
		} else {
			if host == "" {
				host = hostDefault
			}
			if port == "" {
				port = getRandPort()
			}
		}
	}
	s.bindHost = host
	s.bindPort = port
	s.BindAddress = fmt.Sprintf("%s:%s", host, port)
	return s.BindAddress, nil
}

// Validate TODO
func (s *FileServer) Validate() error {
	if s.MountPath == "" || s.MountPath == "/" || !strings.HasPrefix(s.MountPath, "/data") {
		return fmt.Errorf("path should start with /data")
	}
	// @todo should check mount_path exists or not

	pathID := util.RegexReplaceSubString(s.MountPath, `%|/| `, "")
	if pathID == "" {
		return fmt.Errorf("invalid path %s", s.MountPath)
	}
	s.procName = fmt.Sprintf("%s%s", pathID, s.bindPort)
	return nil
}

func (s *FileServer) handleFileServer(prefix string, handler http.Handler) http.HandlerFunc {
	// realHandler := http.StripPrefix(prefix, handler)
	// h := http.StripPrefix(prefix, handler)

	return func(w http.ResponseWriter, req *http.Request) {
		s.lastActiveTime = time.Now()
		handler.ServeHTTP(w, req)
	}
}

// Start TODO
func (s *FileServer) Start() error {
	if err := s.Validate(); err != nil {
		log.Fatalln(err)
	}

	handler := http.StripPrefix(s.PathPrefix, http.FileServer(http.Dir(s.MountPath)))
	hFunc := aclHandler(s.ACLs, s.handleBasicAuth(s.handleFileServer(s.PathPrefix, handler)))
	http.HandleFunc(s.PathPrefix, hFunc)

	s.cw = &ConnectionWatcher{}
	server := &http.Server{
		Addr:      s.BindAddress,
		Handler:   nil,
		ConnState: s.cw.OnStateChange,
	}
	s.server = server

	// http.Handle(s.Prefix, http.StripPrefix(s.Prefix, http.FileServer(http.Dir(s.Path))))
	s.procStartTime = time.Now()
	s.lastActiveTime = time.Now()
	li, err := net.Listen("tcp", s.BindAddress)
	if err != nil {
		log.Fatalln()
	}
	li = netutil.LimitListener(li, s.MaxConnections) // 最大连接数

	go func() {
		if err := server.Serve(li); err != nil {
			log.Fatalln(err)
		}
	}()
	// s.WaitDone()
	return nil
}

// WaitDone TODO
func (s *FileServer) WaitDone() error {
	for true {
		time.Sleep(5 * time.Second)
		idleDura := time.Now().Sub(s.lastActiveTime)
		if s.cw.Count() > 0 {
			logger.Info("server connections %d", s.cw.Count())
			s.lastActiveTime = time.Now()
		} else if idleDura > s.procMaxIdleDuration && s.cw.Count() == 0 && s.procMaxIdleDuration > 0 {
			logger.Info("server idle %s exceed max_idle_duration %s", idleDura, s.ProcMaxIdleDuration)
			s.server.Close()
			break
		} else {
			logger.Debug("server idle %v", idleDura)
		}
	}
	return nil
}

// OutputCtx TODO
func (s *FileServer) OutputCtx() error {
	if !s.PrintDownload {
		return nil
	}
	httpGet := backup_download.DFHttpComp{
		Params: backup_download.DFHttpParam{
			DFBase: backup_download.DFBase{
				BWLimitMB:   50,
				Concurrency: 1,
			},
			HttpGet: backup_download.HttpGet{
				Server:   fmt.Sprintf("http://%s%s", s.BindAddress, s.PathPrefix),
				PathTgt:  "/data/dbbak",
				FileList: []string{"xx", "yy"},
				AuthUser: s.AuthUser,
				AuthPass: s.AuthPass,
			},
		},
	}
	components.PrintOutputCtx(components.ToPrettyJson(httpGet))
	return nil
}

func (s *FileServer) handleBasicAuth(next http.HandlerFunc) http.HandlerFunc {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			w.WriteHeader(http.StatusMethodNotAllowed)
			return
		}
		// basicAuthPrefix := "Basic "
		// auth := r.Header.Get("Authorization")
		w.Header().Set("Content-Type", r.Header.Get("Content-Type"))
		u, p, ok := r.BasicAuth()
		if ok {
			if u == s.AuthUser && p == s.AuthPass {
				logger.Info("requested %s", r.URL)
				// w.WriteHeader(200)
				s.lastActiveTime = time.Now()
				if next != nil {
					next.ServeHTTP(w, r)
				}
				return
			}
		}
		w.Header().Set("WWW-Authenticate", `Basic realm="restricted", charset="UTF-8"`)
		// w.WriteHeader(http.StatusUnauthorized)
		http.Error(w, "Unauthorized BA", http.StatusUnauthorized)
	})
}

func aclHandler(acls []string, next http.HandlerFunc) http.HandlerFunc {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if err := checkACL(acls, nil, r.RemoteAddr); err != nil {
			http.Error(w, "Unauthorized IP", http.StatusUnauthorized)
			return
		}
		if next != nil {
			next.ServeHTTP(w, r)
		}
		return
	})
}

func (s *FileServer) addAcl(acl string) {
	// is acl valid?
	s.ACLs = append([]string{acl}, s.ACLs...)
}

var portRange []int = []int{12000, 19999}
var hostDefault = "localhost"

func getRandPort() string {
	diff := portRange[1] - portRange[0]
	port := rand.Intn(diff) + portRange[0]
	return strconv.Itoa(port)
}

// ConnectionWatcher TODO
type ConnectionWatcher struct {
	n int64
}

// OnStateChange records open connections in response to connection
// state changes. Set net/http Server.ConnState to this method
// as value.
func (cw *ConnectionWatcher) OnStateChange(conn net.Conn, state http.ConnState) {
	switch state {
	case http.StateNew:
		cw.Add(1)
	case http.StateHijacked, http.StateClosed:
		cw.Add(-1)
	}
}

// Count returns the number of connections at the time
// the call.
func (cw *ConnectionWatcher) Count() int {
	return int(atomic.LoadInt64(&cw.n))
}

// Add adds c to the number of active connections.
func (cw *ConnectionWatcher) Add(c int64) {
	atomic.AddInt64(&cw.n, c)
}

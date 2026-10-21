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

package main

import (
	"bytes"
	"context"
	"log"
	"net"
	"sync"
	"time"

	pb "go.etcd.io/etcd/api/v3/etcdserverpb"
	"go.etcd.io/etcd/api/v3/mvccpb"
	"google.golang.org/grpc"
	"google.golang.org/grpc/keepalive"
)

type etcdKV struct {
	value []byte
	lease int64
}

type etcdStore struct {
	mu       sync.Mutex
	rev      int64
	nextID   int64
	kvs      map[string]etcdKV
	leases   map[int64]int64
	endpoint string
}

func newEtcdStore(endpoint string) *etcdStore {
	return &etcdStore{
		kvs:      map[string]etcdKV{},
		leases:   map[int64]int64{},
		endpoint: endpoint,
		nextID:   1,
	}
}

func (s *etcdStore) header() *pb.ResponseHeader {
	return &pb.ResponseHeader{ClusterId: 1, MemberId: 1, Revision: s.rev, RaftTerm: 1}
}

func startEtcdMock(addr string) (*grpc.Server, net.Listener, error) {
	ln, err := net.Listen("tcp", addr)
	if err != nil {
		return nil, nil, err
	}
	store := newEtcdStore("http://" + addr)
	srv := grpc.NewServer(
		grpc.KeepaliveEnforcementPolicy(keepalive.EnforcementPolicy{
			MinTime:             5 * time.Second,
			PermitWithoutStream: true,
		}),
	)
	pb.RegisterKVServer(srv, store)
	pb.RegisterLeaseServer(srv, store)
	pb.RegisterWatchServer(srv, store)
	pb.RegisterClusterServer(srv, store)
	pb.RegisterMaintenanceServer(srv, store)
	go func() {
		_ = srv.Serve(ln)
	}()
	return srv, ln, nil
}

func (s *etcdStore) Range(_ context.Context, req *pb.RangeRequest) (*pb.RangeResponse, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	resp := &pb.RangeResponse{Header: s.header()}
	for key, item := range s.kvs {
		if !inRange(key, req.Key, req.RangeEnd) {
			continue
		}
		resp.Kvs = append(resp.Kvs, &mvccpb.KeyValue{
			Key: []byte(key), Value: item.value, ModRevision: s.rev, CreateRevision: s.rev, Version: 1,
		})
	}
	resp.Count = int64(len(resp.Kvs))
	return resp, nil
}

func (s *etcdStore) Put(_ context.Context, req *pb.PutRequest) (*pb.PutResponse, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.rev++
	s.kvs[string(req.Key)] = etcdKV{value: append([]byte(nil), req.Value...), lease: req.Lease}
	return &pb.PutResponse{Header: s.header()}, nil
}

func (s *etcdStore) DeleteRange(_ context.Context, req *pb.DeleteRangeRequest) (*pb.DeleteRangeResponse, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	var deleted int64
	for key := range s.kvs {
		if inRange(key, req.Key, req.RangeEnd) {
			delete(s.kvs, key)
			deleted++
		}
	}
	s.rev++
	return &pb.DeleteRangeResponse{Header: s.header(), Deleted: deleted}, nil
}

func (s *etcdStore) Txn(_ context.Context, _ *pb.TxnRequest) (*pb.TxnResponse, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.rev++
	return &pb.TxnResponse{Header: s.header(), Succeeded: true}, nil
}

func (s *etcdStore) Compact(_ context.Context, _ *pb.CompactionRequest) (*pb.CompactionResponse, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	return &pb.CompactionResponse{Header: s.header()}, nil
}

func (s *etcdStore) LeaseGrant(_ context.Context, req *pb.LeaseGrantRequest) (*pb.LeaseGrantResponse, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.nextID++
	ttl := req.TTL
	if ttl <= 0 {
		ttl = 60
	}
	s.leases[s.nextID] = ttl
	return &pb.LeaseGrantResponse{Header: s.header(), ID: s.nextID, TTL: ttl}, nil
}

func (s *etcdStore) LeaseRevoke(_ context.Context, req *pb.LeaseRevokeRequest) (*pb.LeaseRevokeResponse, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.leases, req.ID)
	for key, item := range s.kvs {
		if item.lease == req.ID {
			delete(s.kvs, key)
		}
	}
	s.rev++
	return &pb.LeaseRevokeResponse{Header: s.header()}, nil
}

func (s *etcdStore) LeaseKeepAlive(stream pb.Lease_LeaseKeepAliveServer) error {
	for {
		req, err := stream.Recv()
		if err != nil {
			return err
		}
		s.mu.Lock()
		ttl := s.leases[req.ID]
		if ttl == 0 {
			ttl = 60
			s.leases[req.ID] = ttl
		}
		s.mu.Unlock()
		if err := stream.Send(&pb.LeaseKeepAliveResponse{ID: req.ID, TTL: ttl}); err != nil {
			return err
		}
	}
}

func (s *etcdStore) LeaseTimeToLive(_ context.Context, req *pb.LeaseTimeToLiveRequest) (*pb.LeaseTimeToLiveResponse, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	ttl := s.leases[req.ID]
	if ttl == 0 {
		ttl = 60
	}
	return &pb.LeaseTimeToLiveResponse{Header: s.header(), ID: req.ID, TTL: ttl, GrantedTTL: ttl}, nil
}

func (s *etcdStore) LeaseLeases(context.Context, *pb.LeaseLeasesRequest) (*pb.LeaseLeasesResponse, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	resp := &pb.LeaseLeasesResponse{Header: s.header()}
	for id := range s.leases {
		resp.Leases = append(resp.Leases, &pb.LeaseStatus{ID: id})
	}
	return resp, nil
}

func (s *etcdStore) Watch(stream pb.Watch_WatchServer) error {
	var next int64
	for {
		req, err := stream.Recv()
		if err != nil {
			return err
		}
		if req.GetCreateRequest() == nil {
			continue
		}
		next++
		if err := stream.Send(&pb.WatchResponse{Header: s.header(), WatchId: next, Created: true}); err != nil {
			return err
		}
	}
}

func (s *etcdStore) MemberAdd(context.Context, *pb.MemberAddRequest) (*pb.MemberAddResponse, error) {
	return &pb.MemberAddResponse{Header: s.header()}, nil
}

func (s *etcdStore) MemberRemove(context.Context, *pb.MemberRemoveRequest) (*pb.MemberRemoveResponse, error) {
	return &pb.MemberRemoveResponse{Header: s.header()}, nil
}

func (s *etcdStore) MemberUpdate(context.Context, *pb.MemberUpdateRequest) (*pb.MemberUpdateResponse, error) {
	return &pb.MemberUpdateResponse{Header: s.header()}, nil
}

func (s *etcdStore) MemberList(context.Context, *pb.MemberListRequest) (*pb.MemberListResponse, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	return &pb.MemberListResponse{
		Header: s.header(),
		Members: []*pb.Member{{
			ID: 1, Name: "ha-sandbox-mock", ClientURLs: []string{s.endpoint}, PeerURLs: []string{s.endpoint},
		}},
	}, nil
}

func (s *etcdStore) MemberPromote(context.Context, *pb.MemberPromoteRequest) (*pb.MemberPromoteResponse, error) {
	return &pb.MemberPromoteResponse{Header: s.header()}, nil
}

func (s *etcdStore) Alarm(context.Context, *pb.AlarmRequest) (*pb.AlarmResponse, error) {
	return &pb.AlarmResponse{Header: s.header()}, nil
}

func (s *etcdStore) Status(context.Context, *pb.StatusRequest) (*pb.StatusResponse, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	return &pb.StatusResponse{Header: s.header(), Version: "3.6.0", DbSize: 1, Leader: 1}, nil
}

func (s *etcdStore) Defragment(context.Context, *pb.DefragmentRequest) (*pb.DefragmentResponse, error) {
	return &pb.DefragmentResponse{Header: s.header()}, nil
}

func (s *etcdStore) Hash(context.Context, *pb.HashRequest) (*pb.HashResponse, error) {
	return &pb.HashResponse{Header: s.header(), Hash: 1}, nil
}

func (s *etcdStore) HashKV(context.Context, *pb.HashKVRequest) (*pb.HashKVResponse, error) {
	return &pb.HashKVResponse{Header: s.header(), Hash: 1}, nil
}

func (s *etcdStore) Snapshot(*pb.SnapshotRequest, pb.Maintenance_SnapshotServer) error {
	return nil
}

func (s *etcdStore) MoveLeader(context.Context, *pb.MoveLeaderRequest) (*pb.MoveLeaderResponse, error) {
	return &pb.MoveLeaderResponse{Header: s.header()}, nil
}

func (s *etcdStore) Downgrade(context.Context, *pb.DowngradeRequest) (*pb.DowngradeResponse, error) {
	return &pb.DowngradeResponse{Header: s.header(), Version: "3.6.0"}, nil
}

func inRange(key string, start, end []byte) bool {
	if len(end) == 0 {
		return key == string(start)
	}
	kb := []byte(key)
	return bytes.Compare(kb, start) >= 0 && bytes.Compare(kb, end) < 0
}

func logEtcdReady(addr string) {
	log.Printf("etcd mock ready, addr: %s", addr)
}

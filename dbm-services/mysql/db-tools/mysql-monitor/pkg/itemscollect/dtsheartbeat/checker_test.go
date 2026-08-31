package dtsheartbeat

import (
	"net"
	"testing"
)

func TestProbeAddr_Closed(t *testing.T) {
	if ProbeAddr("127.0.0.2", 1) {
		t.Fatal("unused low port should be down")
	}
}

func TestProbeAddr_Empty(t *testing.T) {
	if ProbeAddr("", 18301) {
		t.Fatal("empty ip should be down")
	}
}

func TestProbeAddr_Listen(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer ln.Close()
	port := ln.Addr().(*net.TCPAddr).Port
	if !ProbeAddr("127.0.0.1", port) {
		t.Fatalf("listening 127.0.0.1:%d should be up", port)
	}
}

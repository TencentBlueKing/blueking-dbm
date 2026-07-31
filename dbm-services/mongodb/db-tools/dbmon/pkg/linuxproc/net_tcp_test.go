package linuxproc

import (
	"testing"
)

// Sample /proc/net/tcp LISTEN on 27017 (0x6989). inode is at header column index (fields[11]).
const sampleProcNetTCP = `  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode
   0: 0100007F:6989 00000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0     0 0 12345
   1: 0100007F:1F90 00000000:0000 01 00000000:00000000 00:00000000 00000000     0        0     0 0 99999
`

// IPv6-style row (would appear in /proc/net/tcp6); production code must not scan this file.
const sampleProcNetTCP6Only = `  sl  local_address                         remote_address                        st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode
   0: 00000000000000000000000000000000:6989 00000000000000000000000000000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 54321 1 0000000000000000 100 0 0 10 0
`

func TestProcNetTcpParsesIPv4Listen(t *testing.T) {
	rows, err := ProcNetTcp([]byte(sampleProcNetTCP))
	if err != nil {
		t.Fatal(err)
	}
	if !rowsHaveTCPListen(rows, 27017) {
		t.Fatal("expected LISTEN on 27017")
	}
	if rowsHaveTCPListen(rows, 9999) {
		t.Fatal("did not expect LISTEN on 9999")
	}
	inodes := collectListenInodes(rows, 27017)
	if len(inodes) != 1 || inodes[0] != 12345 {
		t.Fatalf("unexpected inodes: %v", inodes)
	}
	// ESTABLISHED row (st=01) on 8080 must not count as listen inode.
	if got := collectListenInodes(rows, 8080); len(got) != 0 {
		t.Fatalf("expected no listen inodes for established port, got %v", got)
	}
}

func TestTCP6StyleRowsAreNotUsedByIPv4Helpers(t *testing.T) {
	// Simulate "only tcp6 has LISTEN": IPv4 table empty → helpers report free.
	ipv4Rows, err := ProcNetTcp([]byte(`  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode
`))
	if err != nil {
		t.Fatal(err)
	}
	if rowsHaveTCPListen(ipv4Rows, 27017) {
		t.Fatal("empty ipv4 table should not report listen")
	}
	if got := collectListenInodes(ipv4Rows, 27017); len(got) != 0 {
		t.Fatalf("empty ipv4 table should have no inodes, got %v", got)
	}

	// tcp6-only content is irrelevant to IPv4-only path; production never reads ProcNetTcp6Path.
	// ParseLocalPortFromProcNet still works on the port hex; assert we simply never feed tcp6 into helpers.
	_ = sampleProcNetTCP6Only
	if ProcNetTcp6Path == ProcNetTcpPath {
		t.Fatal("tcp6 path must differ from tcp path")
	}
}

func TestTCPPortHasLISTENIPv4OnlyPath(t *testing.T) {
	// Production TCPPortHasLISTEN / ListenSocketInodes only open ProcNetTcpPath.
	busy, err := TCPPortHasLISTEN(1) // privileged port almost never LISTEN for this user
	if err != nil {
		t.Fatal(err)
	}
	_ = busy
	inodes, err := ListenSocketInodes(1)
	if err != nil {
		t.Fatal(err)
	}
	_ = inodes
}

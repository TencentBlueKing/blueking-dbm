package linuxproc

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
)

// TCPListenPID returns one PID that has a TCP LISTEN socket on port, or 0 if none is visible.
// It first maps socket inodes from /proc/net/tcp{,6} to PIDs via /proc/*/fd (cheap when it works).
// If that yields no PID (e.g. cannot read another user's fds), it falls back to parsing `ss -ltnp`
// or `netstat -ntpl`, which report listeners on any local address (127.0.0.1, eth*, ::1, etc.).
// Cost of fallback is similar to one shell pipeline; avoid calling in hot loops when possible.
func TCPListenPID(port int) (int, error) {
	inodes, err := ListenSocketInodes(port)
	if err != nil {
		return 0, err
	}
	for _, ino := range inodes {
		pid, err := pidOwningSocketInode(ino)
		if err != nil {
			return 0, err
		}
		if pid > 0 {
			return pid, nil
		}
	}
	return tcpListenPIDFallback(port), nil
}

var ssPidRE = regexp.MustCompile(`\bpid=(\d+)`)

// tcpListenPIDFallback resolves PID from ss(8) or netstat when inode→pid walk fails or misses listeners.
func tcpListenPIDFallback(port int) int {
	if pid := pidFromSsListen(port); pid > 0 {
		return pid
	}
	return pidFromNetstatListen(port)
}

func pidFromSsListen(port int) int {
	out, err := exec.Command("ss", "-ltnp").Output()
	if err != nil {
		return 0
	}
	for _, line := range strings.Split(string(out), "\n") {
		if !strings.Contains(line, "LISTEN") {
			continue
		}
		if !lineContainsListenPort(line, port) {
			continue
		}
		if m := ssPidRE.FindStringSubmatch(line); len(m) == 2 {
			pid, err := strconv.Atoi(m[1])
			if err == nil && pid > 0 {
				return pid
			}
		}
	}
	return 0
}

var netstatPidRE = regexp.MustCompile(`(\d+)/[\w.-]+\s*$`)

func pidFromNetstatListen(port int) int {
	out, err := exec.Command("netstat", "-ntpl").Output()
	if err != nil {
		return 0
	}
	for _, line := range strings.Split(string(out), "\n") {
		if !strings.Contains(line, "LISTEN") {
			continue
		}
		if !lineContainsListenPort(line, port) {
			continue
		}
		fields := strings.Fields(line)
		if len(fields) == 0 {
			continue
		}
		last := fields[len(fields)-1]
		if m := netstatPidRE.FindStringSubmatch(last); len(m) == 2 {
			pid, err := strconv.Atoi(m[1])
			if err == nil && pid > 0 {
				return pid
			}
		}
	}
	return 0
}

// lineContainsListenPort matches local LISTEN address:port without substring false positives (e.g. :128017).
func lineContainsListenPort(line string, port int) bool {
	wantSuffix := fmt.Sprintf(":%d", port)
	fields := strings.Fields(line)
	for _, f := range fields {
		if strings.HasPrefix(f, "users:") {
			break
		}
		if p, ok := localPortFromAddrToken(f); ok && p == port {
			return true
		}
	}
	// Defensive: substring only when port appears as :<port> boundary (not 128017).
	if !strings.Contains(line, wantSuffix) {
		return false
	}
	idx := strings.Index(line, wantSuffix)
	if idx <= 0 {
		return false
	}
	// Require ':' before port digits
	if line[idx-1] != ':' {
		return false
	}
	after := idx + len(wantSuffix)
	if after < len(line) && line[after] != ' ' && line[after] != '\t' {
		return false
	}
	return true
}

// localPortFromAddrToken parses port from tokens like 127.0.0.1:28017, [::1]:28017, [fe80::1]:27017
func localPortFromAddrToken(tok string) (int, bool) {
	if tok == "" || strings.HasPrefix(tok, "users:") {
		return 0, false
	}
	if strings.HasPrefix(tok, "[") {
		i := strings.LastIndex(tok, "]:")
		if i < 0 {
			return 0, false
		}
		p, err := strconv.Atoi(tok[i+2:])
		if err != nil {
			return 0, false
		}
		return p, true
	}
	i := strings.LastIndex(tok, ":")
	if i <= 0 {
		return 0, false
	}
	p, err := strconv.Atoi(tok[i+1:])
	if err != nil {
		return 0, false
	}
	return p, true
}

func pidOwningSocketInode(inode int64) (int, error) {
	target := fmt.Sprintf("socket:[%d]", inode)
	ents, err := os.ReadDir("/proc")
	if err != nil {
		return 0, err
	}
	for _, ent := range ents {
		name := ent.Name()
		if !isNumericProcDir(name) {
			continue
		}
		fdDir := filepath.Join("/proc", name, "fd")
		fds, err := os.ReadDir(fdDir)
		if err != nil {
			continue
		}
		for _, fd := range fds {
			link, err := os.Readlink(filepath.Join(fdDir, fd.Name()))
			if err != nil {
				continue
			}
			if link == target {
				pid, err := strconv.Atoi(name)
				if err != nil {
					continue
				}
				return pid, nil
			}
		}
	}
	return 0, nil
}

func isNumericProcDir(name string) bool {
	if name == "" {
		return false
	}
	for _, c := range name {
		if c < '0' || c > '9' {
			return false
		}
	}
	return true
}

package linuxproc

import (
	"fmt"
	"os"
	"path/filepath"
	"strconv"
)

// TCPListenPID returns one PID that has a TCP LISTEN socket on port, or 0 if none is visible
// (e.g. no listener, or no permission to scan other users' /proc entries).
// Cost is similar to lsof -i:$port (walks /proc/*/fd); do not call in tight loops.
// To poll whether a port still has a listener, prefer ListenSocketInodes (IPv4 /proc/net/tcp only)
// instead of resolving PID each time.
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
	return 0, nil
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

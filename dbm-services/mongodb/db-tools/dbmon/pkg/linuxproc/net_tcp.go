package linuxproc

// Package linuxproc  用于分析 linux proc下的文件

import (
	"bufio"
	"bytes"
	"fmt"
	"os"
	"strconv"
	"strings"

	"github.com/pkg/errors"
)

// NetTcp https://www.kernel.org/doc/Documentation/networking/proc_net_tcp.txt
type NetTcp struct {
	Fields         []string
	Sl             int
	LocalHost      string
	LocalPort      int
	RemoteHost     string
	RemotePort     int
	St             int
	TxQueue        string
	RxQueue        string
	Tr             string
	TrWhen         string
	Retrnsmt       string
	Uid            int
	Timeout        int
	Inode          int64
	SocketRefCount int
}

// IsListen 是否是监听状态
func (row *NetTcp) IsListen() bool {
	return row.St == LISTEN
}

// IsLoAddr 是否是本地地址
func (row *NetTcp) IsLoAddr() bool {
	return row.LocalHost == "127.0.0.1"
}

// LocalPeer 本地地址
func (row *NetTcp) LocalPeer() string {
	return fmt.Sprintf("%s:%d", row.LocalHost, row.LocalPort)
}

// InetNtoA 将uint64的ip转换为字符串
func InetNtoA(ip uint64) string {
	return fmt.Sprintf("%d.%d.%d.%d",
		byte(ip>>24), byte(ip>>16), byte(ip>>8), byte(ip))
}

// ParseHexAddr 解析hex格式的地址
func ParseHexAddr(host string) (ip string, port int, err error) {
	fs := strings.Split(host, ":")
	if len(fs) != 2 {
		return "", 0, errors.Errorf("bad input '%s'", host)
	}
	if len(fs[0]) != 8 {
		return "", 0, errors.Errorf("bad input '%s'", host)
	}
	b := []byte(fs[0])
	fs[0] = fmt.Sprintf("%s%s%s%s", b[6:8], b[4:6], b[2:4], b[0:2])

	n, err := strconv.ParseUint(fs[0], 16, 64)
	if err != nil {
		return "", 0, err
	}
	ip = InetNtoA(n)

	n2, err := strconv.ParseInt(fs[1], 16, 32)
	if err != nil {
		return "", 0, err
	}
	port = int(n2)

	return

}

// ParseLocalPortFromProcNet parses the local_address column from /proc/net/tcp.
// IPv4 example: 0100007F:0271
func ParseLocalPortFromProcNet(localField string) (int, error) {
	i := strings.LastIndex(localField, ":")
	if i < 0 {
		return 0, errors.Errorf("no port in %q", localField)
	}
	n, err := strconv.ParseInt(localField[i+1:], 16, 32)
	if err != nil {
		return 0, errors.Wrap(err, "parse port hex")
	}
	return int(n), nil
}

func inodeColumnIndex(headerFields []string) int {
	for i, h := range headerFields {
		if strings.EqualFold(strings.TrimSpace(h), "inode") {
			return i
		}
	}
	return -1
}

func parseSlField(slField string) int {
	s := strings.TrimSuffix(slField, ":")
	n, _ := strconv.Atoi(s)
	return n
}

const (
	// ProcNetTcpPath IPv4 TCP socket table
	ProcNetTcpPath = "/proc/net/tcp"
	// ProcNetTcp6Path IPv6 TCP socket table
	ProcNetTcp6Path = "/proc/net/tcp6"
)

const ESTABLISHED = 1
const LISTEN = 10

// ProcNetTcp 读取/proc/net/tcp文件
func ProcNetTcp(input []byte) (rows []NetTcp, err error) {
	return procNetTcpRead(ProcNetTcpPath, input)
}

func procNetTcpRead(path string, input []byte) (rows []NetTcp, err error) {
	var scanner *bufio.Scanner
	if input == nil {
		fh, openErr := os.Open(path)
		if openErr != nil {
			if os.IsNotExist(openErr) {
				return nil, nil
			}
			return nil, errors.Wrap(openErr, "open "+path)
		}
		defer fh.Close()
		scanner = bufio.NewScanner(fh)
	} else {
		scanner = bufio.NewScanner(bytes.NewReader(input))
	}

	inodeIdx := -1
	nLine := 0
	for scanner.Scan() {
		nLine++
		line := scanner.Text()
		fields := strings.Fields(line)
		if len(fields) < 4 {
			continue
		}

		if nLine == 1 {
			if fields[0] != "sl" {
				return nil, errors.New("bad proc net tcp header")
			}
			inodeIdx = inodeColumnIndex(fields)
			continue
		}

		row := NetTcp{}
		row.Fields = fields
		row.Sl = parseSlField(fields[0])

		lp, errLP := ParseLocalPortFromProcNet(fields[1])
		if errLP != nil {
			continue
		}
		row.LocalPort = lp

		if lh, _, e := ParseHexAddr(fields[1]); e == nil {
			row.LocalHost = lh
		}

		if rh, rp, e := ParseHexAddr(fields[2]); e == nil {
			row.RemoteHost = rh
			row.RemotePort = rp
		}

		v, errSt := strconv.ParseUint(fields[3], 16, 8)
		if errSt != nil {
			continue
		}
		row.St = int(v)

		if inodeIdx >= 0 && len(fields) > inodeIdx {
			row.Inode, _ = strconv.ParseInt(fields[inodeIdx], 10, 64)
		} else if len(fields) >= 4 {
			// Header missing "inode" on some kernels/images: inode is usually the last numeric column.
			if n, err := strconv.ParseInt(fields[len(fields)-1], 10, 64); err == nil && n > 0 {
				row.Inode = n
			}
		}

		rows = append(rows, row)
	}
	if scanErr := scanner.Err(); scanErr != nil {
		return rows, scanErr
	}
	return rows, nil
}

// TCPPortHasLISTEN reports whether /proc/net/tcp or tcp6 has any row in TCP LISTEN on local port.
// Unlike ListenSocketInodes, it does not require a non-zero socket inode (fixes false "port free"
// when the inode column is missing or not parsed).
func TCPPortHasLISTEN(port int) (bool, error) {
	for _, path := range []string{ProcNetTcpPath, ProcNetTcp6Path} {
		tcpRows, err := procNetTcpRead(path, nil)
		if err != nil {
			return false, err
		}
		for _, row := range tcpRows {
			if row.LocalPort == port && row.IsListen() {
				return true, nil
			}
		}
	}
	return false, nil
}

// ListenSocketInodes returns socket inodes in TCP LISTEN on local port.
func ListenSocketInodes(port int) ([]int64, error) {
	var inodes []int64
	seen := map[int64]struct{}{}
	for _, path := range []string{ProcNetTcpPath, ProcNetTcp6Path} {
		tcpRows, err := procNetTcpRead(path, nil)
		if err != nil {
			return nil, err
		}
		for _, row := range tcpRows {
			if row.LocalPort != port || !row.IsListen() || row.Inode <= 0 {
				continue
			}
			if _, ok := seen[row.Inode]; ok {
				continue
			}
			seen[row.Inode] = struct{}{}
			inodes = append(inodes, row.Inode)
		}
	}
	return inodes, nil
}

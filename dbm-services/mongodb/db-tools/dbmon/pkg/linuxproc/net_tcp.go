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

const ProcNetTcpPath = "/proc/net/tcp"
const ESTABLISHED = 1
const LISTEN = 10

// ProcNetTcp 读取/proc/net/tcp文件
func ProcNetTcp(input []byte) (rows []NetTcp, err error) {
	var fh *os.File
	var scanner *bufio.Scanner

	if input == nil {
		fh, err = os.Open(ProcNetTcpPath)
		if err != nil {
			panic(err)
		}
		scanner = bufio.NewScanner(fh)
	} else {
		scanner = bufio.NewScanner(bytes.NewReader(input))
	}

	nLine := 0
	for scanner.Scan() {
		nLine++
		line := scanner.Text()
		row := NetTcp{}
		row.Fields = strings.Fields(line)

		if nLine == 1 {
			if row.Fields[0] != "sl" {
				return nil, errors.New("bad input")
			}
			continue
		}

		row.Fields = strings.Fields(line)
		row.Sl, _ = strconv.Atoi(row.Fields[0])
		row.LocalHost, row.LocalPort, err = ParseHexAddr(row.Fields[1])
		row.RemoteHost, row.RemotePort, err = ParseHexAddr(row.Fields[2])
		v, _ := strconv.ParseUint(row.Fields[3], 16, 8)
		row.St = int(v)
		rows = append(rows, row)
	}
	return rows, nil
}

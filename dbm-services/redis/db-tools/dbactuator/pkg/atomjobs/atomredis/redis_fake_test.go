package atomredis

import (
	"bufio"
	"fmt"
	"io"
	"net"
	"strconv"
	"strings"
	"sync"
	"testing"
)

// fakeRedis 一个只够改密码探测用的 RESP 服务端.
//
// 探测的整条链路都在 go-redis 里面: 密码错不错、返回的是 WRONGPASS 还是 NOAUTH、错误文案
// 被包了几层之后还认不认得出来. 这些拿假 client 替不掉, 只能起个真的说 RESP 的东西.
type fakeRedis struct {
	ln       net.Listener
	password string // 期望的密码, 空串表示实例没设密码
	info     string // INFO 的返回内容
	mu       sync.Mutex
	config   map[string]string // CONFIG GET/SET 的存储
	commands []string          // 收到过的命令, 用来断言"到底做没做那一步"
}

func newFakeRedis(t *testing.T, password string) *fakeRedis {
	t.Helper()
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen failed:%v", err)
	}
	f := &fakeRedis{ln: ln, password: password, config: map[string]string{}}
	go f.serve()
	t.Cleanup(func() { _ = ln.Close() })
	return f
}

func (f *fakeRedis) addr() string { return f.ln.Addr().String() }

func (f *fakeRedis) hostPort() (string, string) {
	host, port, _ := net.SplitHostPort(f.addr())
	return host, port
}

func (f *fakeRedis) setConfig(name, val string) {
	f.mu.Lock()
	defer f.mu.Unlock()
	f.config[name] = val
}

func (f *fakeRedis) got(prefix string) bool {
	f.mu.Lock()
	defer f.mu.Unlock()
	for _, cmd := range f.commands {
		if strings.HasPrefix(strings.ToUpper(cmd), strings.ToUpper(prefix)) {
			return true
		}
	}
	return false
}

func (f *fakeRedis) serve() {
	for {
		conn, err := f.ln.Accept()
		if err != nil {
			return
		}
		go f.handle(conn)
	}
}

func (f *fakeRedis) handle(conn net.Conn) {
	defer conn.Close()
	r := bufio.NewReader(conn)
	authed := f.password == ""
	for {
		args, err := readRESPCommand(r)
		if err != nil {
			return
		}
		f.mu.Lock()
		f.commands = append(f.commands, strings.Join(args, " "))
		f.mu.Unlock()

		cmd := strings.ToUpper(args[0])
		if cmd == "AUTH" {
			switch {
			case f.password == "":
				// 对端没设密码却收到 AUTH: 改成无密码的单据里, 主库先改完就是这一种
				io.WriteString(conn, "-ERR Client sent AUTH, but no password is set\r\n")
			case len(args) < 2 || args[1] != f.password:
				io.WriteString(conn, "-WRONGPASS invalid username-password pair\r\n")
			default:
				authed = true
				io.WriteString(conn, "+OK\r\n")
			}
			continue
		}
		if !authed {
			io.WriteString(conn, "-NOAUTH Authentication required.\r\n")
			continue
		}
		f.dispatch(conn, cmd, args)
	}
}

func (f *fakeRedis) dispatch(conn net.Conn, cmd string, args []string) {
	switch {
	case cmd == "PING":
		io.WriteString(conn, "+PONG\r\n")
	case cmd == "INFO":
		io.WriteString(conn, fmt.Sprintf("$%d\r\n%s\r\n", len(f.info), f.info))
	case cmd == "CONFIG" && len(args) >= 3 && strings.EqualFold(args[1], "get"):
		f.mu.Lock()
		val := f.config[strings.ToLower(args[2])]
		f.mu.Unlock()
		io.WriteString(conn, fmt.Sprintf("*2\r\n$%d\r\n%s\r\n$%d\r\n%s\r\n",
			len(args[2]), args[2], len(val), val))
	case cmd == "CONFIG" && len(args) >= 4 && strings.EqualFold(args[1], "set"):
		f.setConfig(strings.ToLower(args[2]), args[3])
		io.WriteString(conn, "+OK\r\n")
	default:
		io.WriteString(conn, "+OK\r\n")
	}
}

// readRESPCommand 读一条 inline array 形式的命令, 客户端发出来的都是这个形状
func readRESPCommand(r *bufio.Reader) ([]string, error) {
	header, err := readRESPLine(r)
	if err != nil {
		return nil, err
	}
	if !strings.HasPrefix(header, "*") {
		return nil, fmt.Errorf("want an array header,got %q", header)
	}
	n, err := strconv.Atoi(header[1:])
	if err != nil || n <= 0 {
		return nil, fmt.Errorf("bad array header %q", header)
	}
	args := make([]string, 0, n)
	for i := 0; i < n; i++ {
		bulk, err := readRESPLine(r)
		if err != nil {
			return nil, err
		}
		if !strings.HasPrefix(bulk, "$") {
			return nil, fmt.Errorf("want a bulk header,got %q", bulk)
		}
		size, err := strconv.Atoi(bulk[1:])
		if err != nil {
			return nil, fmt.Errorf("bad bulk header %q", bulk)
		}
		buf := make([]byte, size+2) // 连同结尾的 CRLF 一起读掉
		if _, err = io.ReadFull(r, buf); err != nil {
			return nil, err
		}
		args = append(args, string(buf[:size]))
	}
	return args, nil
}

func readRESPLine(r *bufio.Reader) (string, error) {
	line, err := r.ReadString('\n')
	if err != nil {
		return "", err
	}
	return strings.TrimRight(line, "\r\n"), nil
}

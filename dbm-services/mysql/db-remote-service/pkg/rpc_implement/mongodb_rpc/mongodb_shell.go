package mongodb_rpc

import (
	"bytes"
	"context"
	"fmt"
	"log/slog"
	"net/url"
	"os"
	"os/exec"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/pkg/errors"
)

const ClusterTypeReplicaSet = "MongoReplicaSet"
const ClusterTypeShardedCluster = "MongoShardedCluster"
const EndOfOutput = "_e70725970764b32aa7f8ba468944535f_"
const ConnectToServerMsg = "connect to server, default db is test\n"

var CheckInputError = errors.New("invalid input")

// mongoshPromptPrefix matches only known interactive prompts, e.g.:
//
//	[direct: mongos] test>
//	utRs44Prompt [direct: primary] test>
//	utRs44Prompt [direct: secondary] test>
//	utRs44Prompt [primary] test>
//	PRIMARY> / SECONDARY>
//
// Intentionally narrow: lines like "score> 10" or "n> 5" must not be stripped.
// After "direct:" there is exactly one space (mongosh format).
var mongoshPromptPrefix = regexp.MustCompile(
	`^(?:(?:[A-Za-z0-9_.$-]+\s+)?\[(?:direct: )?(?:primary|secondary|mongos)\]\s+[A-Za-z0-9_.$-]+|(?:PRIMARY|SECONDARY|ARBITER))>\s?`,
)

// stripMongoShellPrompt removes interactive shell prompts from command output.
// Output is split by '\n'; each line is stripped at most once (line-start match only).
// Empty prompt-only lines are dropped; trailing blank lines are trimmed.
func stripMongoShellPrompt(out []byte) []byte {
	if len(out) == 0 {
		return out
	}
	lines := strings.Split(string(out), "\n")
	cleaned := make([]string, 0, len(lines))
	for _, line := range lines {
		stripped := line
		if loc := mongoshPromptPrefix.FindStringIndex(line); loc != nil {
			stripped = line[loc[1]:]
			if stripped == "" {
				continue
			}
		}
		cleaned = append(cleaned, stripped)
	}
	for len(cleaned) > 0 && cleaned[len(cleaned)-1] == "" {
		cleaned = cleaned[:len(cleaned)-1]
	}
	if len(cleaned) == 0 {
		return []byte{}
	}
	return []byte(strings.Join(cleaned, "\n") + "\n")
}

type MongoHost struct {
	Host          string
	Port          int
	UserName      string
	Password      string
	SetName       string
	AdminUsername string
	AdminPassword string
	RealRtxId     string // 真实的RTX ID
}

func EncodeURIComponent(str string) string {
	str = url.QueryEscape(str)
	str = strings.Replace(str, "+", "%20", -1)
	return str
}

func (h *MongoHost) Uri() string {
	if h.SetName == "" {
		return fmt.Sprintf("mongodb://%s:%s@%s/test?authSource=admin&appname=webconsole_%s",
			h.UserName, EncodeURIComponent(h.Password), h.Host, h.RealRtxId)
	} else {
		// 副本集, replicaSet=SetName不加时，可以直接连Secondary
		return fmt.Sprintf(
			"mongodb://%s:%s@%s/test?authSource=admin&appname=webconsole_%s",
			h.UserName, EncodeURIComponent(h.Password), h.Host, h.RealRtxId)
	}
}

// MongoShell is a routine that can be run and stopped.
type MongoShell struct {
	logger        *slog.Logger
	ProcessStdin  *os.File
	ProcessOutBuf []byte
	OutBuf        []byte
	Cmd           string
	BufChan       chan []byte
	Pid           int
	StopChan      chan struct{}
	MongoHost     MongoHost
	ClusterType   string
	MongoVersion  string
	ShellBin      string // mongo or mongosh
	ReadPref      string // primary,secondary,nearest,direct
	OneOff        int
}

// NewMongoShellFromParm create a new MongoShell instance
func NewMongoShellFromParm(p *QueryParams) *MongoShell {
	setName := ""
	if p.ClusterType == ClusterTypeReplicaSet {
		setName = p.SetName
	}
	return &MongoShell{
		BufChan:      make(chan []byte, 2),
		StopChan:     make(chan struct{}, 1),
		ClusterType:  p.ClusterType,
		MongoVersion: p.Version,
		MongoHost: MongoHost{
			Host:          p.Addresses[0], // 只取第一个地址
			UserName:      p.UserName,
			Password:      p.Password,
			SetName:       setName,
			AdminUsername: p.AdminUsername,
			AdminPassword: p.AdminPassword,
			RealRtxId:     p.OaUser,
		},
		ReadPref: p.ReadPreference,
		OneOff:   p.OneOff,
	}
}

// parseMongoVersion parses the MongoDB version string.
func parseMongoVersion(version string) (major, minor int, err error) {
	if strings.Contains(version, "-") {
		fs := strings.Split(version, "-")
		if len(fs) >= 2 {
			version = fs[1]
		} else {
			return 0, 0, fmt.Errorf("invalid version string")
		}
	}
	fs := strings.Split(version, ".")
	if len(fs) < 2 {
		return 0, 0, fmt.Errorf("invalid version string")
	}

	major, err = strconv.Atoi(fs[0])
	if err != nil {
		return 0, 0, fmt.Errorf("invalid major version")
	}
	minor, err = strconv.Atoi(fs[1])
	if err != nil {
		return 0, 0, fmt.Errorf("invalid minor version")
	}
	return
}

func mongoShellMissingHint(shellBin, mongoVersion string) string {
	switch shellBin {
	case "mongo":
		return fmt.Sprintf(
			"未找到 mongo 命令（集群版本 %s，MongoDB <4.4 需 legacy mongo shell）。请在 db-remote-service 节点安装 mongo 并加入 PATH",
			mongoVersion,
		)
	case "mongosh":
		return fmt.Sprintf(
			"未找到 mongosh 命令（集群版本 %s，MongoDB >=4.4 需 mongosh）。请在 db-remote-service 节点安装 mongosh 并加入 PATH",
			mongoVersion,
		)
	default:
		return fmt.Sprintf("未找到 MongoDB shell 命令 %q", shellBin)
	}
}

func resolveMongoShellBin(shellBin, mongoVersion string) (string, error) {
	cmdPath, err := exec.LookPath(shellBin)
	if err != nil {
		return "", fmt.Errorf("%s: %w", mongoShellMissingHint(shellBin, mongoVersion), err)
	}
	return cmdPath, nil
}

// buildArgs builds the arguments for the MongoShell process.
// 不同的版本，shell和参数都不同
func buildArgs(r *MongoShell) (argv []string, err error) {
	major, minor, err := parseMongoVersion(r.MongoVersion)
	if err != nil {
		return nil, fmt.Errorf("invalid version string")
	}

	// 4.4 之前的版本使用 legacy mongo shell；>=4.4 使用 mongosh
	isLowerVersion := major < 4 || (major == 4 && minor < 4)

	if isLowerVersion {
		r.ShellBin = "mongo"
	} else {
		r.ShellBin = "mongosh"
	}

	evalJs := ""
	isMongos := r.MongoHost.SetName == ""

	/*
		ReadPref:
		- "" 默认 secondary
		- secondary = "secondary" >=3节点
		- secondaryPreferred = "secondaryPreferred" <3节点在primary上执行
	*/
	switch r.ReadPref {
	case "secondary", "":
		if isMongos {
			// 分片集群，总是先执行一次 setReadPref secondary
			evalJs = "db.getMongo().setReadPref('secondary');"
		} else {
			// 副本集，4.2 之前的版本，使用 setSlaveOk
			if isLowerVersion {
				evalJs = "db.getMongo().setSecondaryOk(true);"
			} else {
				evalJs = "db.getMongo().setReadPref('secondary');"
			}
		}
	case "direct":
		evalJs = ""
	default: // secondaryPreferred, < 3节点, 允许在primary上执行

		// 分片集群: setReadPref secondaryPreferred
		if isMongos {
			evalJs = "db.getMongo().setReadPref('secondaryPreferred');"
		} else {
			// 副本集: 4.2 之前的版本，使用 setSecondaryOk
			if isLowerVersion {
				evalJs = "if (! db.isMaster().ismaster) {db.getMongo().setSecondaryOk(true);}"
			} else {
				evalJs = "if (! db.isMaster().ismaster) {db.getMongo().setReadPref('secondary');}"
			}
		}
	}

	cmdPath, err := resolveMongoShellBin(r.ShellBin, r.MongoVersion)
	if err != nil {
		return nil, err
	}
	argv = append(argv, []string{cmdPath, "--norc", "--quiet", "--eval", evalJs, "--shell", r.MongoHost.Uri()}...)
	return argv, nil
}

// Run starts the MongoShell process.
// 如果返回Error，表示进程启动失败，startWg.Done() 不会被调用
func (r *MongoShell) Run(startWg *sync.WaitGroup, logger *slog.Logger) error {
	r.logger = logger
	r.logger.Info("Run")
	var err error

	var inr, outr, outw *os.File
	inr, r.ProcessStdin, err = os.Pipe()
	if err != nil {
		r.logger.Error("os.Pipe", slog.Any("err", err))
		return fmt.Errorf("internal error, create pipe failed")
	}
	defer r.ProcessStdin.Close()
	defer inr.Close()

	outr, outw, err = os.Pipe()
	if err != nil {
		r.logger.Error("os.Pipe", slog.Any("err", err))
		return fmt.Errorf("internal error, create pipe failed")
	}
	defer outr.Close()
	defer outw.Close()

	r.logger.Info("createMongoShell", slog.Any("MongoHost", r.MongoHost))
	// try to create readonly user

	err = createReadOnlyUser(r.MongoHost.Host, r.MongoHost.AdminUsername, r.MongoHost.AdminPassword,
		r.MongoHost.UserName, r.MongoHost.Password, r.ClusterType, r.MongoVersion)
	if err != nil {
		r.logger.Error("createReadOnlyUser", slog.Any("err", err))
		return err
	}

	// 启动进程，启动后，将进程的Pid出发送到 BufChan
	// 如果进程退出，关闭 BufChan
	pidChan := make(chan int)
	procCtx, procCancel := context.WithCancel(context.Background())
	_ = procCancel

	argv, err := buildArgs(r)
	if err != nil {
		r.logger.Error("buildArgs", slog.Any("err", err))
		return err
	}
	r.logger.Info("StartProcess", slog.String("cmdPath", argv[0]),
		slog.Any("argv", replacePassword(argv, r.MongoHost.Password, "")))

	go func(pid chan<- int) {
		proc, err := os.StartProcess(argv[0], argv, &os.ProcAttr{
			Files: []*os.File{inr, outw, outw},
		})
		if err != nil {
			r.logger.Error("os.StartProcess", slog.Any("err", err))
		}
		pidChan <- proc.Pid
		// 等待进程结束， 进程结束后，关闭 BufChan
		state, err := proc.Wait()
		r.logger.Info("proc.exited", slog.String("state", state.String()), slog.Any("err", err))

		r.Pid = 0
		procCancel()
		// send a byte to close the pipe
		_, err = outw.Write([]byte("exit\n"))
		if err != nil {
			r.logger.Error("outw.Write", slog.Any("err", err))
		}
		r.logger.Info("procCancel")

	}(pidChan)

	pid := <-pidChan
	r.Pid = pid
	time.Sleep(2 * time.Second)
	r.logger.Info("startProcess",
		slog.String("cmdPath", argv[0]), slog.Any("argv", replacePassword(argv, r.MongoHost.Password, "")),
		slog.Int("pid", r.Pid), slog.Any("err", err))
	startWg.Done() // signal to main goroutine

	wg := sync.WaitGroup{}
	wg.Add(1)
	go func() {
		// read outr -> write BufChan
		r.logger.Info("pumpStdout: always read from outr, and send to BufChan")
		// 如果不是一次性的，则发送连接成功消息
		if r.OneOff != 1 {
			r.BufChan <- []byte(ConnectToServerMsg)
		}
		defer wg.Done()
		var buf = make([]byte, 1*1024*1024)
		for {
			select {
			case <-procCtx.Done():
				r.logger.Info("pumpStdout stop, because procCtx.Done")
				// r.BufChan <- []byte("exit\n")
				goto done
			default:
				// 阻塞读取 outr
				n, readErr := outr.Read(buf)
				r.logger.Info("readFromOut",
					slog.Int("n", n),
					slog.String("data", shortMsg(string(buf[:n]), 512)),
					slog.Any("err", readErr),
				)
				if err != nil {
					r.logger.Error("outr.Read", slog.Any("err", readErr))
					goto done
				}
				if n > 0 {
					// 发送到 BufChan
					r.logger.Info("sendToBufChan", slog.Int("n", n), slog.String("data", shortMsg(string(buf[:n]), 512)))
					var tmpBuf = make([]byte, n)
					copy(tmpBuf, buf[:n])
					r.BufChan <- tmpBuf
				}
			}
		}
	done:

		r.logger.Info("close chan", slog.String("func", "pumpStdout"))
		close(r.BufChan)
	}()

	wg.Wait()
	r.logger.Info("pumpStdout is done")
	return nil
}

// ReceiveMsg receives a message from the process
func (r *MongoShell) ReceiveMsg(timeout int64) (out []byte, err error) {
	buf := make([]byte, 0, maxRespSize)
	msg := bytes.NewBuffer(buf)
	ctxTimeout, procTimeout := context.WithTimeout(context.Background(), time.Duration(timeout)*time.Second)
	_ = procTimeout // 暂时不用
	bytesTotal := 0
	for {
		select {
		case v, ok := <-r.BufChan:
			endFlag := isResponseEnd(v)
			r.logger.Info("readFromBufChan", slog.Bool("isResponseEnd", endFlag),
				slog.String("data", shortMsg(string(v), 512)))

			if !ok {
				r.logger.Info("chan closed", slog.String("data", shortMsg(string(v), 512)))
				return msg.Bytes(), fmt.Errorf("chan closed")
			}
			n, werr := msg.Write(v)
			bytesTotal += n
			// 超过了bufSize
			if werr != nil {
				r.logger.Error("msg.Write", slog.Any("err", werr))
				return msg.Bytes(), werr
			}
			if bytesTotal > maxRespSize {
				r.logger.Info("excess data size", slog.Int("bytesTotal", bytesTotal),
					slog.Int("maxRespSize", maxRespSize), slog.String("data", shortMsg(string(v), 512)))
				return nil, fmt.Errorf("excess data size %dMB", maxRespSize/1024/1024)
			}

			if endFlag {
				// delete EndOfOutput and strip interactive shell prompts
				out = msg.Bytes()
				out = bytes.ReplaceAll(out, []byte(EndOfOutput), []byte(""))
				out = stripMongoShellPrompt(out)
				r.logger.Info("replace EndOfOutput", slog.String("data", shortMsg(string(out), 512)))
				return out, nil
			}

		case <-ctxTimeout.Done():
			r.logger.Info("ctxTimeout.Done timeout", slog.Int64("timeout", timeout))
			return msg.Bytes(), fmt.Errorf("timeout") // 返回超时或取消原因

		}
	}

	// not reach here
	// return msg.Bytes(), nil
}

func (r *MongoShell) Stop() {
	r.logger.Info("kill process", slog.Int("pid", r.Pid))
	syscall.Kill(r.Pid, syscall.SIGKILL)
	r.StopChan <- struct{}{}
	r.logger.Info("stopped, pid", slog.Int("pid", r.Pid))
}

func precheckInput(ShellBin string, msg []byte) ([]byte, error) {
	_ = ShellBin
	if len(msg) == 0 || msg[len(msg)-1] != '\n' {
		msg = append(msg, []byte("\n")...)
	}

	if isValid, err := isValidInput(msg); !isValid {
		return nil, fmt.Errorf("invalid input, err:%s", err.Error())
	}
	msg = append(msg, []byte(";\nprint('"+EndOfOutput+"');\n")...)
	return msg, nil
	/*
		// 避免空的输出
		// reShow, _ := regexp.Compile("(?i)" + `^\s*show\b`)
		reUse, _ := regexp.Compile("(?i)" + `^\s*use\b`)
		reIt, _ := regexp.Compile("(?i)" + `^\s*it\b`)
		if reIt.Match(msg) || reUse.Match(msg) {
			// use xxx
			// it;
			// 一定会有返回，不需要加 print, 其它的可能没有返回
		} else {
			msg = append(msg, []byte(";\nprint('_done_xxxxx__xxxxx_');\n")...)
		}

		return msg, nil
	*/
}

// SendMsg sends a message to process
func (r *MongoShell) SendMsg(msg []byte) (n int, err error) {
	msg, err = precheckInput(r.ShellBin, msg)
	if err != nil {
		return 0, errors.Wrap(err, "precheckInput")
	}
	n, err = r.ProcessStdin.Write([]byte(msg))
	return
}

func isResponseEnd(buf []byte) bool {
	// return len(buf) > 0 && buf[len(buf)-1] == '>' && bytes.Contains(buf, []byte(" [direct: "))
	return len(buf) > 0 && bytes.Contains(buf, []byte(EndOfOutput))
}

// isValidInput 检查([{}]) 是否成对出现, 优先处理 `'"的嵌套，然后再处理 ([{}])
func isValidInput(buf []byte) (bool, error) {
	scope_start := []byte{'[', '{', '('}
	scope_end := []byte{']', '}', ')'}
	scope_quote := []byte{'`', '"', '\''}
	stack := []byte{}
	quote_char := byte(0)
	for _, b := range buf {
		// 如果在引号中，直接跳过
		if quote_char != 0 {
			if quote_char == b {
				quote_char = 0
			}
			continue
		} else {
			if bytes.Contains(scope_quote, []byte{b}) {
				quote_char = b
			} else if bytes.Contains(scope_start, []byte{b}) {
				stack = append(stack, b)
			} else if bytes.Contains(scope_end, []byte{b}) {
				if len(stack) == 0 {
					return false, errors.Wrap(CheckInputError, fmt.Sprintf("not match scope for %c", b))
				}
				last_char := stack[len(stack)-1]
				if !(last_char == '[' && b == ']' || last_char == '{' && b == '}' || last_char == '(' && b == ')') {
					return false, errors.Wrap(CheckInputError, fmt.Sprintf("not match scope for %c", b))
				}
				stack = stack[:len(stack)-1]
			}
		}
	}
	if len(stack) != 0 {
		return false, errors.Wrap(CheckInputError, fmt.Sprintf("not match scope for %c", stack[len(stack)-1]))
	}
	if quote_char != 0 {
		return false, errors.Wrap(CheckInputError, fmt.Sprintf("not match quote for %c", quote_char))
	}
	return true, nil
}

func replacePassword(argv []string, pwd string, newPwd string) []string {
	if len(pwd) <= 4 {
		return argv
	}
	newArgv := make([]string, len(argv))
	pwd = EncodeURIComponent(pwd)
	if newPwd == "" {
		newPwd = pwd[0:4] + "...." + pwd[len(pwd)-4:]
	}
	for i, v := range argv {
		newArgv[i] = strings.ReplaceAll(v, pwd, newPwd)
	}
	return newArgv
}

package mongodb_rpc

import (
	"bytes"
	"context"
	"fmt"
	"log/slog"
	"net/url"
	"os"
	"os/exec"
	"strings"
	"sync"
	"time"
)

const ClusterTypeReplicaSet = "MongoReplicaSet"

type MongoHost struct {
	Host     string `json:"host"`
	Port     int    `json:"port"`
	UserName string `json:"username"`
	Password string `json:"password"`
	SetName  string `json:"set_name"`
}

func encodeURIComponent(str string) string {
	str = url.QueryEscape(str)
	str = strings.Replace(str, "+", "%20", -1)
	return str
}

func (h *MongoHost) Uri() string {
	if h.SetName == "" {
		return fmt.Sprintf("mongodb://%s:%s@%s/test?authSource=admin&readPreference=secondaryPreferred",
			h.UserName, encodeURIComponent(h.Password), h.Host)
	} else {
		return fmt.Sprintf(
			"mongodb://%s:%s@%s/test?replicaSet=%s&authSource=admin&readPreference=secondaryPreferred",
			h.UserName, encodeURIComponent(h.Password), h.Host, h.SetName)
	}

}

// MongoShell is a routine that can be run and stopped.
type MongoShell struct {
	logger        *slog.Logger
	ProcessStdin  *os.File
	ProcessOutBuf []byte
	OutBuf        []byte
	Cmd           string
	Chan          chan []byte
	Pid           int
	StopChan      chan struct{}
	ShellPath     string
	MongoHost     MongoHost
}

// getMongoBin get mongo shell bin path. mongosh or mongo
func getMongoBin(v string) string {
	for _, ver := range []string{"2.4", "3.0", "3.2", "3.4", "3.6", "4.0", "4.2"} {
		if strings.HasPrefix(v, ver+".") {
			return "mongo"
		}
	}
	return "mongosh"
}

// NewMongoShellFromParm create a new MongoShell instance
func NewMongoShellFromParm(p *QueryParams) *MongoShell {
	setName := ""
	if p.ClusterType == ClusterTypeReplicaSet {
		setName = p.SetName
	}
	return &MongoShell{
		Chan:      make(chan []byte, 102400),
		StopChan:  make(chan struct{}, 1),
		ShellPath: getMongoBin(p.Version),
		MongoHost: MongoHost{
			Host:     strings.Join(p.Addresses, ","),
			UserName: p.UserName,
			Password: p.Password,
			SetName:  setName,
		},
	}
}

func (r *MongoShell) Run(startWg *sync.WaitGroup, logger *slog.Logger) {
	r.logger = logger
	r.logger.Info("Run")
	var cmdPath string
	var argv []string
	var err error
	var inr, outr, outw *os.File
	inr, r.ProcessStdin, err = os.Pipe()
	if err != nil {
		r.logger.Error("os.Pipe", slog.Any("err", err))
		return
	}
	defer r.ProcessStdin.Close()
	defer inr.Close()

	outr, outw, err = os.Pipe()
	if err != nil {
		r.logger.Error("os.Pipe", slog.Any("err", err))
		return
	}

	defer outr.Close()
	defer outw.Close()

	// 启动进程，启动后，将进程的Pid出发送到 Chan
	// 如果进程退出，关闭 Chan
	pidChan := make(chan int)
	procCtx, procCancel := context.WithCancel(context.Background())
	// defer procCancel()

	go func(pid chan<- int) {
		// cmdPath, err = exec.LookPath("mongo")
		if cmdPath, err = exec.LookPath(r.ShellPath); err != nil {
			r.logger.Error("exec.LookPath", slog.Any("err", err))
			return
		}
		argv = append(argv, []string{cmdPath, "--norc", "--quiet", r.MongoHost.Uri()}...)
		r.logger.Info("StartProcess", slog.String("cmdPath", cmdPath), slog.Any("argv", argv))
		proc, err := os.StartProcess(cmdPath, argv, &os.ProcAttr{
			Files: []*os.File{inr, outw, outw},
		})
		if err != nil {
			r.logger.Error("os.StartProcess", slog.Any("err", err))
		}
		pidChan <- proc.Pid
		// 等待进程结束， 进程结束后，关闭 Chan
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

	r.logger.Info("StartProcess", slog.String("cmdPath", cmdPath), slog.Any("argv", argv))

	var pid int
	pid = <-pidChan
	r.Pid = pid
	time.Sleep(2)
	r.logger.Info("StartProcess", slog.String("cmdPath", cmdPath), slog.Any("argv", argv),
		slog.Int("pid", r.Pid), slog.Any("err", err))
	startWg.Done() // signal to main goroutine

	wg := sync.WaitGroup{}
	wg.Add(1)
	go func() {
		// pumpStdout
		// 从 outr 读取数据，发送到 Chan
		// 如果进程结束，关闭 Chan
		r.logger.Info("pumpStdout: always read from outr, and send to Chan")
		defer wg.Done()
		var buf = make([]byte, 102400)
		for {
			select {
			case <-procCtx.Done():
				r.logger.Info("pumpStdout stop, because procCtx.Done")
				r.Chan <- []byte("exit\n")
				goto done
			default:
				// ctx, _ := context.WithTimeout(context.Background(), 1*time.Second
				// 阻塞读取 outr
				n, readErr := outr.Read(buf)
				r.logger.Info("readMsg",
					slog.Int("readByte", n),
					slog.String("buf", string(buf[:n])),
					slog.Any("err", readErr),
				)
				if err != nil {
					r.logger.Error("outr.Read", slog.Any("err", readErr))
					goto done
				}
				if n > 0 {
					r.Chan <- buf[:n]
				}
			}
		}
	done:

		r.logger.Info("close Chan", slog.String("func", "pumpStdout"))
		close(r.Chan)
	}()

	r.logger.Info("pumpStdout is running")
	wg.Wait()
	r.logger.Info("pumpStdout is done")
}

func (r *MongoShell) ReceiveMsg(timeout int64) (out []byte, err error) {
	buf := make([]byte, 0, 32*1024*1024)
	msg := bytes.NewBuffer(buf)
	lastUpdate := time.Now().UnixMilli()
	ctxTimeout, _ := context.WithTimeout(context.Background(), time.Duration(timeout)*time.Second)
	checkCone := time.Tick(100 * time.Millisecond)
	for {
		select {
		case v, ok := <-r.Chan:
			if !ok {
				return nil, fmt.Errorf("chan closed")
			}
			_, werr := msg.Write(v)
			if werr != nil {
				return nil, werr
			}

			lastUpdate = time.Now().UnixMilli()
			if isResponseEnd(msg.Bytes()) {
				return msg.Bytes(), nil
			}
		case <-ctxTimeout.Done():
			return nil, fmt.Errorf("timeout") // 返回超时或取消原因
		case <-checkCone:
			if msg.Len() > 0 && time.Now().UnixMilli()-lastUpdate > 800 {
				r.logger.Info("ReceiveMsg because of timeout", slog.Int("msgLen", msg.Len()))
				return msg.Bytes(), nil
			}
		}
	}

	return msg.Bytes(), nil
}

func (r *MongoShell) Stop() {
	r.logger.Info("Stop")
	r.StopChan <- struct{}{}
	r.logger.Info("Stopped")
}

// SendMsg sends a message to process
func (r *MongoShell) SendMsg(msg []byte) (n int, err error) {
	// todo check priv
	msg = append(msg, '\n')
	n, err = r.ProcessStdin.Write(msg)
	return
}

func isResponseEnd(buf []byte) bool {
	// return len(buf) > 0 && buf[len(buf)-1] == '>' && bytes.Contains(buf, []byte(" [direct: "))
	return len(buf) > 0 && buf[len(buf)-1] == '>'
}

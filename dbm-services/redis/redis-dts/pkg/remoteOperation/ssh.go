// Package remoteOperation TODO
package remoteOperation

import (
	"bytes"
	"fmt"
	"io"
	"math"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"time"

	"dbm-services/redis/redis-dts/pkg/constvar"
	"dbm-services/redis/redis-dts/util"

	"github.com/dustin/go-humanize"
	"github.com/juju/ratelimit"
	"github.com/pkg/sftp"
	"go.uber.org/zap"
	"golang.org/x/crypto/ssh"
)

// ISSHConfig represents SSH connection parameters.
type ISSHConfig struct {
	RemoteUser     string   // 如 test_user
	RemotePassword string   // 如 test_password
	PrivateKey     string   // 可为空
	RemoteServer   string   // 如 1.1.1.1:22
	KeyExchanges   []string // 可为空
	Timeout        time.Duration
}

// 无实际作用,仅确保实现了 RemoteOperation 接口
var _ RemoteOperation = (*ISSHClient)(nil)

// ISSHClient provides basic functionality to interact with a SFTP server.
type ISSHClient struct {
	config     ISSHConfig
	sshClient  *ssh.Client
	sftpClient *sftp.Client
	logger     *zap.Logger
}

// NewISshClient initialises SSH and SFTP clients and returns Client type to use.
func NewISshClient(config ISSHConfig, logger *zap.Logger) (*ISSHClient, error) {
	c := &ISSHClient{
		config: config,
		logger: logger,
	}

	if err := c.connect(); err != nil {
		return nil, err
	}

	return c, nil
}

// NewISshClientByEnvAbsVars new
func NewISshClientByEnvAbsVars(remoteIP string, logger *zap.Logger) (cli *ISSHClient, err error) {
	var absPasswd string
	var absPort int
	absPasswd, err = constvar.GetABSPassword()
	if err != nil {
		logger.Error(err.Error())
		return
	}
	absPort = constvar.GetABSPort()
	conf := ISSHConfig{
		RemoteUser:     constvar.GetABSUser(),
		RemotePassword: absPasswd,
		RemoteServer:   remoteIP + ":" + strconv.Itoa(absPort),
		Timeout:        constvar.GetABSPullTimeout(),
	}
	return NewISshClient(conf, logger)
}

// Create creates a remote/destination file for I/O.
func (c *ISSHClient) Create(filePath string) (io.ReadWriteCloser, error) {
	if err := c.connect(); err != nil {
		return nil, fmt.Errorf("connect: %w", err)
	}

	return c.sftpClient.Create(filePath)
}

// Upload writes local/source file data streams to remote/destination file.
func (c *ISSHClient) Upload(source io.Reader, destination io.Writer, size int) error {
	if err := c.connect(); err != nil {
		return fmt.Errorf("connect: %w", err)
	}

	chunk := make([]byte, size)

	for {
		num, err := source.Read(chunk)
		if err == io.EOF {
			tot, err := destination.Write(chunk[:num])
			if err != nil {
				return err
			}

			if tot != len(chunk[:num]) {
				err = fmt.Errorf("write_size:%d != read_size:%d", tot, num)
				c.logger.Error(err.Error())
				return err
			}

			return nil
		}

		if err != nil {
			return err
		}

		tot, err := destination.Write(chunk[:num])
		if err != nil {
			return err
		}

		if tot != len(chunk[:num]) {
			err = fmt.Errorf("write_size:%d != read_size:%d", tot, num)
			c.logger.Error(err.Error())
			return err
		}
	}
}

// CalcFileSizeIncr 计算文件大小增长速度
func CalcFileSizeIncr(f string, secs uint64) string {
	var err error
	var t1Size, t2Size int64
	if t1Size, err = util.GetFileSize(f); err != nil {
		return "0"
	}
	time.Sleep(time.Duration(secs) * time.Second)
	if t2Size, err = util.GetFileSize(f); err != nil {
		return "0"
	}

	bytesIncr := uint64(math.Abs(float64(t2Size-t1Size))) / secs
	return humanize.Bytes(bytesIncr)
}

// IOLimitRate io.Copy 限速
func IOLimitRate(dst io.Writer, src io.Reader, bwlimitMB int64) (written int64, err error) {
	bwlimit := bwlimitMB * 1024 * 1024
	srcBucket := ratelimit.NewBucketWithRate(float64(bwlimit), bwlimit)
	return io.Copy(dst, ratelimit.Reader(src, srcBucket))
}

// RemoteDownload download file from remote server
func (c *ISSHClient) RemoteDownload(srcDir, dstDir string, fileName string, bwlimitMB int64) (err error) {

	srcFile := filepath.Join(srcDir, fileName)
	dstFile := filepath.Join(dstDir, fileName)
	if fileName == "" {
		srcFile = srcDir
		dstFile = dstDir
	}
	c.logger.Info(fmt.Sprintf("start download to %s", dstFile))
	// Get remote file stats.
	info, err := c.Info(srcFile)
	if err != nil {
		return err
	}
	c.logger.Info(fmt.Sprintf("download source file info:%+v", info))

	// Download remote file.

	r, err := c.sftpClient.Open(srcFile)
	if err != nil {
		err = fmt.Errorf("sftp.Open fail,err:%v,srcFile:%s", err, srcFile)
		c.logger.Error(err.Error())
		return err
	}
	defer r.Close()

	// create local file
	f, err := os.Create(dstFile)
	if err != nil {
		err = fmt.Errorf("os.Create %s fail,err:%v", dstFile, err)
		c.logger.Error(err.Error())
		return err
	}
	defer f.Close()

	done := make(chan int, 1)
	defer close(done)
	go func(chan int) {
		for true {
			speed := CalcFileSizeIncr(dstFile, 1)
			if speed != "0" {
				c.logger.Info(fmt.Sprintf("file %s change speed %s", dstFile, speed))
			} else {
				break
			}
			select {
			case _, beforeClosed := <-done:
				if !beforeClosed {
					return
				}
			case <-time.After(2 * time.Hour):
				return
			default:
				time.Sleep(time.Duration(10) * time.Second)
			}
		}
	}(done)

	// Read downloaded file.
	_, err = IOLimitRate(f, r, bwlimitMB)
	if err != nil {
		return err
	}
	return nil
}

// RemoteBash do remote bash -c "$cmd"
func (c *ISSHClient) RemoteBash(cmd string) (ret string, err error) {
	bashCmd := fmt.Sprintf("bash -c %q", cmd)
	err = c.connect()
	if err != nil {
		return "", fmt.Errorf("connct,err:%v", err)
	}
	var session *ssh.Session = nil
	var outBuf bytes.Buffer
	var errBuf bytes.Buffer
	session, err = c.sshClient.NewSession()
	if err != nil {
		err = fmt.Errorf("client.NewSession fail,err:%v,server:%s", err, c.config.RemoteServer)
		c.logger.Error(err.Error())
		return
	}
	session.Stdout = &outBuf
	session.Stderr = &errBuf
	err = session.Run(bashCmd)
	if err != nil {
		err = fmt.Errorf("session.Run fail,err:%v,server:%s,cmd:%q", err, c.config.RemoteServer, cmd)
		c.logger.Error(err.Error())
		return
	}
	if errBuf.String() != "" {
		err = fmt.Errorf("session.Run fail,err:%s,server:%s,cmd:%q", errBuf.String(), c.config.RemoteServer, cmd)
		c.logger.Error(err.Error())
		return
	}
	return outBuf.String(), nil
}

// Info gets the details of a file. If the file was not found, an error is returned.
func (c *ISSHClient) Info(filePath string) (os.FileInfo, error) {
	if err := c.connect(); err != nil {
		return nil, fmt.Errorf("connect: %w", err)
	}

	info, err := c.sftpClient.Lstat(filePath)
	if err != nil {
		err = fmt.Errorf("file lstat fail,err:%v,server:%s,filePath:%s", err, c.config.RemoteServer, filePath)
		c.logger.Error(err.Error())
		return nil, err
	}

	return info, nil
}

// Close closes open connections.
func (c *ISSHClient) Close() {
	if c.sftpClient != nil {
		c.sftpClient.Close()
	}
	if c.sshClient != nil {
		c.sshClient.Close()
	}
}

// GetAuthMethods TODO
func (c *ISSHConfig) GetAuthMethods(password string) []ssh.AuthMethod {
	auth := ssh.Password(password)
	/*
		if c.config.PrivateKey != "" {
			signer, err := ssh.ParsePrivateKey([]byte(c.config.PrivateKey))
			if err != nil {
				return fmt.Errorf("ssh parse private key: %w", err)
			}
			auth = ssh.PublicKeys(signer)
		}
	*/
	keyboardInteractiveChallenge := func(
		user,
		instruction string,
		questions []string,
		echos []bool,
	) (answers []string, err error) {
		if len(questions) == 0 {
			return []string{}, nil
		}
		/*
			for i, question := range questions {
				log.Debug("SSH Question %d: %s", i+1, question)
			}
		*/
		answers = make([]string, len(questions))
		for i := range questions {
			yes, _ := regexp.MatchString("*yes*", questions[i])
			if yes {
				answers[i] = "yes"

			} else {
				answers[i] = password
			}
		}
		return answers, nil
	}
	auth2 := ssh.KeyboardInteractive(keyboardInteractiveChallenge)

	methods := []ssh.AuthMethod{auth2, auth}
	return methods
}

// connect initialises a new SSH and SFTP client only if they were not
// initialised before at all and, they were initialised but the SSH
// connection was lost for any reason.
func (c *ISSHClient) connect() error {
	if c.sshClient != nil {
		_, _, err := c.sshClient.SendRequest("keepalive", false, nil)
		if err == nil {
			return nil
		}
	}

	cfg := &ssh.ClientConfig{
		User: c.config.RemoteUser,
		Auth: c.config.GetAuthMethods(c.config.RemotePassword),
		// HostKeyCallback: func(string, net.Addr, ssh.PublicKey) error { return nil },
		HostKeyCallback: ssh.InsecureIgnoreHostKey(),
		// HostKeyCallback: ssh.FixedHostKey(hostKey),
		Timeout: c.config.Timeout,
	}

	sshClient, err := ssh.Dial("tcp", c.config.RemoteServer, cfg)
	if err != nil {
		err = fmt.Errorf("ssh dial %s fail,err:%w", c.config.RemoteServer, err)
		c.logger.Error(err.Error())
		return err
	}
	c.sshClient = sshClient

	sftpClient, err := sftp.NewClient(sshClient)
	if err != nil {
		err = fmt.Errorf("sftp new client fail,sshClient:%+v,err:%v", c.config, err)
		c.logger.Error(err.Error())
		return err
	}
	c.sftpClient = sftpClient

	return nil
}

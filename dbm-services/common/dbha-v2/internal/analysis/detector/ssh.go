/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package detector

import (
	"context"
	"errors"
	"fmt"
	"net"
	"strings"
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"

	"golang.org/x/crypto/ssh"
)

// sshAuthFailureKeyword is the SSH authentication failure keyword, kept
// consistent with v1's CheckSSHErrIsAuthFail.
const sshAuthFailureKeyword = "unable to authenticate"

var (
	ErrDetectorCreateSshConnection = gerrors.Newf(gerrors.NetException, "failed to dial")
	ErrDetectorCreateSshSession    = gerrors.Newf(gerrors.NetException, "failed to create SSH session")
	ErrDetectorSshAuth             = gerrors.Newf(gerrors.SshFailure, "ssh auth failed")
	ErrDetectorSshConnectTimeout   = gerrors.Newf(gerrors.Timeout, "ssh connect timed out")
	ErrDetectorSshExecTimeout      = gerrors.Newf(gerrors.Timeout, "ssh command execution timed out")
)

// SshResponse contains the result of the shell that was running on the remote host.
type SshResponse struct {
	Id       string
	Data     string
	ExitCode int
	ErrMsg   string
}

// Ssh is used to detect a remote host.
type Ssh struct {
	port     int
	ip       string
	user     string
	password string
	timeout  time.Duration
}

// Id returns the detector identifier for the SSH target.
func (s *Ssh) Id() string {
	return fmt.Sprintf("ssh-id:%s@%d:%s", s.ip, s.port, s.user)
}

// Run runs cmd on the remote host and returns its combined standard output and
// standard error.
//
// One overall budget bounds every stage: the TCP dial is bounded by the dialer,
// while the banner exchange, the key exchange, the authentication, the session
// setup, the command execution and the close are bounded by the connection deadline.
func (s *Ssh) Run(cmd string) (*SshResponse, error) {
	deadline := time.Now().Add(s.timeout)
	ctx, cancel := context.WithDeadline(context.Background(), deadline)
	defer cancel()

	addr := fmt.Sprintf("%s:%d", s.ip, s.port)

	conn, err := s.dialWithDeadline(ctx, addr, deadline)
	if err != nil {
		return nil, err
	}
	defer func() { _ = conn.Close() }()

	client, err := s.newClientWithDeadline(conn, addr)
	if err != nil {
		return nil, err
	}
	defer func() { _ = client.Close() }()

	session, err := client.NewSession()
	if err != nil {
		logger.Error("failed to create an SSH session for the remote host: %s, errmsg: %s", addr, err)
		return nil, classifySshErr(err, ErrDetectorCreateSshSession)
	}
	defer func() { _ = session.Close() }()

	resp := &SshResponse{Id: s.Id()}
	return s.runCombinedOutput(ctx, resp, session, cmd, deadline)
}

// dialWithDeadline establishes the TCP connection and pins the overall deadline
// on it. That deadline also bounds the following banner exchange, key exchange,
// authentication, command execution and close stages.
func (s *Ssh) dialWithDeadline(ctx context.Context, addr string, deadline time.Time) (net.Conn, error) {
	conn, err := (&net.Dialer{}).DialContext(ctx, "tcp", addr)
	if err != nil {
		logger.Error("failed to connect the remote host with SSH, host: %s, errmsg: %s", addr, err)
		return nil, classifySshErr(err, ErrDetectorCreateSshConnection)
	}

	if err := conn.SetDeadline(deadline); err != nil {
		logger.Error("failed to set the deadline on the SSH connection, host: %s, errmsg: %s", addr, err)
		_ = conn.Close()
		return nil, ErrDetectorCreateSshConnection
	}

	return conn, nil
}

// newClientWithDeadline completes the SSH handshake and the authentication over conn.
func (s *Ssh) newClientWithDeadline(conn net.Conn, addr string) (*ssh.Client, error) {
	conf := &ssh.ClientConfig{
		User:            s.user,
		HostKeyCallback: ssh.InsecureIgnoreHostKey(),
		Auth: []ssh.AuthMethod{
			ssh.KeyboardInteractive(s.keyboardInteractive()),
			ssh.Password(s.password),
		},
	}

	c, chans, reqs, err := ssh.NewClientConn(conn, addr, conf)
	if err != nil {
		logger.Error("ssh handshake failed, host: %s, errmsg: %s", addr, err)
		if strings.Contains(err.Error(), sshAuthFailureKeyword) {
			return nil, ErrDetectorSshAuth
		}
		return nil, classifySshErr(err, ErrDetectorCreateSshConnection)
	}

	return ssh.NewClient(c, chans, reqs), nil
}

// classifySshErr returns the connect timeout sentinel when err is a timeout,
// otherwise it keeps the error that describes the failed stage.
func classifySshErr(err error, stageErr error) error {
	var nerr net.Error
	if errors.As(err, &nerr) && nerr.Timeout() {
		return ErrDetectorSshConnectTimeout
	}
	if errors.Is(err, context.DeadlineExceeded) {
		return ErrDetectorSshConnectTimeout
	}
	return stageErr
}

// runCombinedOutput runs cmd and classifies the result.
func (s *Ssh) runCombinedOutput(ctx context.Context, resp *SshResponse, session *ssh.Session,
	cmd string, deadline time.Time) (*SshResponse, error) {
	// execBudget is the remaining budget when exec starts. It tells whether a
	// timeout came from a squeezed budget or from a slow command.
	execBudget := time.Until(deadline)

	data, cmdErr := session.CombinedOutput(cmd)
	resp.Data = string(data)

	var exitErr *ssh.ExitError
	switch {
	case cmdErr == nil:
		logger.Debug("shell command response: %s, cmd: %s", string(data), cmd)

	case errors.As(cmdErr, &exitErr):
		resp.ExitCode = exitErr.ExitStatus()
		resp.ErrMsg = exitErr.Error()

	case errors.Is(ctx.Err(), context.DeadlineExceeded) || !time.Now().Before(deadline):
		resp.ExitCode = gerrors.Timeout.Int()
		resp.ErrMsg = ErrDetectorSshExecTimeout.Error()
		logger.Error("SSH command execution timed out, host: %s, exec budget: %v, cmd: %s, errmsg: %s",
			fmt.Sprintf("%s:%d", s.ip, s.port), execBudget, cmd, cmdErr)
		return resp, ErrDetectorSshExecTimeout

	default:
		resp.ExitCode = gerrors.Failure.Int()
		resp.ErrMsg = cmdErr.Error()
	}

	return resp, nil
}

func (s *Ssh) keyboardInteractive() ssh.KeyboardInteractiveChallenge {
	return func(user, instruction string, questions []string, echos []bool) ([]string, error) {
		answers := make([]string, len(questions))

		for n := range questions {
			answers[n] = s.password
		}

		return answers, nil
	}
}

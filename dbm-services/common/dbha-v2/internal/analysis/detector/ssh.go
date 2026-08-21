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
	"fmt"
	"io"
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
	ErrDetectorSshTimeout          = gerrors.Newf(gerrors.Timeout, "ssh command execution timed out")
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

// Run runs cmd on the remote host and returns it's combined standard output and standard error.
// Dial and command execution are each bounded by s.timeout independently,
// so the total elapsed time may reach up to 2× s.timeout in the worst case.
func (s *Ssh) Run(cmd string) (*SshResponse, error) {
	conf := &ssh.ClientConfig{
		Timeout:         s.timeout,
		User:            s.user,
		HostKeyCallback: ssh.InsecureIgnoreHostKey(),
	}

	conf.Auth = []ssh.AuthMethod{
		ssh.KeyboardInteractive(s.keyboardInteractive()),
		ssh.Password(s.password),
	}

	addr := fmt.Sprintf("%s:%d", s.ip, s.port)

	sshClient, err := ssh.Dial("tcp", addr, conf)
	if err != nil {
		logger.Error("failed to connect the remote host with SSH, host: %s, errmsg: %s", addr, err)
		if strings.Contains(err.Error(), sshAuthFailureKeyword) {
			return nil, ErrDetectorSshAuth
		}
		return nil, ErrDetectorCreateSshConnection
	}

	defer func() {
		if err := sshClient.Close(); err != nil && err != io.EOF {
			logger.Warn("failed to close the connection with the remote host: %s, errmsg: %s", addr, err)
		}
	}()

	session, err := sshClient.NewSession()
	if err != nil {
		logger.Error("failed to create an SSH session for the remote host: %s, errmsg: %s", addr, err)
		return nil, ErrDetectorCreateSshSession
	}

	defer func() {
		if err := session.Close(); err != nil && err != io.EOF {
			logger.Warn("failed to close the SSH session with the remote host: %s, errmsg: %s", addr, err)
		}
	}()

	resp := &SshResponse{Id: s.Id()}
	resp = s.runCombinedOutputWithTimeout(resp, session, cmd)

	return resp, nil
}

func (s *Ssh) runCombinedOutputWithTimeout(resp *SshResponse, session *ssh.Session, cmd string) *SshResponse {
	type cmdResult struct {
		data []byte
		err  error
	}

	resultCh := make(chan cmdResult, 1)
	go func() {
		data, cmdErr := session.CombinedOutput(cmd)
		resultCh <- cmdResult{data: data, err: cmdErr}
	}()

	timer := time.NewTimer(s.timeout)
	defer timer.Stop()

	select {
	case result := <-resultCh:
		resp.Data = string(result.data)

		if result.err == nil {
			logger.Debug("shell command response: %s, cmd: %s", string(result.data), cmd)
			return resp
		}

		if exitErr, ok := result.err.(*ssh.ExitError); ok {
			resp.ExitCode = exitErr.ExitStatus()
			resp.ErrMsg = exitErr.Error()
			return resp
		}

		resp.ExitCode = gerrors.Failure.Int()
		resp.ErrMsg = result.err.Error()
		return resp
	case <-timer.C:
		_ = session.Close()

		resp.ExitCode = gerrors.Timeout.Int()
		resp.ErrMsg = ErrDetectorSshTimeout.Error()
		logger.Error("SSH command execution timed out, host: %s, timeout: %v, cmd: %s",
			fmt.Sprintf("%s:%d", s.ip, s.port), s.timeout, cmd)
		return resp
	}
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

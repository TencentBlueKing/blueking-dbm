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
	"time"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/pkg/logger"

	"golang.org/x/crypto/ssh"
)

var (
	ErrDetectorCreateSshConnection = gerrors.Newf(gerrors.NetException, "failed to dial")
	ErrDetectorCreateSshSession    = gerrors.Newf(gerrors.NetException, "failed to create SSH session")
	ErrDetectorRunShellCommand     = gerrors.Newf(gerrors.Failure, "failed to run shell command")
)

// Ssh is used to detect a remote host.
type Ssh struct {
	port     int
	ip       string
	user     string
	password string
	timeout  time.Duration
}

func (s *Ssh) Id() string {
	return fmt.Sprintf("ssh-id:%s@%d:%s", s.ip, s.port, s.user)
}

// Run runs cmd on the remote host and returns it's combined standard output and standard error.
func (s *Ssh) Run(cmd string) ([]byte, error) {
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

	respond, err := session.CombinedOutput(cmd)
	if err != nil {
		logger.Error("failed to run the command: %s, host: %s, respond: %s, errmsg: %s", cmd, addr, respond, err)
		return nil, ErrDetectorRunShellCommand
	}

	return respond, nil
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

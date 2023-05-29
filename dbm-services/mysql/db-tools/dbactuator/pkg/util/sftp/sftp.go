// Package sftp TODO
package sftp

import (
	"fmt"
	"io"
	"os"
	"regexp"
	"time"

	"github.com/pkg/sftp"
	"golang.org/x/crypto/ssh"
)

// Config represents SSH connection parameters.
type Config struct {
	Username     string
	Password     string
	PrivateKey   string
	Server       string
	KeyExchanges []string

	Timeout time.Duration
}

// Client provides basic functionality to interact with a SFTP server.
type Client struct {
	config     Config
	sshClient  *ssh.Client
	sftpClient *sftp.Client
}

// New initialises SSH and SFTP clients and returns Client type to use.
func New(config Config) (*Client, error) {
	c := &Client{
		config: config,
	}

	if err := c.connect(); err != nil {
		return nil, err
	}

	return c, nil
}

// Create creates a remote/destination file for I/O.
func (c *Client) Create(filePath string) (io.ReadWriteCloser, error) {
	if err := c.connect(); err != nil {
		return nil, fmt.Errorf("connect: %w", err)
	}

	return c.sftpClient.Create(filePath)
}

// Upload writes local/source file data streams to remote/destination file.
func (c *Client) Upload(source io.Reader, destination io.Writer, size int) error {
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
				return fmt.Errorf("failed to write stream")
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
			return fmt.Errorf("failed to write stream")
		}
	}
}

// Download returns remote/destination file for reading.
func (c *Client) Download(filePath string) (io.ReadCloser, error) {
	if err := c.connect(); err != nil {
		return nil, fmt.Errorf("connect: %w", err)
	}

	return c.sftpClient.Open(filePath)
}

// Info gets the details of a file. If the file was not found, an error is returned.
func (c *Client) Info(filePath string) (os.FileInfo, error) {
	if err := c.connect(); err != nil {
		return nil, fmt.Errorf("connect: %w", err)
	}

	info, err := c.sftpClient.Lstat(filePath)
	if err != nil {
		return nil, fmt.Errorf("file stats: %w", err)
	}

	return info, nil
}

// Close closes open connections.
func (c *Client) Close() {
	if c.sftpClient != nil {
		c.sftpClient.Close()
	}
	if c.sshClient != nil {
		c.sshClient.Close()
	}
}

// GetAuthMethods TODO
func (c *Config) GetAuthMethods(password string) []ssh.AuthMethod {
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
func (c *Client) connect() error {
	if c.sshClient != nil {
		_, _, err := c.sshClient.SendRequest("keepalive", false, nil)
		if err == nil {
			return nil
		}
	}

	cfg := &ssh.ClientConfig{
		User: c.config.Username,
		Auth: c.config.GetAuthMethods(c.config.Password),
		// HostKeyCallback: func(string, net.Addr, ssh.PublicKey) error { return nil },
		HostKeyCallback: ssh.InsecureIgnoreHostKey(),
		// HostKeyCallback: ssh.FixedHostKey(hostKey),
		Timeout: c.config.Timeout,
	}

	sshClient, err := ssh.Dial("tcp", c.config.Server, cfg)
	if err != nil {
		return fmt.Errorf("ssh dial: %w", err)
	}
	c.sshClient = sshClient

	sftpClient, err := sftp.NewClient(sshClient)
	if err != nil {
		return fmt.Errorf("sftp new client: %w", err)
	}
	c.sftpClient = sftpClient

	return nil
}

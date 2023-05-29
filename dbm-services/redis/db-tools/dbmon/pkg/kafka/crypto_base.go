package kafka

import (
	"crypto/sha256"
	"crypto/sha512"

	"github.com/xdg-go/scram"
)

var (
	// SHA256 256
	SHA256 scram.HashGeneratorFcn = sha256.New
	// SHA512 512
	SHA512 scram.HashGeneratorFcn = sha512.New
)

// XDGSCRAMClient struct
type XDGSCRAMClient struct {
	*scram.Client
	*scram.ClientConversation
	scram.HashGeneratorFcn
}

// Begin implement interface
func (x *XDGSCRAMClient) Begin(userName, password, authzID string) (err error) {
	x.Client, err = x.HashGeneratorFcn.NewClient(userName, password, authzID)
	if err != nil {
		return err
	}
	x.ClientConversation = x.Client.NewConversation()
	return nil
}

// Step implement interface
func (x *XDGSCRAMClient) Step(challenge string) (response string, err error) {
	response, err = x.ClientConversation.Step(challenge)
	return
}

// Done implement interface
func (x *XDGSCRAMClient) Done() bool {
	return x.ClientConversation.Done()
}

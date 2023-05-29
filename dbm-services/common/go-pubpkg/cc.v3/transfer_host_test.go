package cc

import (
	"testing"
)

// TestTransfer
func TestTransfer(t *testing.T) {
	client, err := NewClient("http://127.0.0.1", TestSecret)
	if err != nil {
		t.Fatal(err)
	}
	h := NewTransferHost(client)
	err = h.Transfer(&TransferHostParam{
		From: BKFrom{
			BKBizId:  310,
			InnerIPs: []string{"1.1.1.1"},
		},
		To: BKTo{
			BKBizId:    100605,
			BKModuleId: 548622,
		},
	})
	if err != nil {
		t.Fatal(err)
	}
}

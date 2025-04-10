// precheck_input_test.go
package mongodb_rpc

import (
	"reflect"
	"testing"
)

func TestPrecheckInput(t *testing.T) {
	tests := []struct {
		name    string
		input   []byte
		want    []byte
		wantErr bool
	}{
		{
			name:    "Empty input",
			input:   []byte(""),
			want:    []byte("\n"),
			wantErr: false,
		},
		{
			name:    "Input without newline",
			input:   []byte("show"),
			want:    []byte("show\nprint('')\n"),
			wantErr: false,
		},
		{
			name:    "Input with newline",
			input:   []byte("show\n"),
			want:    []byte("show\nprint('')\n"),
			wantErr: false,
		},
		{
			name:    "Non-show input",
			input:   []byte("db.stats()"),
			want:    []byte("db.stats()\n"),
			wantErr: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := precheckInput(tt.input)
			if (err != nil) != tt.wantErr {
				t.Errorf("precheckInput() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if !reflect.DeepEqual(got, tt.want) {
				t.Errorf("precheckInput() = %v, want %v", string(got), string(tt.want))
			}
		})
	}
}

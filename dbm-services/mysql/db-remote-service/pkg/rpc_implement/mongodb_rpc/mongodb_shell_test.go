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
			got, err := precheckInput("mongo", tt.input)
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

func TestIsValidInput(t *testing.T) {
	tests := []struct {
		name  string
		input []byte
		want  bool
	}{
		{name: "Valid input", input: []byte("db.stats()"), want: true},
		{name: "Invalid input", input: []byte("db.stats()\n"), want: true},
		{name: "Valid input with quote", input: []byte("db.stats('{a:1}')"), want: true},
		{name: "Invalid input with quote", input: []byte("db.stats('{a:1}'"), want: false},
		{name: "Valid input with quote", input: []byte("db.stats('{a:1}', 'b')"), want: true},
		{name: "Invalid input with quote", input: []byte("db.stats('{a:1}', 'b'"), want: false},
		{name: "Valid input with quote", input: []byte("db.stats('{a:1}', 'b')"), want: true},
		{name: "valid input no quote", input: []byte("abc;"), want: true},
		{name: "valid input no quote", input: []byte(`'"'`), want: true},
		{name: "valid input no quote", input: []byte(`'x'`), want: true},
		{name: "valid input no quote", input: []byte(`'''`), want: false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, _ := isValidInput(tt.input)

			if got != tt.want {
				t.Errorf("isValidInput() = %v, want %v", got, tt.want)
			}
		})
	}
}

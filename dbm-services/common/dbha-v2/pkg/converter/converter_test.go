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

package converter

import (
	"testing"
)

func TestToInt(t *testing.T) {
	tests := []struct {
		name    string
		input   any
		want    int
		wantErr bool
	}{
		{"int", 42, 42, false},
		{"uint", uint(100), 100, false},
		{"uint64", uint64(999), 999, false},
		{"string valid", "123", 123, false},
		{"string invalid", "abc", 0, true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var got int
			var err error

			switch v := tt.input.(type) {
			case int:
				got, err = ToInt(v)
			case uint:
				got, err = ToInt(v)
			case uint64:
				got, err = ToInt(v)
			case string:
				got, err = ToInt(v)
			}

			if (err != nil) != tt.wantErr {
				t.Fatalf("ToInt() error = %v, wantErr %v", err, tt.wantErr)
			}
			if !tt.wantErr && got != tt.want {
				t.Fatalf("ToInt() = %v, want %v", got, tt.want)
			}
			t.Logf("ToInt(%v) = %v", tt.input, got)
		})
	}
}

func TestToInt64(t *testing.T) {
	tests := []struct {
		name    string
		input   any
		want    int64
		wantErr bool
	}{
		{"int", 42, 42, false},
		{"uint", uint(100), 100, false},
		{"int64", int64(9999999999), 9999999999, false},
		{"string valid", "123456789", 123456789, false},
		{"string invalid", "not_number", 0, true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var got int64
			var err error

			switch v := tt.input.(type) {
			case int:
				got, err = ToInt64(v)
			case uint:
				got, err = ToInt64(v)
			case int64:
				got, err = ToInt64(v)
			case string:
				got, err = ToInt64(v)
			}

			if (err != nil) != tt.wantErr {
				t.Fatalf("ToInt64() error = %v, wantErr %v", err, tt.wantErr)
			}
			if !tt.wantErr && got != tt.want {
				t.Fatalf("ToInt64() = %v, want %v", got, tt.want)
			}
			t.Logf("ToInt64(%v) = %v", tt.input, got)
		})
	}
}

func TestToUint64(t *testing.T) {
	tests := []struct {
		name    string
		input   any
		want    uint64
		wantErr bool
	}{
		{"int", 42, 42, false},
		{"uint", uint(100), 100, false},
		{"uint64", uint64(18446744073709551615), 18446744073709551615, false},
		{"string valid", "999", 999, false},
		{"string invalid", "-1", 0, true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var got uint64
			var err error

			switch v := tt.input.(type) {
			case int:
				got, err = ToUint64(v)
			case uint:
				got, err = ToUint64(v)
			case uint64:
				got, err = ToUint64(v)
			case string:
				got, err = ToUint64(v)
			}

			if (err != nil) != tt.wantErr {
				t.Fatalf("ToUint64() error = %v, wantErr %v", err, tt.wantErr)
			}
			if !tt.wantErr && got != tt.want {
				t.Fatalf("ToUint64() = %v, want %v", got, tt.want)
			}
			t.Logf("ToUint64(%v) = %v", tt.input, got)
		})
	}
}

func TestToFloat64(t *testing.T) {
	tests := []struct {
		name    string
		input   string
		want    float64
		wantErr bool
	}{
		{"valid float", "3.14159", 3.14159, false},
		{"valid int string", "100", 100.0, false},
		{"invalid string", "abc", 0, true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := ToFloat64(tt.input)
			if (err != nil) != tt.wantErr {
				t.Fatalf("ToFloat64() error = %v, wantErr %v", err, tt.wantErr)
			}
			if !tt.wantErr && got != tt.want {
				t.Fatalf("ToFloat64() = %v, want %v", got, tt.want)
			}
			t.Logf("ToFloat64(%v) = %v", tt.input, got)
		})
	}
}

func TestToUint(t *testing.T) {
	tests := []struct {
		name    string
		input   any
		want    uint
		wantErr bool
	}{
		{"int", 42, 42, false},
		{"uint", uint(100), 100, false},
		{"uint64", uint64(999), 999, false},
		{"string valid", "123", 123, false},
		{"string invalid", "abc", 0, true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var got uint
			var err error

			switch v := tt.input.(type) {
			case int:
				got, err = ToUint(v)
			case uint:
				got, err = ToUint(v)
			case uint64:
				got, err = ToUint(v)
			case string:
				got, err = ToUint(v)
			}

			if (err != nil) != tt.wantErr {
				t.Fatalf("ToUint() error = %v, wantErr %v", err, tt.wantErr)
			}
			if !tt.wantErr && got != tt.want {
				t.Fatalf("ToUint() = %v, want %v", got, tt.want)
			}
			t.Logf("ToUint(%v) = %v", tt.input, got)
		})
	}
}

func TestTo(t *testing.T) {
	t.Run("successful conversion", func(t *testing.T) {
		input := "hello"
		got, err := To[string](input)
		if err != nil {
			t.Fatalf("To() unexpected error: %v", err)
		}
		if got != input {
			t.Fatalf("To() = %v, want %v", got, input)
		}
		t.Logf("To[string](%v) = %v", input, got)
	})

	t.Run("failed conversion", func(t *testing.T) {
		input := 123
		_, err := To[string](input)
		if err == nil {
			t.Fatal("To() expected error, got nil")
		}
		t.Logf("To[string](%v) returned expected error", input)
	})

	t.Run("struct conversion", func(t *testing.T) {
		type TestStruct struct {
			Name string
		}
		input := TestStruct{Name: "test"}
		got, err := To[TestStruct](input)
		if err != nil {
			t.Fatalf("To() unexpected error: %v", err)
		}
		if got.Name != input.Name {
			t.Fatalf("To() = %v, want %v", got, input)
		}
		t.Logf("To[TestStruct](%v) = %v", input, got)
	})
}

func TestToJsonStr(t *testing.T) {
	tests := []struct {
		name    string
		input   any
		wantErr bool
	}{
		{"map", map[string]int{"a": 1, "b": 2}, false},
		{"struct", struct{ Name string }{"test"}, false},
		{"slice", []int{1, 2, 3}, false},
		{"channel", make(chan int), true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := ToJsonStr(tt.input)
			if (err != nil) != tt.wantErr {
				t.Fatalf("ToJsonStr() error = %v, wantErr %v", err, tt.wantErr)
			}
			if !tt.wantErr && got == "" {
				t.Fatal("ToJsonStr() returned empty string")
			}
			t.Logf("ToJsonStr() = %v", got)
		})
	}
}

func TestToJsonLine(t *testing.T) {
	tests := []struct {
		name    string
		input   any
		want    string
		wantErr bool
	}{
		{"map", map[string]int{"a": 1}, `{"a":1}`, false},
		{"string", "hello", `"hello"`, false},
		{"int", 42, "42", false},
		{"channel", make(chan int), "", true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := ToJsonLine(tt.input)
			if (err != nil) != tt.wantErr {
				t.Fatalf("ToJsonLine() error = %v, wantErr %v", err, tt.wantErr)
			}
			if !tt.wantErr && got != tt.want {
				t.Fatalf("ToJsonLine() = %v, want %v", got, tt.want)
			}
			t.Logf("ToJsonLine() = %v", got)
		})
	}
}

func TestToStrIgnoreErr(t *testing.T) {
	tests := []struct {
		name  string
		input any
		want  string
	}{
		{"map", map[string]int{"a": 1}, `{"a":1}`},
		{"string", "hello", `"hello"`},
		{"int", 42, "42"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := ToStrIgnoreErr(tt.input)
			if got != tt.want {
				t.Fatalf("ToStrIgnoreErr() = %v, want %v", got, tt.want)
			}
			t.Logf("ToStrIgnoreErr() = %v", got)
		})
	}

	// Test channel separately - it cannot be serialized, so check it returns fallback format
	t.Run("channel fallback", func(t *testing.T) {
		got := ToStrIgnoreErr(make(chan int))
		// ToStrIgnoreErr uses fmt.Sprintf as fallback for non-serializable types
		if got == "" {
			t.Fatal("ToStrIgnoreErr() should return non-empty fallback for channel")
		}
		t.Logf("ToStrIgnoreErr(chan) = %v", got)
	})
}

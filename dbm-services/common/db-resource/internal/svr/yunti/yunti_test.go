package yunti

import (
	"encoding/hex"
	"testing"
)

func TestYuntiConfig_IsNotEmpty(t *testing.T) {
	tests := []struct {
		name string
		cfg  YuntiConfig
		want bool
	}{
		{
			name: "empty config",
			cfg:  YuntiConfig{},
			want: false,
		},
		{
			name: "config with addr only",
			cfg:  YuntiConfig{Addr: "http://example.com"},
			want: true,
		},
		{
			name: "config with api key name only",
			cfg:  YuntiConfig{ApiKeyName: "test-key"},
			want: true,
		},
		{
			name: "config with api key secret only",
			cfg:  YuntiConfig{ApiKeySecret: "test-secret"},
			want: true,
		},
		{
			name: "config with interface name only",
			cfg:  YuntiConfig{InterfaceName: "test-interface"},
			want: true,
		},
		{
			name: "full config",
			cfg: YuntiConfig{
				Addr:          "http://example.com",
				ApiKeyName:    "test-key",
				ApiKeySecret:  "test-secret",
				InterfaceName: "test-interface",
			},
			want: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := tt.cfg.IsNotEmpty(); got != tt.want {
				t.Errorf("YuntiConfig.IsNotEmpty() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestGetDataDiskTotalSize(t *testing.T) {
	tests := []struct {
		name         string
		dataDiskList []CvmDataDisk
		want         int
	}{
		{
			name:         "empty disk list",
			dataDiskList: []CvmDataDisk{},
			want:         0,
		},
		{
			name: "single disk",
			dataDiskList: []CvmDataDisk{
				{DiskSize: 100},
			},
			want: 100,
		},
		{
			name: "multiple disks",
			dataDiskList: []CvmDataDisk{
				{DiskSize: 100},
				{DiskSize: 200},
				{DiskSize: 300},
			},
			want: 600,
		},
		{
			name: "disks with zero size",
			dataDiskList: []CvmDataDisk{
				{DiskSize: 0},
				{DiskSize: 50},
				{DiskSize: 0},
			},
			want: 50,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := GetDataDiskTotalSize(tt.dataDiskList); got != tt.want {
				t.Errorf("GetDataDiskTotalSize() = %v, want %v", got, tt.want)
			}
		})
	}
}

func TestYuntiConfig_GetUrl(t *testing.T) {
	config := YuntiConfig{
		Addr:          "example.com:8080",
		ApiKeyName:    "test-key",
		ApiKeySecret:  "test-secret",
		InterfaceName: "api/v1",
	}

	url := config.GetUrl()

	if url == "" {
		t.Error("GetUrl() returned empty string")
	}

	if len(url) < 20 {
		t.Errorf("GetUrl() returned unexpectedly short URL: %s", url)
	}

	if url[:7] != "http://" {
		t.Errorf("GetUrl() should start with http://, got: %s", url)
	}

	if url[len("http://example.com:8080/api/v1?"):] == "" {
		t.Error("GetUrl() should have query parameters")
	}
}

func TestHmacSHA1(t *testing.T) {
	tests := []struct {
		name           string
		apiKeySecret   string
		signData       string
		expectedLength int
	}{
		{
			name:           "normal case",
			apiKeySecret:   "secret",
			signData:       "test-data",
			expectedLength: 40,
		},
		{
			name:           "empty secret",
			apiKeySecret:   "",
			signData:       "test-data",
			expectedLength: 40,
		},
		{
			name:           "empty data",
			apiKeySecret:   "secret",
			signData:       "",
			expectedLength: 40,
		},
		{
			name:           "both empty",
			apiKeySecret:   "",
			signData:       "",
			expectedLength: 40,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := hmacSHA1(tt.apiKeySecret, tt.signData)
			if len(result) != tt.expectedLength {
				t.Errorf("hmacSHA1() returned string of length %d, expected %d", len(result), tt.expectedLength)
			}

			_, err := hex.DecodeString(result)
			if err != nil {
				t.Errorf("hmacSHA1() returned invalid hex string: %v", err)
			}
		})
	}
}

func TestGetSign(t *testing.T) {
	tests := []struct {
		name         string
		timeStr      string
		apiKeyName   string
		apiKeySecret string
	}{
		{
			name:         "normal case",
			timeStr:      "1234567890",
			apiKeyName:   "test-key",
			apiKeySecret: "test-secret",
		},
		{
			name:         "empty values",
			timeStr:      "",
			apiKeyName:   "",
			apiKeySecret: "",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := getSign(tt.timeStr, tt.apiKeyName, tt.apiKeySecret)

			if len(result) != 40 {
				t.Errorf("getSign() returned string of length %d, expected 40", len(result))
			}

			_, err := hex.DecodeString(result)
			if err != nil {
				t.Errorf("getSign() returned invalid hex string: %v", err)
			}
		})
	}
}
